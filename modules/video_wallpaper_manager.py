"""
video_wallpaper_manager.py

Gestisce sfondi video in streaming (stile Projectivy "Overflight") usando mpv
come motore di playback embedded. Legge un catalogo JSON compatibile con
projectivy-plugin-wallpaper-overflight:

    [
        {
            "location": "...",
            "title": "...",
            "author": "...",
            "url_img": "...",
            "url_1080p": "...",
            "url_1080p_hdr": "...",
            "url_4k": "...",
            "url_4k_hdr": "..."
        },
        ...
    ]

Nessun campo è obbligatorio tranne almeno un url_*. Non esiste un campo
"categoria" nel formato originale: i filtri (Night, China, Ocean, ...) sono
ottenuti facendo matching di parole chiave su "location" + "title".

Requisiti:
    pip install python-mpv
    + libmpv binario (mpv-2.dll su Windows, libmpv.so.2 su Linux) presente in:
        <assets_dir>/lib/mpv/<platform>/   oppure già installato nel sistema.
"""

import os
import sys
import json
import time
import random
import platform
import ctypes.util
import re
from pathlib import Path
from urllib.request import urlopen, Request
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtGui import QImage, QPixmap, QOpenGLContext, QSurfaceFormat

# FRAME_MAX_WIDTH ora viene calcolato dinamicamente sulla risoluzione reale
# dello schermo (vedi _init_mpv -> _screen_width()), non più fisso a 1080px:
# su schermi 4K/1440p il vecchio valore fisso produceva un frame più piccolo
# dello schermo, poi "stirato" da Qt (setScaledContents) -> sfocatura visibile.
# Questo è solo un fallback per quando lo schermo non è ancora rilevabile.
FRAME_MAX_WIDTH_FALLBACK = 1920
FRAME_GRAB_INTERVAL_MS = 40  # ~25fps: più regolare su readback GPU->RAM di ogni singolo frame ad alta risoluzione


class _FrameGrabWorker(QObject):
    """Cattura i fotogrammi da mpv (headless, vo='null') su un thread
    separato dalla UI, cosi' l'event loop di Qt resta sempre libero.
    """
    frame_ready = pyqtSignal(QImage)

    def __init__(self, mpv_getter, interval_ms, max_width):
        super().__init__()
        self._mpv_getter = mpv_getter
        self._interval_ms = interval_ms
        self._max_width = max_width
        self._timer = None
        self._grabbing = False
        self._running = False

    @pyqtSlot()
    def start(self):
        # Timer single-shot auto-riprogrammato: se un grab impiega più del
        # previsto, il prossimo parte comunque DOPO quello (mai in coda
        # dietro grab già in ritardo) -> pacing più regolare.
        self._running = True
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._grab)
        self._timer.start(self._interval_ms)

    @pyqtSlot()
    def stop(self):
        self._running = False
        if self._timer:
            self._timer.stop()

    def _grab(self):
        if self._grabbing:
            self._reschedule()
            return
        mpv = self._mpv_getter()
        if mpv is None:
            self._reschedule()
            return
        # Riallinea l'intervallo di grab all'fps reale del video, invece di
        # usare sempre il valore fisso iniziale: un timer scollegato dal
        # ritmo reale dei fotogrammi produce un mismatch periodico (a volte
        # cattura due volte lo stesso frame, a volte ne salta uno) che è la
        # causa principale dello scatto percepito, indipendente da CPU/GPU.
        try:
            fps = mpv.fps or mpv.container_fps
            if fps and fps > 1:
                target_interval = max(16, round(1000 / fps))
                if target_interval != self._interval_ms:
                    self._interval_ms = target_interval
        except Exception:
            pass
        self._grabbing = True
        try:
            img = mpv.screenshot_raw()
            if img is None:
                return
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            # NIENTE resize qui: il filtro vf=scale di mpv (GPU-side, veloce)
            # ha già portato il frame alla risoluzione target. Ridimensionare
            # di nuovo qui in Python con PIL era lavoro doppio e la causa
            # principale degli scatti: un resize CPU per ogni singolo frame,
            # ~25-30 volte al secondo, oltre al normale readback GPU->RAM.
            data = img.tobytes("raw", "RGBA")
            qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
            qimg = qimg.copy()
            self.frame_ready.emit(qimg)
        except Exception as e:
            self._fail_count = getattr(self, '_fail_count', 0) + 1
            # Logga solo ogni 25 fallimenti (~1 al secondo a 40ms/frame) invece
            # che ad ogni singolo frame perso: con hwdec attivo il log veniva
            # inondato di errori identici, che da soli rallentavano il thread
            # e peggioravano gli scatti.
            if self._fail_count % 25 == 1:
                print(f"[VideoWallpaper] grab frame fallito ({self._fail_count} totali): {e}")
        finally:
            self._grabbing = False
            self._reschedule()

    def _reschedule(self):
        if self._running and self._timer:
            self._timer.start(self._interval_ms)


class _MpvGLWidget(QOpenGLWidget):
    """Widget che disegna i frame di mpv usando la render API di libmpv
    (push-based, mpv scrive direttamente su una FBO OpenGL) invece dello
    screenshot-per-frame via IPC usato da _FrameGrabWorker.

    A differenza di un embedding "nativo" via winId/wid (una vera finestra a
    livello OS che ignora lo z-order di Qt), QOpenGLWidget compone il proprio
    contenuto DENTRO alla normale pipeline di rendering di Qt: si comporta
    come un widget qualsiasi ai fini di lower()/stackUnder(), quindi i tile
    sopra restano correttamente sopra. Questo risolve sia il problema di
    fluidità (nessun readback CPU per ogni frame, mpv scrive dov'è già pronto
    per essere disegnato) sia il problema di stacking dell'embedding nativo.
    """

    def __init__(self, mpv_instance, parent=None):
        super().__init__(parent)
        self._mpv = mpv_instance
        self._render_ctx = None
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, False)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)

        # Disattiva il vsync-wait sul contesto GL di QUESTO widget. Senza
        # questo, ogni frame del video (~30fps) forza un proprio swap-buffer
        # che di default aspetta il prossimo vsync, in competizione con lo
        # swap del compositor principale di Qt (quello che fa girare i tile
        # a 60fps): il thread GUI finisce ad aspettare due vsync invece di
        # uno, e tutta l'app viene trascinata giù verso il framerate del
        # video. Con swapInterval=0 solo il compositor principale aspetta
        # il vsync, e lo fa una volta sola per frame.
        fmt = QSurfaceFormat()
        fmt.setSwapInterval(0)
        self.setFormat(fmt)

    frame_ready = pyqtSignal()

    def _get_proc_address(self, _, name):
        glctx = QOpenGLContext.currentContext()
        if glctx is None:
            return 0
        addr = glctx.getProcAddress(bytes(name))
        return int(addr) if addr else 0

    def initializeGL(self):
        import mpv as mpv_module
        # get_proc_address deve essere un vero ctypes CFUNCTYPE (il tipo
        # esposto da python-mpv come MpvGlGetProcAddressFn), non un metodo
        # Python passato as-is: kwargs_to_render_param_array fa una
        # conversione ctypes stretta e un metodo "nudo" fallisce con
        # TypeError. Teniamo anche un riferimento esplicito (self._get_proc_address_c)
        # perché altrimenti il garbage collector di Python può liberare il
        # wrapper ctypes mentre libmpv lo sta ancora usando -> crash.
        self._get_proc_address_c = mpv_module.MpvGlGetProcAddressFn(self._get_proc_address)
        self._render_ctx = mpv_module.MpvRenderContext(
            self._mpv, 'opengl',
            opengl_init_params={'get_proc_address': self._get_proc_address_c}
        )
        # update_cb viene chiamato da mpv su un thread interno ogni volta che
        # c'è un nuovo frame pronto: non tocchiamo la UI da lì direttamente
        # (non è il thread Qt), emettiamo solo un segnale, thread-safe, che
        # Qt marshalla sul thread principale per noi.
        self._render_ctx.update_cb = self._on_frame_ready

    def _on_frame_ready(self):
        self.frame_ready.emit()

    def paintGL(self):
        if self._render_ctx is None:
            return
        try:
            self._render_ctx.render(
                flip_y=True,
                opengl_fbo={'w': self.width(), 'h': self.height(), 'fbo': self.defaultFramebufferObject()},
                # Senza questo, libmpv blocca INTERNAMENTE il thread chiamante
                # (qui: il thread GUI di Qt, dentro paintGL) per far
                # coincidere il fotogramma con l'istante di tempo esatto
                # (frame pacing). Girando sul thread principale, quel blocco
                # fermava anche animazioni dei tile e apertura menu, non solo
                # il video: tutta l'app rallentava in lockstep col framerate
                # del video pur con hardware quasi a riposo (il thread era
                # bloccato in attesa, non impegnato a calcolare). Con
                # block_for_target_time=False, mpv disegna subito col
                # fotogramma corrente senza mai bloccare il chiamante.
                block_for_target_time=False,
            )
        except Exception as e:
            print(f"[VideoWallpaper] render frame fallito: {e}")

    def shutdown(self):
        if self._render_ctx is not None:
            try:
                self._render_ctx.update_cb = None
                self._render_ctx.free()
            except Exception:
                pass
            self._render_ctx = None


DEFAULT_CATALOG_URL = (
    "https://raw.githubusercontent.com/spocky/"
    "projectivy-plugin-wallpaper-overflight/main/videos.json"
)

# Priorità qualità: chiave config -> ordine di fallback sui campi url_*
QUALITY_CHAINS = {
    "4k_hdr": ["url_4k_hdr", "url_4k", "url_1080p_hdr", "url_1080p"],
    "4k":     ["url_4k", "url_4k_hdr", "url_1080p_hdr", "url_1080p"],
    "1080p_hdr": ["url_1080p_hdr", "url_1080p", "url_4k_hdr", "url_4k"],
    "1080p":  ["url_1080p", "url_1080p_hdr", "url_4k", "url_4k_hdr"],
    "auto":   ["url_1080p", "url_4k", "url_1080p_hdr", "url_4k_hdr"],
}

# Parole chiave di default per i filtri "categoria" mostrati nel dialog.
# L'utente può estenderle/modificarle da config (vedi set_category_keywords).
DEFAULT_CATEGORIES = {
    "Nature":      ["nature", "forest", "mountain", "valley", "canyon", "waterfall"],
    "City":        ["city", "skyline", "urban", "downtown", "night city"],
    "Night":       ["night", "notturn", "aurora night", "northern lights"],
    "Ocean":       ["ocean", "sea", "coast", "beach", "reef", "wave"],
    "Space":       ["space", "earth", "orbit", "galaxy", "iss", "satellite", "aurora"],
    "Countryside": ["countryside", "farm", "field", "rural", "vineyard"],
    "Desert":      ["desert", "dune", "sahara"],
    "Snow":        ["snow", "winter", "alps", "glacier", "ice"],
    "China":       ["china", "beijing", "shanghai", "hong kong", "great wall"],
    "Japan":       ["japan", "tokyo", "kyoto", "fuji"],
    "USA":         ["usa", "america", "new york", "california", "hawaii"],
}


class VideoWallpaperManager:
    """Gestisce catalogo, filtri, playback mpv e rotazione automatica dei video wallpaper."""

    def __init__(self, parent, config_data, assets_dir, background_manager=None):
        """
        Args:
            parent: la finestra principale (TVLauncher)
            config_data: dict di configurazione globale (sezione 'video_wallpaper')
            assets_dir: Path alla cartella assets
            background_manager: istanza di BackgroundManager (per fallback statico
                                 e per mettere in pausa la rotazione wallpaper statici
                                 quando i video sono attivi)
        """
        self.parent = parent
        self.assets_dir = Path(assets_dir)
        self.background_manager = background_manager

        cfg = dict(config_data.get('video_wallpaper', {})) if config_data else {}
        self.enabled = cfg.get('enabled', False)
        self.quality = cfg.get('quality', '1080p')                 # vedi QUALITY_CHAINS
        self.interval_seconds = cfg.get('interval_seconds', 600)   # 10 minuti default
        self.categories = cfg.get('categories', [])                # lista vuota = tutte
        self.catalog_url = cfg.get('catalog_url', DEFAULT_CATALOG_URL)
        self.muted = cfg.get('muted', True)
        self.volume = cfg.get('volume', 0)

        self.category_keywords = dict(DEFAULT_CATEGORIES)

        self.catalog = []            # lista di entry filtrate/valide
        self.current_entry = None
        self.rotation_timer = None
        self._dead_urls = set()      # URL risultati non funzionanti in questa sessione
        self._consecutive_failures = 0
        self._max_consecutive_failures = 15
        self._skip_timer = None
        self._play_generation = 0

        self.mpv = None
        self._render_mode = None     # 'gl' (render API, veloce) oppure 'legacy' (screenshot relay, fallback)
        self.video_label = None      # _MpvGLWidget in modalità 'gl', QLabel in modalità 'legacy'
        self.available = False       # True se mpv è stato inizializzato con successo
        self.last_error = None
        self._frame_thread = None
        self._frame_worker = None

        self._cache_file = self.assets_dir / 'wallpapers_video' / 'catalog_cache.json'
        self._cache_file.parent.mkdir(parents=True, exist_ok=True)

    # ==================== INIZIALIZZAZIONE MPV ====================

    def _screen_width(self):
        """Larghezza reale dello schermo primario, usata per far scalare mpv
        (via filtro vf, GPU-side) esattamente alla risoluzione di destinazione,
        invece del vecchio limite fisso a 1080px che su schermi più grandi
        produceva un frame sotto-risoluzione poi stirato da Qt."""
        try:
            screen = QApplication.primaryScreen().geometry()
            if screen.width() > 0:
                return screen.width()
        except Exception:
            pass
        return FRAME_MAX_WIDTH_FALLBACK

    def _locate_libmpv(self):
        """Cerca il binario libmpv: prima bundled in assets/lib/mpv, poi di sistema."""
        system = platform.system()
        bundled_dir = self.assets_dir / 'lib' / 'mpv'

        candidates = []
        if system == "Windows":
            candidates.append(bundled_dir / 'windows' / 'libmpv-2.dll')
            candidates.append(bundled_dir / 'windows' / 'mpv-2.dll')
        else:
            candidates.append(bundled_dir / 'linux' / 'libmpv.so.2')
            candidates.append(bundled_dir / 'linux' / 'libmpv.so')

        for c in candidates:
            if c.exists():
                return str(c)

        # Fallback: libreria di sistema già installata
        found = ctypes.util.find_library('mpv')
        return found  # può essere None

    def _init_mpv(self):
        """Inizializza libmpv + python-mpv embedding in un QWidget dietro l'overlay.

        Prova prima la render API (vo='libmpv' + QOpenGLWidget, push-based,
        mpv scrive i frame direttamente su una FBO GPU senza passare dalla
        CPU). Se fallisce per qualsiasi motivo (libmpv troppo vecchia,
        python-mpv senza MpvRenderContext, driver OpenGL problematico...) si
        ripiega automaticamente sul vecchio meccanismo a screenshot, che è
        più lento ma più compatibile.
        """
        if self.mpv is not None:
            return True

        lib_path = self._locate_libmpv()
        if lib_path is None:
            self.last_error = (
                "libmpv non trovata. Metti mpv-2.dll (Windows) o libmpv.so.2 (Linux) "
                "in assets/lib/mpv/<piattaforma>/ oppure installa mpv nel sistema."
            )
            self.available = False
            return False

        if platform.system() == "Windows":
            dll_dir = str(Path(lib_path).parent)
            try:
                os.add_dll_directory(dll_dir)
            except (AttributeError, OSError):
                pass
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
        else:
            if 'wallpapers_video' not in lib_path and 'lib/mpv' in lib_path:
                ctypes.CDLL(lib_path)

        if self._init_mpv_render_api():
            self._render_mode = 'gl'
            self.available = True
            self.last_error = None
            return True

        print(f"[VideoWallpaper] Render API non disponibile ({self.last_error}), "
              f"fallback su screenshot relay.")
        if self._init_mpv_legacy():
            self._render_mode = 'legacy'
            self.available = True
            self.last_error = None
            return True

        self.available = False
        return False

    def _common_mpv_kwargs(self, vo):
        return dict(
            vo=vo,
            loop_file='inf',
            keep_open='yes',
            idle='yes',
            osc=False,
            input_default_bindings=False,
            input_vo_keyboard=False,
            mute=self.muted,
            volume=self.volume,
            cache='yes',
            network_timeout=15,
            log_handler=self._mpv_log,
            loglevel='warn',
            ytdl=False,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            http_header_fields="Referer: https://www.apple.com/",
        )

    def _init_mpv_render_api(self):
        """Percorso veloce: mpv + QOpenGLWidget via render API di libmpv."""
        try:
            import mpv

            mpv_kwargs = self._common_mpv_kwargs(vo='libmpv')
            # Con la render API il frame resta sulla GPU dall'inizio alla
            # fine (decodifica hw -> texture -> composizione Qt): nessun
            # readback CPU per-frame come nel percorso screenshot, quindi
            # qui l'hwdec torna un vantaggio invece di un problema.
            mpv_kwargs['hwdec'] = 'auto-safe'

            self.mpv = mpv.MPV(**mpv_kwargs)
            self.mpv.observe_property('eof-reached', self._on_eof_reached)
            self.mpv.event_callback('file-loaded')(self._on_file_loaded)
            self.mpv.event_callback('end-file')(self._on_end_file)

            self.video_label = _MpvGLWidget(self.mpv, self.parent)
            self.video_label.frame_ready.connect(self.video_label.update)
            screen = QApplication.primaryScreen().geometry()
            self.video_label.setGeometry(0, 0, screen.width(), screen.height())
            self.video_label.lower()
            if getattr(self, 'overlay', None):
                self.video_label.stackUnder(self.overlay)
            self.video_label.show()  # forza initializeGL() -> crea il render context

            if getattr(self.video_label, '_render_ctx', None) is None:
                raise RuntimeError("MpvRenderContext non creato (initializeGL non chiamato o fallito)")

            return True
        except Exception as e:
            self.last_error = f"Render API fallita: {e}"
            if self.mpv is not None:
                try:
                    self.mpv.terminate()
                except Exception:
                    pass
                self.mpv = None
            if getattr(self, 'video_label', None):
                self.video_label.deleteLater()
                self.video_label = None
            return False

    def _init_mpv_legacy(self):
        """Percorso di fallback: mpv headless (vo='null') + screenshot per
        frame su una QLabel, come prima dell'introduzione della render API."""
        try:
            import mpv

            self.video_label = QLabel(self.parent)
            self.video_label.setStyleSheet("background-color: black;")
            self.video_label.setScaledContents(True)
            screen = QApplication.primaryScreen().geometry()
            self.video_label.setGeometry(0, 0, screen.width(), screen.height())
            self.video_label.lower()
            if getattr(self, 'overlay', None):
                self.video_label.stackUnder(self.overlay)
            self.video_label.show()

            mpv_kwargs = self._common_mpv_kwargs(vo='null')
            # hwdec disattivato: con vo='null' e uno screenshot per ogni
            # frame via IPC, un frame decodificato in hardware va comunque
            # scaricato dalla GPU ad ogni cattura -> fallimenti intermittenti
            # (MPV_ERROR_COMMAND, -12) e frame persi. Vedi _init_mpv_render_api
            # per il percorso senza questo limite.
            mpv_kwargs['hwdec'] = 'no'
            mpv_kwargs['vf'] = f"lavfi=[scale={self._screen_width()}:-2]"

            self.mpv = mpv.MPV(**mpv_kwargs)
            self.mpv.observe_property('eof-reached', self._on_eof_reached)
            self.mpv.event_callback('file-loaded')(self._on_file_loaded)
            self.mpv.event_callback('end-file')(self._on_end_file)

            self._setup_frame_worker()
            return True

        except Exception as e:
            self.last_error = f"Inizializzazione mpv fallita: {e}"
            self.mpv = None
            if getattr(self, 'video_label', None):
                self.video_label.deleteLater()
                self.video_label = None
            return False

    def _setup_frame_worker(self):
        self._frame_thread = QThread()
        self._frame_worker = _FrameGrabWorker(
            mpv_getter=lambda: self.mpv,
            interval_ms=FRAME_GRAB_INTERVAL_MS,
            max_width=self._screen_width(),
        )
        self._frame_worker.moveToThread(self._frame_thread)
        self._frame_worker.frame_ready.connect(self._apply_frame)
        self._frame_thread.started.connect(self._frame_worker.start)
        self._frame_thread.start()

    def _apply_frame(self, qimg):
        if self.video_label:
            self.video_label.setPixmap(QPixmap.fromImage(qimg))

    def _start_frame_grabbing(self):
        if self._frame_worker:
            from PyQt6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self._frame_worker, "start")

    def _stop_frame_grabbing(self):
        if self._frame_worker:
            from PyQt6.QtCore import QMetaObject
            QMetaObject.invokeMethod(self._frame_worker, "stop")

    def resize_to_parent(self):
        """Ridimensiona la QLabel video per riempire lo schermo (chiamare su resize)."""
        if self.video_label:
            screen = QApplication.primaryScreen().geometry()
            self.video_label.setGeometry(0, 0, screen.width(), screen.height())

    def _mpv_log(self, loglevel, component, message):
        """Riceve i log interni di mpv - fondamentale per diagnosticare schermo nero silenzioso."""
        print(f"[mpv/{loglevel}] {component}: {message}")

    def _on_eof_reached(self, name, value):
        """Se il file corrente finisce (non dovrebbe con loop_file='inf', ma per sicurezza)
        o se il caricamento fallisce e mpv segnala eof senza aver mai riprodotto nulla."""
        if value:
            print(f"[VideoWallpaper] eof-reached su: "
                  f"{self.current_entry.get('title') if self.current_entry else '?'}")

    def _on_file_loaded(self, event=None):
        """Chiamato da mpv quando un file è stato caricato correttamente."""
        self._consecutive_failures = 0

    def _log_playback_diagnostics(self):
        """Stampa lo stato interno di mpv per capire se il problema è decodifica o rendering."""
        if not self.mpv:
            return
        try:
            params = self.mpv.video_params
            width = self.mpv.width
            height = self.mpv.height
            core_idle = self.mpv.core_idle
            pause = self.mpv.pause
            print(
                f"[VideoWallpaper][diag] video_params={params} width={width} height={height} "
                f"core_idle={core_idle} pause={pause} "
                f"label_size={self.video_label.size() if self.video_label else None} "
                f"label_visible={self.video_label.isVisible() if self.video_label else None}"
            )
        except Exception as e:
            print(f"[VideoWallpaper][diag] Impossibile leggere lo stato mpv: {e}")

    def _on_end_file(self, event):
        """Chiamato da mpv a fine riproduzione file.

        NOTA: non ci si affida più a event.get('reason') qui, perché l'oggetto
        passato da python-mpv per l'evento 'end-file' non è un dict (è un
        MpvEvent, con la reason dentro event.data, in formati che variano tra
        versioni della libreria) — isinstance(event, dict) risultava sempre
        False, la funzione ritornava subito e un link morto non veniva MAI
        gestito: mpv restava idle per sempre -> schermo nero permanente senza
        alcun log di errore. La logica di failure-detection vera è ora in
        _check_playback_health(), un watchdog temporizzato avviato da
        play_entry() che non dipende dal formato dell'evento.
        """
        pass

    def stack_under(self, overlay=None):
        """Assicura che la QLabel video resti sotto ai tile/overlay (widget
        figlio della stessa finestra: normale stacking Qt, non tra finestre)."""
        if self.video_label:
            self.video_label.lower()
            if overlay:
                self.video_label.stackUnder(overlay)

    # ==================== CATALOGO ====================

    def fetch_catalog(self, force=False):
        """
        Scarica (o legge da cache) il catalogo JSON e lo normalizza.

        Args:
            force: ignora la cache e riscarica
        Returns:
            bool: True se il catalogo è stato caricato (rete o cache), False altrimenti
        """
        raw = None

        if not force and self._cache_file.exists():
            try:
                cached = json.loads(self._cache_file.read_text(encoding='utf-8'))
                age = time.time() - cached.get('_fetched_at', 0)
                if age < 24 * 3600 and cached.get('url') == self.catalog_url:
                    raw = cached.get('data')
            except Exception:
                raw = None

        if raw is None:
            try:
                req = Request(self.catalog_url, headers={'User-Agent': 'TVLauncher/1.0'})
                with urlopen(req, timeout=10) as resp:
                    raw = json.loads(resp.read().decode('utf-8'))
                self._cache_file.write_text(
                    json.dumps({'url': self.catalog_url, '_fetched_at': time.time(), 'data': raw}),
                    encoding='utf-8'
                )
            except Exception as e:
                self.last_error = f"Download catalogo fallito: {e}"
                # Fallback: prova comunque a usare la cache anche se scaduta/di altro URL
                if self._cache_file.exists():
                    try:
                        cached = json.loads(self._cache_file.read_text(encoding='utf-8'))
                        raw = cached.get('data')
                    except Exception:
                        raw = None

        if not raw:
            self.catalog = []
            return False

        # Normalizza: tiene solo entry con almeno un campo url_*
        url_fields = ('url_4k_hdr', 'url_4k', 'url_1080p_hdr', 'url_1080p')
        normalized = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if any(entry.get(f) for f in url_fields):
                normalized.append(entry)

        self.catalog = normalized
        return True

    def set_catalog_url(self, url):
        self.catalog_url = url or DEFAULT_CATALOG_URL

    def get_available_categories(self):
        """Ritorna la lista dei nomi di categoria configurati (per la UI)."""
        return list(self.category_keywords.keys())

    def _entry_text(self, entry):
        return f"{entry.get('location', '')} {entry.get('title', '')} {entry.get('author', '')}".lower()

    def _matches_categories(self, entry):
        if not self.categories:
            return True
        text = self._entry_text(entry)
        for cat in self.categories:
            keywords = self.category_keywords.get(cat, [cat.lower()])
            for k in keywords:
                # Confine di parola: evita match parziali tipo "night" dentro
                # "midnight", o "stars" dentro "Sea Stars" quando non è quella
                # la parola cercata. \s+ nel pattern gestisce anche keyword
                # multi-parola come "night city" o "aurora night".
                pattern = r'\b' + re.escape(k.lower()).replace(r'\ ', r'\s+') + r'\b'
                if re.search(pattern, text):
                    return True
        return False

    def get_filtered_entries(self):
        entries = [e for e in self.catalog if self._matches_categories(e)]
        # Esclude entry i cui URL (per la qualità corrente) sono già risultati morti in sessione
        return [e for e in entries if self.pick_video_url(e) not in self._dead_urls]

    def validate_catalog(self, max_workers=16, timeout=4, progress_callback=None):
        """
        Controlla in parallelo (richieste HEAD, poi fallback GET Range 0-0) quali URL
        del catalogo (per la qualità attualmente selezionata) sono raggiungibili, e
        popola self._dead_urls con quelli morti. Da chiamare dopo fetch_catalog(),
        tipicamente dal pulsante "Aggiorna catalogo" nel dialog impostazioni: evita
        di scoprire i link morti uno alla volta con schermo nero durante la rotazione.

        Args:
            max_workers: numero di richieste in parallelo
            timeout: timeout in secondi per singola richiesta
            progress_callback: opzionale, callback(checked, total) per aggiornare la UI

        Returns:
            tuple (alive_count, dead_count)
        """
        entries = [e for e in self.catalog if self._matches_categories(e)]
        urls = [self.pick_video_url(e) for e in entries]
        urls = [u for u in urls if u]
        total = len(urls)
        checked = 0
        dead = 0

        def _check(url):
            try:
                req = Request(url, method='HEAD', headers={
                    'User-Agent': (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    )
                })
                with urlopen(req, timeout=timeout) as resp:
                    return url, resp.status < 400
            except Exception:
                # Alcuni server non supportano HEAD: prova un GET con range minimo
                try:
                    req = Request(url, headers={
                        'User-Agent': (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                        ),
                        'Range': 'bytes=0-0'
                    })
                    with urlopen(req, timeout=timeout) as resp:
                        return url, resp.status < 400
                except Exception:
                    return url, False

        if not urls:
            return 0, 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_check, u): u for u in urls}
            for future in as_completed(futures):
                url, alive = future.result()
                checked += 1
                if not alive:
                    self._dead_urls.add(url)
                    dead += 1
                if progress_callback:
                    progress_callback(checked, total)

        return total - dead, dead

    def pick_video_url(self, entry):
        """Sceglie l'URL video migliore per un'entry secondo la qualità configurata."""
        chain = QUALITY_CHAINS.get(self.quality, QUALITY_CHAINS['1080p'])
        for field in chain:
            url = entry.get(field)
            if url:
                return url
        return None

    # ==================== PLAYBACK ====================

    def initialize(self, overlay=None):
        """
        Predispone il manager (overlay, config). L'inizializzazione VERA di mpv
        viene rimandata a start_deferred(), da chiamare quando la finestra
        principale è già visibile (es. subito dopo launcher.show()), altrimenti
        l'embedding via window id può agganciarsi a un handle non ancora valido
        e produrre schermo nero.
        """
        self.overlay = overlay
        if not self.enabled:
            return
        # Se il parent è già visibile (es. reinizializzazione a runtime), procedi subito.
        if self.parent.isVisible():
            self.start_deferred()

    def start_deferred(self):
        """Da chiamare quando la finestra principale è sicuramente visibile."""
        if not self.enabled:
            return

        if not self._init_mpv():
            print(f"[VideoWallpaper] {self.last_error} - fallback su sfondo statico.")
            return

        self.resize_to_parent()
        self.stack_under(getattr(self, 'overlay', None))

        if not self.catalog:
            self.fetch_catalog()

        self.start_rotation()

    def play_entry(self, entry):
        """Avvia la riproduzione di una specifica entry del catalogo."""
        if not self.available or not self.mpv:
            return False

        url = self.pick_video_url(entry)
        if not url:
            return False

        try:
            self.mpv.play(url)
            self.current_entry = entry
            # Incrementa il "generation token": serve al watchdog per capire se,
            # quando scatta, si sta ancora controllando QUESTA riproduzione o se
            # nel frattempo se ne è già avviata un'altra (es. skip manuale).
            self._play_generation += 1
            my_generation = self._play_generation

            if self.video_label:
                self.video_label.show()
                self.stack_under(getattr(self, 'overlay', None))

            if self._render_mode == 'legacy':
                self._start_frame_grabbing()

            # Diagnostica: dopo 3s controlla se mpv ha effettivamente dei parametri
            # video validi (cioè sta decodificando), utile per distinguere un problema
            # di rete/decodifica da un problema di sola visualizzazione/embedding.
            QTimer.singleShot(3000, self._log_playback_diagnostics)

            # Watchdog di failure-detection: non ci si affida più agli eventi
            # 'end-file' di mpv (il loro formato tramite python-mpv non è un
            # dict come ci si aspettava, quindi i link morti non venivano mai
            # rilevati -> schermo nero permanente senza retry). Si controlla
            # invece direttamente lo stato di mpv dopo un tempo ragionevole.
            QTimer.singleShot(4500, lambda: self._check_playback_health(entry, url, my_generation))

            return True
        except Exception as e:
            self.last_error = f"Playback fallito ({entry.get('title', '?')}): {e}"
            print(f"[VideoWallpaper] {self.last_error}")
            return False

    def _check_playback_health(self, entry, url, generation):
        """Watchdog: se 4.5s dopo l'avvio mpv è ancora idle senza video_params,
        il link è considerato morto (404, formato non supportato, timeout di
        rete, ecc.) e si passa automaticamente al successivo."""
        if not self.enabled:
            # L'utente ha disattivato il video wallpaper nel frattempo: questo
            # watchdog era già schedulato da PRIMA (play_entry lo avvia con
            # QTimer.singleShot) e non veniva annullato da toggle_enabled().
            # Senza questo controllo, mpv.stop() (chiamato per disattivare)
            # veniva scambiato per un "link morto" e la riproduzione ripartiva
            # da sola qualche secondo dopo, come se il toggle non avesse
            # avuto effetto.
            return
        if generation != self._play_generation:
            # Nel frattempo è già partita un'altra riproduzione: non fare nulla.
            return
        if not self.mpv:
            return

        try:
            healthy = (not self.mpv.core_idle) or (self.mpv.video_params is not None)
        except Exception:
            healthy = False

        if healthy:
            self._consecutive_failures = 0
            return

        # Link morto: marca come tale ed escludilo dai tentativi futuri.
        self._dead_urls.add(url)
        title = entry.get('title') or entry.get('location') or '?'
        print(f"[VideoWallpaper] Link non raggiungibile, skip: {title}")

        self._consecutive_failures += 1
        if self._consecutive_failures >= self._max_consecutive_failures:
            self.last_error = (
                f"Troppi video non raggiungibili di fila ({self._consecutive_failures}). "
                "Interrompo i tentativi automatici: prova ad aggiornare il catalogo o "
                "cambia URL/categorie."
            )
            print(f"[VideoWallpaper] {self.last_error}")
            self.stop_rotation()
            return

        if self._skip_timer is None:
            self._skip_timer = QTimer()
            self._skip_timer.setSingleShot(True)
            self._skip_timer.timeout.connect(self.play_random)
        self._skip_timer.start(300)

    def play_random(self):
        """Sceglie e riproduce un video casuale dal set filtrato (evitando il corrente)."""
        entries = self.get_filtered_entries()
        if not entries:
            self.last_error = "Nessun video disponibile per i filtri selezionati."
            return False

        if len(entries) > 1 and self.current_entry in entries:
            entries = [e for e in entries if e is not self.current_entry]

        entry = random.choice(entries)
        return self.play_entry(entry)

    def next_video(self):
        return self.play_random()

    # ==================== ROTAZIONE AUTOMATICA ====================

    def start_rotation(self):
        if not self.enabled or not self.available:
            return

        # Nasconde lo sfondo statico (nessuna immagine deve competere con il
        # video per lo stesso spazio) e ferma la sua rotazione.
        if self.background_manager:
            self.background_manager.suspend_for_video()

        self.play_random()

        # suspend_for_video() può aver ricreato l'HWND del launcher (cambio
        # windowFlags + showFullScreen), il che può temporaneamente rimetterlo
        # sopra alla finestra video nello z-order. play_entry() già richiama
        # stack_under(), ma un secondo richiamo posticipato copre il caso in
        # cui la ri-creazione dell'HWND avvenga con un frame di ritardo.
        QTimer.singleShot(150, lambda: self.stack_under(getattr(self, 'overlay', None)))

        if self.rotation_timer is None:
            self.rotation_timer = QTimer()
            self.rotation_timer.timeout.connect(self.next_video)
        self.rotation_timer.start(max(30, self.interval_seconds) * 1000)

    def stop_rotation(self):
        if self.rotation_timer:
            self.rotation_timer.stop()
        if self._skip_timer:
            self._skip_timer.stop()
        self._stop_frame_grabbing()

    def toggle_enabled(self, enabled):
        """Attiva/disattiva la modalità video wallpaper, coordinandosi con BackgroundManager."""
        self.enabled = enabled

        if enabled:
            if not self.available:
                if not self._init_mpv():
                    print(f"[VideoWallpaper] {self.last_error}")
                    self.enabled = False
                    return False
                self.resize_to_parent()

            if self.video_label:
                self.video_label.show()
            self.stack_under(getattr(self, 'overlay', None))

            if not self.catalog:
                self.fetch_catalog()

            self.start_rotation()
        else:
            self.stop_rotation()
            if self.mpv:
                try:
                    self.mpv.stop()
                except Exception:
                    pass
            if self.video_label:
                self.video_label.hide()
            # Ripristina lo sfondo statico
            if self.background_manager:
                self.background_manager.resume_after_video()

        return True

    # ==================== PAUSA PER FOCUS APP ESTERNA ====================

    def pause_for_app_focus(self):
        """Il launcher ha perso il focus (un'altra app è in primo piano):
        ferma decode/rendering/rete senza smontare lo stream mpv, cosi il
        resume è istantaneo e non richiede un nuovo fetch della sorgente.
        """
        if not self.available or not self.mpv:
            return
        try:
            self.mpv.pause = True
        except Exception:
            pass
        if self.rotation_timer:
            self.rotation_timer.stop()
        if self._skip_timer:
            self._skip_timer.stop()
        self._stop_frame_grabbing()
        # NOTA: non nascondiamo video_label. mpv in pausa lascia l'ultimo
        # frame renderizzato fermo sullo schermo (equivalente a uno sfondo
        # statico), quindi la label resta a coprire lo stesso spazio senza
        # rivelare per un istante ciò che c'è sotto (QMainWindow/vecchio
        # sfondo statico) mentre l'app esterna sta ancora aprendosi. Nascondere
        # e poi ri-mostrare la label produceva un flicker visibile e un
        # ritardo extra proprio nel momento più delicato del cambio focus.

    def resume_from_app_focus(self):
        """Il launcher è tornato in focus: riprendi la riproduzione del
        video wallpaper (se era abilitato)."""
        if not self.enabled or not self.available or not self.mpv:
            return
        self._start_frame_grabbing()
        try:
            self.mpv.pause = False
        except Exception:
            pass
        if self.rotation_timer:
            self.rotation_timer.start(max(30, self.interval_seconds) * 1000)

    def set_interval(self, seconds):
        self.interval_seconds = max(30, seconds)
        if self.rotation_timer and self.rotation_timer.isActive():
            self.rotation_timer.start(self.interval_seconds * 1000)

    def set_quality(self, quality):
        if quality in QUALITY_CHAINS:
            self.quality = quality
            if self.current_entry and self.available:
                self.play_entry(self.current_entry)

    def set_categories(self, categories):
        self.categories = list(categories or [])

    def set_muted(self, muted):
        self.muted = muted
        if self.mpv:
            try:
                self.mpv.mute = muted
            except Exception:
                pass

    # ==================== CONFIGURAZIONE ====================

    def get_config(self):
        return {
            'enabled': self.enabled,
            'quality': self.quality,
            'interval_seconds': self.interval_seconds,
            'categories': self.categories,
            'catalog_url': self.catalog_url,
            'muted': self.muted,
            'volume': self.volume,
        }

    def load_config(self, config_data):
        cfg = dict(config_data.get('video_wallpaper', {})) if config_data else {}
        self.enabled = cfg.get('enabled', False)
        self.quality = cfg.get('quality', '1080p')
        self.interval_seconds = cfg.get('interval_seconds', 600)
        self.categories = cfg.get('categories', [])
        self.catalog_url = cfg.get('catalog_url', DEFAULT_CATALOG_URL)
        self.muted = cfg.get('muted', True)
        self.volume = cfg.get('volume', 0)

    # ==================== CLEANUP ====================

    def cleanup(self):
        self.stop_rotation()
        if self._frame_thread:
            self._stop_frame_grabbing()
            self._frame_thread.quit()
            self._frame_thread.wait(2000)
            self._frame_thread = None
            self._frame_worker = None
        if self._render_mode == 'gl' and self.video_label is not None:
            try:
                self.video_label.shutdown()
            except Exception:
                pass
        if self.mpv:
            try:
                self.mpv.terminate()
            except Exception:
                pass
            self.mpv = None
        if self.video_label:
            self.video_label.close()
            self.video_label.deleteLater()
            self.video_label = None
        self._render_mode = None
        self.available = False


# ==================== FUNZIONE DI INTEGRAZIONE ====================

def integrate_video_wallpaper(launcher_class):
    """
    Integra il VideoWallpaperManager nella classe TVLauncher.
    Va chiamata DOPO integrate_background_manager (o comunque assicurarsi
    che self.background_manager esista già quando si costruisce il manager).
    """
    original_init = launcher_class.__init__

    def new_init(self):
        original_init(self)
        from modules.video_wallpaper_manager import VideoWallpaperManager
        self.video_wallpaper_manager = VideoWallpaperManager(
            parent=self,
            config_data=self.config_data,
            assets_dir=self.assets_dir,
            background_manager=getattr(self, 'background_manager', None),
        )
        # Chiamare self.video_wallpaper_manager.initialize(overlay=self.overlay)
        # subito dopo self.background_manager.initialize(...) nel tuo showEvent/__init__.

    launcher_class.__init__ = new_init

    original_close = launcher_class.closeEvent

    def new_close_event(self, event):
        if hasattr(self, 'video_wallpaper_manager'):
            self.video_wallpaper_manager.cleanup()
        original_close(self, event)

    launcher_class.closeEvent = new_close_event

    original_resize = getattr(launcher_class, 'resizeEvent', None)

    def new_resize_event(self, event):
        if original_resize:
            original_resize(self, event)
        if hasattr(self, 'video_wallpaper_manager'):
            self.video_wallpaper_manager.resize_to_parent()

    launcher_class.resizeEvent = new_resize_event
