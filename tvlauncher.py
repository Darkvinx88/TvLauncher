import sys
import json
import subprocess
import os
import winreg
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QDialog, QLineEdit, QMessageBox, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QProgressBar, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPoint, QSize,
    QParallelAnimationGroup, QTimer, QCoreApplication,
    QThread, pyqtSignal
)
from PyQt6.QtGui import QPixmap, QFont, QKeyEvent, QPainter, QColor, QIcon
import psutil

# Try to import pygame for joystick support
try:
    import pygame
    JOYSTICK_AVAILABLE = True
except ImportError:
    JOYSTICK_AVAILABLE = False
    print("Warning: pygame not installed. Joystick support disabled.")
    print("Install with: pip install pygame")

# Try to import requests for image downloading
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Online image search disabled.")
    print("Install with: pip install requests")


class ResponsiveScaling:
    """Sistema di scaling responsive basato sulla risoluzione"""
   
    def __init__(self):
        # Risoluzione di riferimento (quella su cui hai progettato l'interfaccia)
        self.BASE_WIDTH = 1920
        self.BASE_HEIGHT = 1080
       
        # Ottieni la risoluzione corrente
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
       
        # Calcola il fattore di scala
        width_scale = self.screen_width / self.BASE_WIDTH
        height_scale = self.screen_height / self.BASE_HEIGHT
       
        # Usa il minore dei due per mantenere l'aspect ratio
        self.scale_factor = min(width_scale, height_scale)
       
        print(f"📐 Screen: {self.screen_width}x{self.screen_height}")
        print(f"📐 Scale factor: {self.scale_factor:.2f}")
   
    def scale(self, value):
        """Scala un valore in base alla risoluzione"""
        return int(value * self.scale_factor)
   
    def scale_font(self, base_size):
        """Scala la dimensione del font"""
        return int(base_size * self.scale_factor)


# === IMAGE MANAGER CLASS ===
class ImageManager:
    """Gestisce il download e la cache delle immagini per le app"""
    
    def __init__(self, assets_dir="assets", api_key=None):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(exist_ok=True)
        self.api_key = api_key
        
    def get_app_image(self, app_name, app_path):
        """
        Ottiene l'immagine per un'app.
        Cerca prima in locale, poi online se necessario.
        """
        # 1. Cerca in locale
        local_image = self._find_local_image(app_name)
        if local_image:
            return str(local_image)
        
        # 2. Cerca online (se API key disponibile e requests installato)
        if self.api_key and REQUESTS_AVAILABLE:
            online_image = self._download_from_steamgriddb(app_name)
            if online_image:
                return str(online_image)
        
        # 3. Fallback su icona exe
        return app_path if app_path and os.path.exists(app_path) else None
    
    def _find_local_image(self, app_name):
        """Cerca immagine nella cartella assets locale"""
        safe_name = self._sanitize_filename(app_name)
        app_folder = self.assets_dir / safe_name
        
        if app_folder.exists():
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                image_path = app_folder / f"banner{ext}"
                if image_path.exists():
                    return image_path
                
                image_path = app_folder / f"{safe_name}{ext}"
                if image_path.exists():
                    return image_path
        
        return None
    
    def _download_from_steamgriddb(self, app_name):
        """Scarica immagine da SteamGridDB"""
        if not self.api_key or not REQUESTS_AVAILABLE:
            return None
        
        try:
            from urllib.parse import quote
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 1. Cerca il gioco
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{quote(app_name)}"
            response = requests.get(search_url, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            if not results.get('data'):
                return None
            
            game_id = results['data'][0]['id']
            
            # 2. Ottieni immagini 16:9
            grids_url = f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}"
            params = {
                "dimensions": ["460x215", "920x430"],
                "types": ["static"]
            }
            grids_response = requests.get(grids_url, headers=headers, params=params, timeout=5)
            
            if grids_response.status_code != 200:
                return None
            
            grids = grids_response.json()
            if not grids.get('data'):
                return None
            
            # 3. Scarica la prima immagine
            image_url = grids['data'][0]['url']
            image_data = requests.get(image_url, timeout=10).content
            
            # 4. Salva in locale
            safe_name = self._sanitize_filename(app_name)
            app_folder = self.assets_dir / safe_name
            app_folder.mkdir(exist_ok=True)
            
            ext = '.png' if 'png' in image_url.lower() else '.jpg'
            image_path = app_folder / f"banner{ext}"
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            print(f"✅ Downloaded image for: {app_name}")
            return image_path
            
        except Exception as e:
            print(f"❌ Error downloading image for {app_name}: {e}")
            return None
    
    def _sanitize_filename(self, name):
        """Rimuove caratteri non validi per nomi file"""
        safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        return safe.strip().replace(' ', '_')


# === API KEY DIALOG ===
class ApiKeyDialog(QDialog):
    def __init__(self, current_key="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("SteamGridDB API Key")
        self.setModal(True)
        self.setFixedSize(600, 300)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a; }
            QLabel { color: white; font-size: 14px; }
            QLineEdit { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: 10px; 
                border-radius: 8px; 
                font-size: 14px; 
            }
            QPushButton { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: 12px 30px; 
                border-radius: 8px; 
                font-size: 14px; 
                font-weight: bold; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🔑 SteamGridDB API Key")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info text
        info = QLabel(
            "Per scaricare automaticamente le immagini 16:9:\n\n"
            "1. Vai su steamgriddb.com\n"
            "2. Crea un account gratuito\n"
            "3. Vai in Preferences → API\n"
            "4. Genera una API Key e incollala qui sotto"
        )
        info.setStyleSheet("color: #aaa; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # API Key input
        key_label = QLabel("API Key:")
        layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setText(current_key)
        self.key_input.setPlaceholderText("Incolla la tua API key qui...")
        layout.addWidget(self.key_input)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.save_btn = QPushButton("Salva")
        self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Custom key handling
        self.confirm_buttons = [self.save_btn, self.cancel_btn]
        self.confirm_index = [0]
        self.update_confirm_focus()
    
    def update_confirm_focus(self):
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;

                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
    
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.confirm_index[0] = (self.confirm_index[0] - 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Right:
            self.confirm_index[0] = (self.confirm_index[0] + 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.confirm_buttons[self.confirm_index[0]].click()
        elif key == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def get_api_key(self):
        return self.key_input.text().strip()


# === FUNZIONE UTILITY PER ARROTONDARE PIXMAP SENZA BORDO NERO ===
def rounded_pixmap(original_path, width, height, radius):
    """Restituisce un QPixmap arrotondato con sfondo trasparente e senza bordi neri"""
    pixmap = QPixmap(original_path)
    if pixmap.isNull():
        return None
    scaled = pixmap.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    result = QPixmap(scaled.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("white"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, scaled.width(), scaled.height(), radius, radius)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return result


class ProgramScanner(QThread):
    """Background thread per scansionare i programmi installati SENZA download immagini"""
    program_found = pyqtSignal(dict)
    scan_complete = pyqtSignal()
    progress_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
    
    def _find_best_exe(self, directory, app_name):
        """Trova l'exe migliore in una directory usando euristiche intelligenti"""
        if not os.path.isdir(directory):
            return None
        
        try:
            exe_files = []
            for f in os.listdir(directory):
                if f.lower().endswith('.exe'):
                    exe_files.append(f)
            
            if not exe_files:
                return None
            
            # Filtri per escludere exe indesiderati
            bad_keywords = [
                'unins', 'uninst', 'uninstall', 'setup', 'install', 'update', 
                'updater', 'launcher', 'crash', 'report', 'helper', 'service',
                'background', 'agent', 'stub', 'bootstrap', 'redist'
            ]
            
            # Prima passata: rimuovi exe chiaramente sbagliati
            good_exes = []
            for exe in exe_files:
                exe_lower = exe.lower()
                if not any(bad in exe_lower for bad in bad_keywords):
                    good_exes.append(exe)
            
            if not good_exes:
                # Se abbiamo filtrato tutto, usa il primo che non è uninstaller
                for exe in exe_files:
                    if 'unins' not in exe.lower():
                        return os.path.join(directory, exe)
                return None
            
            # Seconda passata: trova il migliore
            app_name_clean = app_name.lower().replace(' ', '').replace('-', '').replace('_', '')
            
            # 1. Cerca exe con nome simile all'app
            for exe in good_exes:
                exe_clean = exe.lower().replace('.exe', '').replace(' ', '').replace('-', '').replace('_', '')
                if exe_clean == app_name_clean or app_name_clean in exe_clean:
                    return os.path.join(directory, exe)
            
            # 2. Cerca exe con parole chiave del nome app
            app_words = app_name.lower().split()
            for exe in good_exes:
                exe_lower = exe.lower()
                if any(word in exe_lower and len(word) > 3 for word in app_words):
                    return os.path.join(directory, exe)
            
            # 3. Preferisci exe più corti (di solito sono i principali)
            good_exes.sort(key=len)
            return os.path.join(directory, good_exes[0])
            
        except Exception as e:
            print(f"Error finding best exe in {directory}: {e}")
            return None

    def run(self):
        seen_names = set()

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0].strip()
                        except:
                            winreg.CloseKey(subkey)
                            continue

                        exe_path = None
                        icon_path = None

                        # Icona
                        try:
                            val = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            icon_path = val.strip('"').split(',')[0]
                        except:
                            pass

                        # Percorso eseguibile da InstallLocation
                        try:
                            val = winreg.QueryValueEx(subkey, "InstallLocation")[0].strip()
                            if val:
                                exe_path = self._find_best_exe(val, name)
                        except:
                            pass

                        # Fallback su UninstallString
                        if not exe_path:
                            try:
                                val = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                if "unins" in val.lower():
                                    parts = val.split('"')
                                    for p in parts:
                                        if p.lower().endswith('.exe'):
                                            dir_path = os.path.dirname(p)
                                            exe_path = self._find_best_exe(dir_path, name)
                                            if exe_path:
                                                break
                            except:
                                pass

                        if name and exe_path and os.path.exists(exe_path):
                            if name.lower() not in seen_names:
                                seen_names.add(name.lower())
                                
                                self.progress_update.emit(f"Trovato: {name}")
                                final_icon = icon_path if icon_path and os.path.exists(icon_path) else exe_path
                                
                                program_data = {
                                    'name': name,
                                    'path': exe_path,
                                    'icon': final_icon
                                }
                                self.program_found.emit(program_data)

                        winreg.CloseKey(subkey)
                    except:
                        continue
                winreg.CloseKey(key)
            except:
                continue

        # Start Menu shortcuts
        start_menu_paths = [
            os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)")
        ]
        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                self.scan_shortcuts(start_path, seen_names)

        self.scan_complete.emit()

    def scan_shortcuts(self, directory, seen_names):
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.lnk'):
                        try:
                            shortcut_path = os.path.join(root, file)
                            shortcut = shell.CreateShortCut(shortcut_path)
                            target = shortcut.Targetpath
                            if target and target.lower().endswith('.exe') and os.path.exists(target):
                                name = Path(file).stem
                                if name.lower() not in seen_names:
                                    seen_names.add(name.lower())
                                    
                                    self.progress_update.emit(f"Trovato: {name}")
                                    
                                    program_data = {
                                        'name': name,
                                        'path': target,
                                        'icon': target
                                    }
                                    self.program_found.emit(program_data)
                        except:
                            continue
        except ImportError:
            pass


class ProgramScanDialog(QDialog):
    def __init__(self, image_manager=None, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.setWindowTitle("Scansiona Programmi Installati")
        self.setModal(True)
        self.setFixedSize(700, 650)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 8px; border-radius: 8px; font-size: 14px; }
            QListWidget { background-color: #2a2a2a; color: white; border: 2px solid #444; border-radius: 8px; font-size: 14px; padding: 5px; }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #3a3a3a; }
            QListWidget::item:hover { background-color: #333; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #3a3a3a;} 
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        self.title_label = QLabel("Scansione programmi installati in corso...")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 12px;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

        # Barra di ricerca
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtra per nome...")
        self.search_input.textChanged.connect(self.filter_list)
        search_box.addWidget(self.search_input)
        layout.addLayout(search_box)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)

        self.info_label = QLabel("Seleziona i programmi da aggiungere (Ctrl/Shift per multipli)")
        self.info_label.setStyleSheet("color: #aaa; font-size: 13px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Aggiungi Selezionati")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Annulla")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.list_widget.itemSelectionChanged.connect(self.update_add_button)

        # Avvia scansione SENZA ImageManager
        self.scanner = ProgramScanner()
        self.scanner.program_found.connect(self.add_item)
        self.scanner.scan_complete.connect(self.scan_done)
        self.scanner.progress_update.connect(self.update_progress)
        self.scanner.start()

    def add_item(self, data):
        item = QListWidgetItem(f"📦 {data['name']}")
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.list_widget.addItem(item)
        self.title_label.setText(f"Trovati {self.list_widget.count()} programmi")

    def scan_done(self):
        self.title_label.setText(f"Scansione completata — Trovati {self.list_widget.count()} programmi")
        self.progress_label.setText("")
        self.list_widget.sortItems(Qt.SortOrder.AscendingOrder)
    
    def update_progress(self, message):
        self.progress_label.setText(message)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def update_add_button(self):
        selected = len(self.list_widget.selectedItems())
        self.add_btn.setEnabled(selected > 0)
        self.info_label.setText(f"{selected} selezionati" if selected > 0 else "Seleziona i programmi da aggiungere")

    def get_selected(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.list_widget.selectedItems()]


# ==================================
# === NUOVO WORKER PER DOWNLOAD ===
# ==================================
class DownloadWorker(QThread):
    """Worker thread per scaricare immagini in background"""
    progress_update = pyqtSignal(str, int) # Messaggio, percentuale
    app_ready = pyqtSignal(dict) # Invia un'app completa
    finished = pyqtSignal()

    def __init__(self, selected_programs, image_manager, existing_app_names):
        super().__init__()
        self.selected = selected_programs
        self.image_manager = image_manager
        self.existing = existing_app_names
        self.is_running = True

    def run(self):
        # Filtra solo i programmi non già esistenti
        to_download = []
        for prog in self.selected:
            if prog['name'].lower() not in self.existing:
                 to_download.append(prog)
        
        total = len(to_download)
        if total == 0:
            self.progress_update.emit("Programmi già presenti.", 100)
            self.finished.emit()
            return

        for i, prog in enumerate(to_download):
            if not self.is_running:
                break
            
            percent = int((i + 1) / total * 100)
            self.progress_update.emit(f"Scaricando per: {prog['name']}...", percent)
            
            # Scarica immagine 16:9 (se API key c'è)
            if self.image_manager.api_key and REQUESTS_AVAILABLE:
                image_result = self.image_manager.get_app_image(prog['name'], prog['path'])
                if image_result:
                    prog['icon'] = image_result
            
            self.app_ready.emit(prog) # Invia l'app al thread principale
        
        if self.is_running:
            self.progress_update.emit("Completato!", 100)
        else:
            self.progress_update.emit("Annullato.", 100)
            
        self.finished.emit()

    def stop(self):
        """Ferma il worker in modo sicuro"""
        print("Richiesta interruzione worker")
        self.is_running = False


class AppTile(QWidget):
    def __init__(self, app_data, scaling, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.scaling = scaling
        self.is_focused = False
       
        # === INIZIO OTTIMIZZAZIONE #1: CACHE PIXMAP ===
        self._normal_pixmap = None
        self._focused_pixmap = None
        # === FINE OTTIMIZZAZIONE #1 ===
       
        # Dimensioni scalate
        self.normal_width = self.scaling.scale(360)
        self.normal_height = self.scaling.scale(260)
        self.focused_width = self.scaling.scale(400)
        self.focused_height = self.scaling.scale(288)
       
        self.normal_img_width = self.scaling.scale(360)
        self.normal_img_height = self.scaling.scale(203)
        self.focused_img_width = self.scaling.scale(400)
        self.focused_img_height = self.scaling.scale(225)
       
        self.border_radius = self.scaling.scale(24)
       
        self.setFixedSize(self.normal_width, self.normal_height)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.normal_img_width, self.normal_img_height)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # === OTTIMIZZAZIONE #1: Rimossa generazione pixmap da qui ===
        # La generazione è spostata in set_focused
        
        self.image_label.setStyleSheet(f"""
            QLabel {{
                background-color: #1a1a1a;
                border-radius: {self.border_radius}px;
                color: #cccccc;
                font-size: {self.scaling.scale_font(18)}px;
                font-weight: 600;
            }}
        """)
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(self.scaling.scale(15))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(self.scaling.scale(4))
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.image_label.setGraphicsEffect(self.shadow)
        layout.addWidget(self.image_label)
        
        self.name_label = QLabel(app_data['name'])
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setMaximumWidth(self.normal_width)
        self.name_label.setStyleSheet(f"""
            QLabel {{
                color: #999999;
                font-size: {self.scaling.scale_font(14)}px;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.name_label)
        self.setLayout(layout)
        
        # === OTTIMIZZAZIONE #1: Popola la cache iniziale ===
        self.set_focused(False)

    def set_focused(self, focused):
        self.is_focused = focused
        icon_path = self.app_data.get('icon')
        
        if focused:
            self.setFixedSize(self.focused_width, self.focused_height)
            self.image_label.setFixedSize(self.focused_img_width, self.focused_img_height)
            
            # === INIZIO OTTIMIZZAZIONE #1: USA CACHE FOCUSED ===
            if self._focused_pixmap is None and icon_path and Path(icon_path).exists():
                # Genera solo se non è in cache
                self._focused_pixmap = rounded_pixmap(
                    icon_path, self.focused_img_width, self.focused_img_height, self.border_radius
                )
            
            if self._focused_pixmap:
                self.image_label.setPixmap(self._focused_pixmap)
            else:
                self.image_label.setText(self.app_data['name']) # Fallback
            # === FINE OTTIMIZZAZIONE #1 ===
            
            self.image_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #1a1a1a;
                    border: {self.scaling.scale(3)}px solid #ffffff;
                    border-radius: {self.border_radius}px;
                    color: #ffffff;
                    font-size: {self.scaling.scale_font(18)}px;
                    font-weight: 600;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                QLabel {{
                    color: #ffffff;
                    font-size: {self.scaling.scale_font(15)}px;
                    font-weight: 600;
                }}
            """)
            self.shadow.setBlurRadius(self.scaling.scale(25))
            self.shadow.setYOffset(self.scaling.scale(8))
        else:
            self.setFixedSize(self.normal_width, self.normal_height)
            self.image_label.setFixedSize(self.normal_img_width, self.normal_img_height)
            
            # === INIZIO OTTIMIZZAZIONE #1: USA CACHE NORMALE ===
            if self._normal_pixmap is None and icon_path and Path(icon_path).exists():
                # Genera solo se non è in cache
                self._normal_pixmap = rounded_pixmap(
                    icon_path, self.normal_img_width, self.normal_img_height, self.border_radius
                )
            
            if self._normal_pixmap:
                self.image_label.setPixmap(self._normal_pixmap)
            else:
                self.image_label.setText(self.app_data['name']) # Fallback
            # === FINE OTTIMIZZAZIONE #1 ===
            
            self.image_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #1a1a1a;
                    border-radius: {self.border_radius}px;
                    color: #cccccc;
                    font-size: {self.scaling.scale_font(18)}px;
                    font-weight: 600;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                QLabel {{
                    color: #999999;
                    font-size: {self.scaling.scale_font(14)}px;
                }}
            """)
            self.shadow.setBlurRadius(self.scaling.scale(15))
            self.shadow.setYOffset(self.scaling.scale(4))


class SystemMenuDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        parent_rect = parent.geometry()
        dialog_width = 250
        dialog_height = 100
        self.setGeometry(
            parent_rect.width() - dialog_width - 40,
            parent_rect.height() - dialog_height - 40,
            dialog_width,
            dialog_height
        )
        self.current_index = 0
        self.buttons = []
        main_widget = QWidget()
        main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 50px;
            }
        """)
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setFixedSize(60, 60)
        self.restart_btn.setToolTip("Restart")
        self.buttons.append(("restart", self.restart_btn))
        layout.addWidget(self.restart_btn)
        self.shutdown_btn = QPushButton("⏻")
        self.shutdown_btn.setFixedSize(60, 60)
        self.shutdown_btn.setToolTip("Shutdown")
        self.buttons.append(("shutdown", self.shutdown_btn))
        layout.addWidget(self.shutdown_btn)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(60, 60)
        self.close_btn.setToolTip("Close")
        self.buttons.append(("close", self.close_btn))
        layout.addWidget(self.close_btn)
        for action, btn in self.buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 3px solid #444;
                    border-radius: 30px;
                    font-size: 24px;
                }
                
                QPushButton:hover {
                        background-color: #3a3a3a;}
            """)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_widget)
        self.setLayout(dialog_layout)
        self.update_focus()
   
    def update_focus(self):
        for i, (action, btn) in enumerate(self.buttons):
            if i == self.current_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        color: #1a1a1a;
                        border: 4px solid white;
                        border-radius: 30px;
                        font-size: 24px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 3px solid #444;
                        border-radius: 30px;
                        font-size: 24px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
   
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Right:
            self.current_index = (self.current_index + 1) % len(self.buttons)
            self.update_focus()
        elif key == Qt.Key.Key_Left:
            self.current_index = (self.current_index - 1) % len(self.buttons)
            self.update_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            action = self.buttons[self.current_index][0]
            if action == "close":
                self.reject()
            else:
                self.selected_action = action
                self.accept()
        elif key == Qt.Key.Key_Escape or key == Qt.Key.Key_M:
            self.reject()
        else:
            super().keyPressEvent(event)
   
    def get_selected_action(self):
        return getattr(self, 'selected_action', 'close')


class EditAppDialog(QDialog):
    def __init__(self, app_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit App")
        self.setModal(True)
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 10px; border-radius: 8px; font-size: 14px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        name_label = QLabel("App Name:")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setText(app_data.get('name', ''))
        layout.addWidget(self.name_input)
        exe_label = QLabel("Executable Path:")
        exe_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(exe_label)
        exe_container = QHBoxLayout()
        exe_container.setSpacing(10)
        self.exe_input = QLineEdit()
        self.exe_input.setText(app_data.get('path', ''))
        exe_container.addWidget(self.exe_input, 3)
        self.exe_button = QPushButton("Browse")
        self.exe_button.clicked.connect(self.browse_exe)
        exe_container.addWidget(self.exe_button, 1)
        layout.addLayout(exe_container)
        icon_label = QLabel("Icon Image (16:9 recommended):")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(icon_label)
        icon_container = QHBoxLayout()
        icon_container.setSpacing(10)
        self.icon_input = QLineEdit()
        self.icon_input.setText(app_data.get('icon', ''))
        icon_container.addWidget(self.icon_input, 3)
        self.icon_button = QPushButton("Browse")
        self.icon_button.clicked.connect(self.browse_icon)
        icon_container.addWidget(self.icon_button, 1)
        layout.addLayout(icon_container)
        layout.addSpacing(20)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        self.save_button = QPushButton("Save")
        self.save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.confirm_buttons = [self.save_button, self.cancel_button]
        self.confirm_index = [0]
        self.update_confirm_focus()
   
    def update_confirm_focus(self):
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;;
                        color: white;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                         }
                    QPushButton:hover { background-color: #3a3a3a; }    
                    
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                   QPushButton:hover { background-color: #3a3a3a; }    
                    
                """)
   
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.confirm_index[0] = (self.confirm_index[0] - 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Right:
            self.confirm_index[0] = (self.confirm_index[0] + 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.confirm_buttons[self.confirm_index[0]].click()
        elif key == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
   
    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.exe_input.setText(file_path)
   
    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_path:
            self.icon_input.setText(file_path)
   
    def get_app_data(self):
        return {
            'name': self.name_input.text(),
            'path': self.exe_input.text(),
            'icon': self.icon_input.text()
        }


class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New App")
        self.setModal(True)
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 10px; border-radius: 8px; font-size: 14px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
            
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        name_label = QLabel("App Name:")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)
        exe_label = QLabel("Executable Path:")
        exe_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(exe_label)
        exe_container = QHBoxLayout()
        exe_container.setSpacing(10)
        self.exe_input = QLineEdit()
        exe_container.addWidget(self.exe_input, 3)
        self.exe_button = QPushButton("Browse")
        self.exe_button.clicked.connect(self.browse_exe)
        exe_container.addWidget(self.exe_button, 1)
        layout.addLayout(exe_container)
        icon_label = QLabel("Icon Image (16:9 recommended):")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(icon_label)
        icon_container = QHBoxLayout()
        icon_container.setSpacing(10)
        self.icon_input = QLineEdit()
        icon_container.addWidget(self.icon_input, 3)
        self.icon_button = QPushButton("Browse")
        self.icon_button.clicked.connect(self.browse_icon)
        icon_container.addWidget(self.icon_button, 1)
        layout.addLayout(icon_container)
        layout.addSpacing(20)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        self.ok_button = QPushButton("Add")
        self.ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.confirm_buttons = [self.ok_button, self.cancel_button]
        self.confirm_index = [0]
        self.update_confirm_focus()
   
    def update_confirm_focus(self):
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;;
                    }
                    QPushButton:hover { background-color: #3a3a3a;}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #3a3a3a;}
                """)
   
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.confirm_index[0] = (self.confirm_index[0] - 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Right:
            self.confirm_index[0] = (self.confirm_index[0] + 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.confirm_buttons[self.confirm_index[0]].click()
        elif key == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
   
    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.exe_input.setText(file_path)
            if not self.name_input.text():
                self.name_input.setText(Path(file_path).stem)
   
    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_path:
            self.icon_input.setText(file_path)
   
    def get_app_data(self):
        return {
            'name': self.name_input.text(),
            'path': self.exe_input.text(),
            'icon': self.icon_input.text()
        }


class TVLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inizializza il sistema di scaling responsive
        self.scaling = ResponsiveScaling()
        
        self.config_file = Path("launcher_apps.json")
        self.config_data = self.load_config()
        self.apps = self.config_data.get('apps', [])
        self.background_image = self.config_data.get('background', '')
        self.steamgriddb_api_key = self.config_data.get('steamgriddb_api_key', '')
        self.image_manager = ImageManager(api_key=self.steamgriddb_api_key)
        self.current_index = 0
        self.tiles = []
        self.menu_button_index = 0
        self.is_in_menu = False
        self.animation_group = None
        self.is_animating = False
        self.joystick = None
        self.joystick_timer = None
        self.axis_deadzone = 0.2
        self.last_axis_state = {'x': 0, 'y': 0}
        self.last_hat = (0, 0)
        self.button_cooldown = {}
        self.axis_cooldown = 0
        self.launched_process = None
        self.process_check_timer = None
        self.inputs_enabled = True
        
        # === INIZIO OTTIMIZZAZIONE #2: INIT VAR WORKER ===
        self.download_worker = None
        self.progress_dialog = None
        self.added_count = 0
        # === FINE OTTIMIZZAZIONE #2 ===
        
        if JOYSTICK_AVAILABLE:
            pygame.init()
            self.init_joystick()
        self.joystick_detection_timer = QTimer()
        self.joystick_detection_timer.timeout.connect(self.detect_joystick)
        self.joystick_detection_timer.start(5000)
        self.init_ui()
        self.build_infinite_carousel()
    
    def init_joystick(self):
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                print(f"Joystick connected: {self.joystick.get_name()}")
                self.joystick_timer = QTimer()
                self.joystick_timer.timeout.connect(self.poll_joystick)
                self.joystick_timer.start(12)
            else:
                print("No joystick detected")
        except Exception as e:
            print(f"Error initializing joystick: {e}")
   
    def detect_joystick(self):
        try:
            pygame.joystick.init()
            count = pygame.joystick.get_count()
            if count > 0:
                if self.joystick is None:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    print(f"Joystick connected (late detection): {self.joystick.get_name()}")
                    if self.joystick_timer is None:
                        self.joystick_timer = QTimer()
                        self.joystick_timer.timeout.connect(self.poll_joystick)
                        self.joystick_timer.start(12)
            else:
                if self.joystick is not None:
                    print("Joystick disconnected")
                    if self.joystick_timer:
                        self.joystick_timer.stop()
                        self.joystick_timer = None
                    self.joystick.quit()
                    self.joystick = None
        except Exception as e:
            print(f"Error during joystick detection: {e}")
            if self.joystick is not None:
                print("Assuming joystick disconnected due to error")
                if self.joystick_timer:
                    self.joystick_timer.stop()
                    self.joystick_timer = None
                self.joystick = None
   
    def poll_joystick(self):
        if not self.joystick or not self.inputs_enabled:
            return
        try:
            pygame.event.pump()
            x_axis = self.joystick.get_axis(0)
            y_axis = self.joystick.get_axis(1)
            if self.joystick.get_numhats() > 0:
                hat = self.joystick.get_hat(0)
                if hat != (0, 0):
                    if self.axis_cooldown > 0:
                        self.axis_cooldown -= 1 
                    elif hat != self.last_hat:
                        if hat[0] == 1:
                            self.simulate_key_press(Qt.Key.Key_Right)
                        elif hat[0] == -1:
                            self.simulate_key_press(Qt.Key.Key_Left)
                        if hat[1] == 1:
                            self.simulate_key_press(Qt.Key.Key_Up)
                        elif hat[1] == -1:
                            self.simulate_key_press(Qt.Key.Key_Down)
                        self.axis_cooldown = 2
                        self.last_hat = hat
                else:
                    self.last_hat = hat
                    self.axis_cooldown = 0
            if abs(x_axis) > self.axis_deadzone or abs(y_axis) > self.axis_deadzone:
                self.handle_axis(x_axis, y_axis)
            else:
                self.axis_cooldown = 0
                self.last_axis_state = {'x': 0, 'y': 0}
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    self.handle_button(i)
        except (pygame.error, ValueError) as e:
            print(f"Joystick polling error, assuming disconnected: {e}")
            if self.joystick_timer:
                self.joystick_timer.stop()
                self.joystick_timer = None
            self.joystick = None
        except Exception as e:
            print(f"Error polling joystick: {e}")
   
    def handle_axis(self, x_axis, y_axis):
        if self.axis_cooldown > 0:
            self.axis_cooldown -= 1
            return
        if abs(x_axis) > self.axis_deadzone:
            if x_axis > 0 and self.last_axis_state['x'] <= 0:
                self.simulate_key_press(Qt.Key.Key_Right)
                self.axis_cooldown = 2
            elif x_axis < 0 and self.last_axis_state['x'] >= 0:
                self.simulate_key_press(Qt.Key.Key_Left)
                self.axis_cooldown = 2
            self.last_axis_state['x'] = x_axis
        if abs(y_axis) > self.axis_deadzone:
            if y_axis > 0 and self.last_axis_state['y'] <= 0:
                self.simulate_key_press(Qt.Key.Key_Down)
                self.axis_cooldown = 2
            elif y_axis < 0 and self.last_axis_state['y'] >= 0:
                self.simulate_key_press(Qt.Key.Key_Up)
                self.axis_cooldown = 2
            self.last_axis_state['y'] = y_axis
   
    def handle_button(self, button_index):
        current_time = pygame.time.get_ticks()
        if button_index in self.button_cooldown:
            if current_time - self.button_cooldown[button_index] < 300:
                return
        self.button_cooldown[button_index] = current_time
        if button_index == 0:
            self.simulate_key_press(Qt.Key.Key_Return)
        elif button_index == 1:
            self.simulate_key_press(Qt.Key.Key_Escape)
        elif button_index == 2:
            self.simulate_key_press(Qt.Key.Key_E)
        elif button_index == 3:
            self.simulate_key_press(Qt.Key.Key_Delete)
        elif button_index == 9:
            self.simulate_key_press(Qt.Key.Key_Down if not self.is_in_menu else Qt.Key.Key_Up)
   
    def simulate_key_press(self, key):
        event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
        active_win = QApplication.activeWindow()
        if active_win:
            QCoreApplication.postEvent(active_win, event)
   
    def disable_inputs(self):
        self.inputs_enabled = False
        print("🎮 Inputs disabled - App in focus")
   
    def enable_inputs(self):
        self.inputs_enabled = True
        print("🎮 Inputs enabled - Launcher in focus")
   
    def check_launched_process(self):
        if self.launched_process is None:
            return
        try:
            process = psutil.Process(self.launched_process)
            if not process.is_running():
                self.on_app_closed()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.on_app_closed()
   
    def on_app_closed(self):
        print("✅ App closed - Re-enabling inputs")
        self.launched_process = None
        if self.process_check_timer:
            self.process_check_timer.stop()
            self.process_check_timer = None
        self.enable_inputs()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def init_ui(self):
        self.setWindowTitle("TV Launcher")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if JOYSTICK_AVAILABLE and self.joystick:
            print(f"🎮 Joystick ready: {self.joystick.get_name()}")
        elif JOYSTICK_AVAILABLE:
            print("⚠️ No joystick detected - using keyboard only")
        else:
            print("⚠️ Pygame not installed - joystick support disabled")
        screen = QApplication.primaryScreen().geometry()
        self.setFixedSize(screen.width(), screen.height())
        self.update_background()
        overlay = QWidget(self)
        overlay.setGeometry(0, 0, screen.width(), screen.height())
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        overlay.lower()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay = overlay
        main_widget = QWidget()
        main_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        main_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Layout principale con margini scalati
        main_layout.setContentsMargins(
            self.scaling.scale(5),
            self.scaling.scale(48),
            self.scaling.scale(5),
            self.scaling.scale(48)
        )
        main_layout.setSpacing(0)
        header_layout = QHBoxLayout()
        
        # Header con margini scalati
        header_layout.setContentsMargins(
            self.scaling.scale(43), 0,
            self.scaling.scale(43), 0
        )
        
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'Italian_Italy')
            except:
                pass
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d %B %Y")
        parts = date_str.split()
        if len(parts) >= 2:
            parts[1] = parts[1].capitalize()
            date_str = " ".join(parts)
        time_label = QLabel(time_str)
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {self.scaling.scale_font(48)}px;
            font-weight: 700;
        """)
        date_label = QLabel(date_str)
        date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(22)}px;
            font-weight: 500;
        """)
        clock_layout = QVBoxLayout()
        clock_layout.addWidget(time_label)
        clock_layout.addWidget(date_label)
        header_layout.addLayout(clock_layout)
        header_layout.addStretch()
        
        # Stile pulsanti header scalato
        btn_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.7);
                border: none;
                padding: {self.scaling.scale(8)}px {self.scaling.scale(16)}px;
                
                font-size: {self.scaling.scale_font(16)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
            }}
        """
        
        # API KEY BUTTON
        api_btn = QPushButton()
        api_btn.setIcon(QIcon("assets/icons/key.png"))
        api_btn.setIconSize(QSize(self.scaling.scale(23), self.scaling.scale(23)))

        api_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        api_btn.setFixedSize(self.scaling.scale(48), self.scaling.scale(48))

        api_btn.setToolTip("SteamGridDB API Key")
        api_btn.clicked.connect(self.set_api_key)

        header_layout.addWidget(api_btn)
        
        scan_btn = QPushButton()
        scan_btn.setIcon(QIcon("assets/icons/search.png"))
        scan_btn.setIconSize(QSize(self.scaling.scale(23), self.scaling.scale(23)))

        
        scan_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        scan_btn.setFixedSize(self.scaling.scale(48), self.scaling.scale(48))

        scan_btn.setToolTip("Search Your Apps Here")
        scan_btn.clicked.connect(self.scan_programs)

        header_layout.addWidget(scan_btn)
        
        add_btn = QPushButton()
        add_btn.setIcon(QIcon("assets/icons/plus.png"))
        add_btn.setIconSize(QSize(self.scaling.scale(23), self.scaling.scale(23)))

        add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        add_btn.setFixedSize(self.scaling.scale(48), self.scaling.scale(48))

        
        add_btn.setToolTip("Add Your Apps Here")
        add_btn.clicked.connect(self.add_app)
        header_layout.addWidget(add_btn)
        
        
        bg_btn = QPushButton()
        bg_btn.setIcon(QIcon("assets/icons/image.png"))
        bg_btn.setIconSize(QSize(self.scaling.scale(23), self.scaling.scale(23)))

        
        bg_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        bg_btn.setFixedSize(self.scaling.scale(48), self.scaling.scale(48))

        bg_btn.setToolTip("Set a Background Here")
        bg_btn.clicked.connect(self.set_background)
        header_layout.addWidget(bg_btn)

        api_btn.setStyleSheet(btn_style)
        scan_btn.setStyleSheet(btn_style)
        add_btn.setStyleSheet(btn_style)
        bg_btn.setStyleSheet(btn_style)


        main_layout.addLayout(header_layout)
        main_layout.addSpacing(40)
        main_layout.addStretch(3)
        self.carousel_container = QWidget()
        self.carousel_container.setFixedHeight(self.scaling.scale(310))
        visible_width = (5 * self.scaling.scale(400)) + (4 * self.scaling.scale(5))
        self.carousel_container.setFixedWidth(visible_width)
        self.carousel_container.setStyleSheet("background-color: transparent;")
        
        self.max_visible_tiles = 9
        self.tile_width = self.scaling.scale(360)
        self.tile_spacing = self.scaling.scale(17)
        
        main_layout.addWidget(self.carousel_container, alignment=Qt.AlignmentFlag.AlignCenter)  # cambiato in Center per responsive
        main_layout.addSpacing(20)
        main_layout.addStretch(1)
        menu_container = QWidget()
        menu_container.setStyleSheet("background-color: transparent;")
        menu_layout = QHBoxLayout(menu_container)
        menu_layout.setContentsMargins(0, 0, 0, 20)
        menu_layout.addStretch()
        button_widget = QWidget()
        button_widget.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(20, 20, 20, 0.6);
                border-radius: {self.scaling.scale(32)}px;
            }}
        """)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(self.scaling.scale(12))
        button_layout.setContentsMargins(
            self.scaling.scale(16),
            self.scaling.scale(16),
            self.scaling.scale(16),
            self.scaling.scale(16)
        )
        
        btn_size = self.scaling.scale(50)
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setFixedSize(btn_size, btn_size)
        self.restart_btn.setToolTip("Restart")
        self.restart_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.restart_btn)
        self.shutdown_btn = QPushButton("OFF")
        self.shutdown_btn.setFixedSize(btn_size, btn_size)
        self.shutdown_btn.setToolTip("Shutdown")
        self.shutdown_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.shutdown_btn)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(btn_size, btn_size)
        self.close_btn.setToolTip("Close")
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.close_btn)
        self.menu_buttons = [
            ("restart", self.restart_btn),
            ("shutdown", self.shutdown_btn),
            ("close", self.close_btn)
        ]
        for action, btn in self.menu_buttons:
            btn.clicked.connect(lambda checked, a=action: self.execute_menu_action_direct(a))
        
        # Stili menu scalati (separati per shutdown)
        for action, btn in self.menu_buttons:
            if btn == self.shutdown_btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: rgba(255, 255, 255, 0.7);
                        border: {self.scaling.scale(2)}px solid transparent;
                        border-radius: {self.scaling.scale(25)}px;
                        font-size: {self.scaling.scale_font(14)}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: rgba(255, 255, 255, 0.7);
                        border: {self.scaling.scale(2)}px solid transparent;
                        border-radius: {self.scaling.scale(25)}px;
                        font-size: {self.scaling.scale_font(24)}px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a; }}
                """)
        
        menu_layout.addWidget(button_widget)
        menu_layout.addStretch()
        main_layout.addWidget(menu_container)
        instructions = QLabel("Navigate: ← → ↑ ↓ or D-Pad/Stick | Launch: Enter/A | Edit: E/X | Delete: Del/Y | Exit: Esc/B")
        instructions.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.3);
            font-size: {self.scaling.scale_font(11)}px;
            background: transparent;
        """)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(instructions)
        main_layout.addSpacing(8)
        self.showFullScreen()
   
    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {'apps': data, 'background': '', 'steamgriddb_api_key': ''}
                    elif isinstance(data, dict):
                        if 'steamgriddb_api_key' not in data:
                            data['steamgriddb_api_key'] = ''
                        return data
                    else:
                        return {'apps': [], 'background': '', 'steamgriddb_api_key': ''}
            except:
                return {'apps': [], 'background': '', 'steamgriddb_api_key': ''}
        return {'apps': [], 'background': '', 'steamgriddb_api_key': ''}
   
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump({
                'apps': self.apps,
                'background': self.background_image,
                'steamgriddb_api_key': self.steamgriddb_api_key
            }, f, indent=2)
   
    def set_api_key(self):
        """Apre il dialog per impostare la API key"""
        dialog = ApiKeyDialog(self.steamgriddb_api_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key = dialog.get_api_key()
            if new_key != self.steamgriddb_api_key:
                self.steamgriddb_api_key = new_key
                self.image_manager = ImageManager(api_key=self.steamgriddb_api_key)
                self.save_config()
                
                if new_key:
                    QMessageBox.information(
                        self,
                        "API Key Salvata",
                        "✅ API Key salvata con successo!\n\n"
                        "Ora puoi scaricare le immagini 16:9\n"
                        "quando aggiungi nuove app al launcher."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "API Key Rimossa",
                        "API Key rimossa. Il launcher userà solo\n"
                        "le immagini locali e le icone degli exe."
                    )
        
        self.setFocus()
        self.activateWindow()
   
    def update_background(self):
        if self.background_image and Path(self.background_image).exists():
            self.setStyleSheet(f"""
                QMainWindow {{
                    background-image: url({self.background_image.replace(chr(92), '/')});
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            if hasattr(self, 'overlay'):
                self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #0f0f0f;
                }
            """)
            if hasattr(self, 'overlay'):
                self.overlay.setStyleSheet("background-color: transparent;")
   
    def set_background(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_path:
            self.background_image = file_path
            self.save_config()
            self.update_background()
        self.setFocus()
        self.activateWindow()
       
    def update_menu_focus(self):
        for i, (action, btn) in enumerate(self.menu_buttons):
            if i == self.menu_button_index:
                if btn == self.shutdown_btn:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.95);
                            color: #000000;
                            border: {self.scaling.scale(2)}px solid white;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: 700;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.95);
                            color: #000000;
                            border: {self.scaling.scale(2)}px solid white;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(24)}px;
                            font-weight: 600;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
                    """)
            else:
                if btn == self.shutdown_btn:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.1);
                            color: rgba(255, 255, 255, 0.7);
                            border: {self.scaling.scale(2)}px solid transparent;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: 600;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.1);
                            color: rgba(255, 255, 255, 0.7);
                            border: {self.scaling.scale(2)}px solid transparent;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(24)}px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
                    """)
   
    def execute_menu_action(self):
        action = self.menu_buttons[self.menu_button_index][0]
        self.execute_menu_action_direct(action)
   
    def execute_menu_action_direct(self, action):
        if action == "close":
            self.close()
        elif action == "restart":
            self.confirm_action("restart")
        elif action == "shutdown":
            self.confirm_action("shutdown")
   
    def confirm_action(self, action):
        action_text = "Restart" if action == "restart" else "Shutdown"
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle(f"Confirm {action_text}")
        confirm_dialog.setModal(True)
        confirm_dialog.setFixedSize(400, 200)
        confirm_dialog.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:focus { background-color: #3a3a3a; border: 3px solid white; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        message = QLabel(f"Are you sure you want to {action.lower()} the computer?")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        yes_btn = QPushButton("Yes")
        yes_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        yes_btn.clicked.connect(confirm_dialog.accept)
        no_btn = QPushButton("No")
        no_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        no_btn.clicked.connect(confirm_dialog.reject)
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        layout.addLayout(button_layout)
        confirm_dialog.setLayout(layout)
        confirm_buttons = [yes_btn, no_btn]
        confirm_index = [1]
        def update_confirm_focus():
            for i, btn in enumerate(confirm_buttons):
                if i == confirm_index[0]:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2a2a2a;
                            color: white;
                            border: 3px solid white;
                            padding: 12px 30px;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #3a3a3a;}
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #2a2a2a;
                            color: white;
                            border: 2px solid #444;
                            padding: 12px 30px;
                            border-radius: 8px;
                            font-size: 14px;
                            font-weight: bold;
                        }
                        QPushButton:hover { background-color: #3a3a3a;}
                    """)
        def confirm_key_handler(event):
            if event.isAutoRepeat():
                return
            key = event.key()
            if key == Qt.Key.Key_Left:
                confirm_index[0] = (confirm_index[0] - 1) % 2
                update_confirm_focus()
            elif key == Qt.Key.Key_Right:
                confirm_index[0] = (confirm_index[0] + 1) % 2
                update_confirm_focus()
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                confirm_buttons[confirm_index[0]].click()
            elif key == Qt.Key.Key_Escape:
                confirm_dialog.reject()
            else:
                super(confirm_dialog.__class__, confirm_dialog).keyPressEvent(event)
        confirm_dialog.keyPressEvent = confirm_key_handler
        update_confirm_focus()
        if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
            self.execute_power_action(action)
   
    def execute_power_action(self, action):
        try:
            if action == "restart":
                subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)
            elif action == "shutdown":
                subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not {action}:\n{str(e)}")
   
    def build_infinite_carousel(self):
        for tile in self.tiles:
            tile.setParent(None)
            tile.deleteLater()
        self.tiles.clear()
        if not self.apps:
            empty_label = QLabel("No apps added yet. Press '+ Add App' to get started!", self.carousel_container)
            empty_label.setStyleSheet("color: #666; font-size: 18px;")
            empty_label.move(0, 100)
            return
        if self.current_index >= len(self.apps):
            self.current_index = 0
        num_apps = len(self.apps)
        center_tile_index = 4
        for i in range(self.max_visible_tiles):
            app_offset = i - center_tile_index
            app_idx = (self.current_index + app_offset) % num_apps
            tile = AppTile(self.apps[app_idx], self.scaling, self.carousel_container)
            tile.app_index = app_idx
            is_focused = (i == center_tile_index)
            tile.set_focused(is_focused)
            self.tiles.append(tile)
        self._position_all_tiles()
        for tile in self.tiles:
            tile.show()
        current_app = self.apps[self.current_index]
   
    def _position_all_tiles(self):
        if not self.tiles:
            return
        center_tile_index = 4
        left_width = 0
        for i in range(center_tile_index):
            left_width += self.tiles[i].width() + self.tile_spacing
        start_x = -left_width - (self.tiles[center_tile_index].width() // 2) + (self.carousel_container.width() // 2) - self.tile_spacing - self.scaling.scale(30)
        x_pos = int(start_x)
        for i, tile in enumerate(self.tiles):
            tile.move(int(x_pos), 0)
            x_pos += tile.width() + self.tile_spacing
   
    def animate_carousel(self, direction):
        if self.is_animating or not self.tiles:
            return
        self.is_animating = True
        shift_distance = self.tile_width + self.tile_spacing
        self.animation_group = QParallelAnimationGroup()
        for tile in self.tiles:
            anim = QPropertyAnimation(tile, b"pos")
            anim.setDuration(250)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            start_pos = tile.pos()
            if direction == "right":
                end_pos = QPoint(start_pos.x() - shift_distance, start_pos.y())
            else:
                end_pos = QPoint(start_pos.x() + shift_distance, start_pos.y())
            anim.setStartValue(start_pos)
            anim.setEndValue(end_pos)
            self.animation_group.addAnimation(anim)
        self.animation_group.finished.connect(lambda: self.reposition_tiles(direction))
        self.animation_group.start()
   
    def reposition_tiles(self, direction):
        num_apps = len(self.apps)
        center_tile_index = 4
        
        if direction == "right":
            first_tile = self.tiles.pop(0)
            new_app_idx = (self.current_index + 4) % num_apps
            first_tile.app_data = self.apps[new_app_idx]
            first_tile.app_index = new_app_idx
            
            # === INIZIO OTTIMIZZAZIONE #1: INVALIDA CACHE ===
            first_tile._normal_pixmap = None
            first_tile._focused_pixmap = None
            # === FINE OTTIMIZZAZIONE #1 ===
            
            first_tile.name_label.setText(self.apps[new_app_idx]['name'])
            first_tile.set_focused(False) # Rigenera la cache _normal_pixmap
            self.tiles.append(first_tile)
        else:
            last_tile = self.tiles.pop()
            new_app_idx = (self.current_index - 4) % num_apps
            last_tile.app_data = self.apps[new_app_idx]
            last_tile.app_index = new_app_idx

            # === INIZIO OTTIMIZZAZIONE #1: INVALIDA CACHE ===
            last_tile._normal_pixmap = None
            last_tile._focused_pixmap = None
            # === FINE OTTIMIZZAZIONE #1 ===
            
            last_tile.name_label.setText(self.apps[new_app_idx]['name'])
            last_tile.set_focused(False) # Rigenera la cache _normal_pixmap
            self.tiles.insert(0, last_tile)
            
        for i, tile in enumerate(self.tiles):
            tile.set_focused(i == center_tile_index) # Rigenera la cache _focused_pixmap per la tile centrale
            
        self._position_all_tiles()
        self.is_animating = False

    # ============================================
    # === INIZIO OTTIMIZZAZIONE #2: METODI WORKER ===
    # ============================================
    def scan_programs(self):
        dialog = ProgramScanDialog(self.image_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected()
            if not selected:
                self.setFocus()
                self.activateWindow()
                return

            # --- NUOVA GESTIONE THREAD ---
            self.added_count = 0 # Resetta il contatore
            self.progress_dialog = QProgressDialog("Ricerca immagini in corso...", "Annulla", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Aggiunta Programmi")
            self.progress_dialog.setFixedSize(self.scaling.scale(450), self.scaling.scale(150))
            self.progress_dialog.setValue(0)
            
            # Stile per il QProgressDialog
            self.progress_dialog.setStyleSheet("""
                QProgressDialog {
                    background-color: #1a1a1a;
                    color: white;
                }
                QProgressDialog QLabel {
                    color: white;
                    font-size: 14px;
                }
                QProgressBar {
                    background-color: #2a2a2a;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #3a3a3a;
                    border-radius: 5px;
                }
                QPushButton {
                    background-color: #2a2a2a; 
                    color: white; 
                    border: 2px solid #444; 
                    padding: 8px 20px; 
                    border-radius: 8px; 
                    font-size: 14px; 
                }
                QPushButton:hover { background-color: #3a3a3a; }
            """)

            existing_names = {app['name'].lower() for app in self.apps}
            
            self.download_worker = DownloadWorker(selected, self.image_manager, existing_names)
            self.download_worker.app_ready.connect(self._on_app_ready_from_scan)
            self.download_worker.progress_update.connect(self._on_download_progress)
            self.download_worker.finished.connect(self._on_download_finished)
            
            # Connetti il pulsante "Annulla"
            self.progress_dialog.canceled.connect(self.download_worker.stop) 
            
            self.download_worker.start()
            self.progress_dialog.show()
            # --- FINE GESTIONE THREAD ---
            
        else:
            # L'utente ha chiuso il ProgramScanDialog
            self.setFocus()
            self.activateWindow()   

    def _on_app_ready_from_scan(self, app_data):
        """Chiamato dal worker per ogni app pronta"""
        self.apps.append(app_data)
        self.added_count += 1
    
    def _on_download_progress(self, message, percent):
        """Aggiorna il progress dialog"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(percent)

    def _on_download_finished(self):
        """Chiamato al termine di tutti i download"""
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        self.save_config()
        self.build_infinite_carousel()
        
        # Mostra messaggio solo se il worker non è stato annullato
        if self.download_worker and self.download_worker.is_running:
            if self.added_count > 0:
                QMessageBox.information(self, "Fatto!", f"Aggiunti {self.added_count} programma(i) con successo!")
            else:
                QMessageBox.information(self, "Info", "Nessun nuovo programma aggiunto (potrebbero essere già presenti).")

        self.download_worker = None # Pulisci il riferimento al worker
        self.added_count = 0 # Resetta contatore
        
        self.setFocus()
        self.activateWindow()
    # ==========================================
    # === FINE OTTIMIZZAZIONE #2: METODI WORKER ===
    # ==========================================
   
    def add_app(self):
        dialog = AddAppDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_data = dialog.get_app_data()
            if app_data['name'] and app_data['path']:
                # NOTA: Questo download è ancora bloccante (come nell'originale)
                # Per ottimizzare anche questo, servirebbe un worker separato
                # per la singola app. Per ora rimane così.
                if (not app_data['icon'] or app_data['icon'] == app_data['path']) and self.image_manager.api_key and REQUESTS_AVAILABLE:
                    print(f"📥 Cercando immagine per: {app_data['name']}")
                    
                    image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
                    if image_result:
                        app_data['icon'] = image_result
                        print(f"✅ Immagine trovata per: {app_data['name']}")
                    else:
                        print(f"⚠️ Nessuna immagine trovata, uso icona exe")
                
                self.apps.append(app_data)
                self.save_config()
                self.build_infinite_carousel()
            else:
                QMessageBox.warning(self, "Invalid Input", "Please provide at least a name and executable path.")
        self.setFocus()
        self.activateWindow()
   
    def edit_current_app(self):
        if not self.apps:
            return
        dialog = EditAppDialog(self.apps[self.current_index], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_data = dialog.get_app_data()
            if app_data['name'] and app_data['path']:
                self.apps[self.current_index] = app_data
                self.save_config()
                self.build_infinite_carousel() # Ricostruisce e rigenera le cache
            else:
                QMessageBox.warning(self, "Invalid Input", "Please provide at least a name and executable path.")
        self.setFocus()
        self.activateWindow()
   
    def remove_current_app(self):
        if not self.apps:
         return

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Remove App")
        msg_box.setText(f"<div style='margin-left:0px; margin-top:10px;'>Remove '<b>{self.apps[self.current_index]['name']}</b>'?</div>")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)

      # Styling only
        msg_box.setStyleSheet("""
        QMessageBox {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 15px 30px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #3a3a3a;
            color: #ffffff;
            padding: 10px 40px;
            border-radius: 8px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #1e90ff;
        }
      """)

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
           self.apps.pop(self.current_index)
        if self.current_index >= len(self.apps) and self.apps:
            self.current_index = len(self.apps) - 1
        elif not self.apps:
            self.current_index = 0
        self.save_config()
        self.build_infinite_carousel()
   
    def launch_current_app(self):
        if not self.apps:
            return
        app = self.apps[self.current_index]
        try:
            process = subprocess.Popen(app['path'], shell=True)
            self.launched_process = process.pid
            self.disable_inputs()
            self.process_check_timer = QTimer()
            self.process_check_timer.timeout.connect(self.check_launched_process)
            self.process_check_timer.start(1000)
            print(f"🚀 Launched: {app['name']} (PID: {process.pid})")
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Could not launch app:\n{str(e)}")
            self.enable_inputs()
   
    def keyPressEvent(self, event: QKeyEvent):
        if not self.inputs_enabled:
            return
        # Non permettere input se il dialog di progresso è attivo
        if self.progress_dialog and self.progress_dialog.isVisible():
            return
            
        key = event.key()
        if event.isAutoRepeat():
            if self.is_in_menu and key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                return
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                return
        if key == Qt.Key.Key_Down:
            if not self.is_in_menu:
                self.is_in_menu = True
                self.menu_button_index = 0
                self.update_menu_focus()
        elif key == Qt.Key.Key_Up:
            if self.is_in_menu:
                self.is_in_menu = False
                for action, btn in self.menu_buttons:
                    if btn == self.shutdown_btn:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(255, 255, 255, 0.1);
                                color: rgba(255, 255, 255, 0.7);
                                border: {self.scaling.scale(2)}px solid transparent;
                                border-radius: {self.scaling.scale(25)}px;
                                font-size: {self.scaling.scale_font(14)}px;
                                font-weight: 600;
                            }}
                            QPushButton:hover {{ background-color: #3a3a3a; }}
                        """)
                    else:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(255, 255, 255, 0.1);
                                color: rgba(255, 255, 255, 0.7);
                                border: {self.scaling.scale(2)}px solid transparent;
                                border-radius: {self.scaling.scale(25)}px;
                                font-size: {self.scaling.scale_font(24)}px;
                                font-weight: 500;
                            }}
                            QPushButton:hover {{ background-color: #3a3a3a; }}
                        """)
        elif key == Qt.Key.Key_Right:
            if self.is_in_menu:
                self.menu_button_index = (self.menu_button_index + 1) % len(self.menu_buttons)
                self.update_menu_focus()
            elif self.apps and not self.is_animating:
                self.current_index = (self.current_index + 1) % len(self.apps)
                self.animate_carousel("right")
        elif key == Qt.Key.Key_Left:
            if self.is_in_menu:
                self.menu_button_index = (self.menu_button_index - 1) % len(self.menu_buttons)
                self.update_menu_focus()
            elif self.apps and not self.is_animating:
                self.current_index = (self.current_index - 1) % len(self.apps)
                self.animate_carousel("left")
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            if self.is_in_menu:
                self.execute_menu_action()
            elif self.apps:
                self.launch_current_app()
        elif key == Qt.Key.Key_Delete:
            if not self.is_in_menu and self.apps:
                self.remove_current_app()
        elif key == Qt.Key.Key_E:
            if not self.is_in_menu and self.apps:
                self.edit_current_app()
        elif key == Qt.Key.Key_Escape:
            if self.is_in_menu:
                self.is_in_menu = False
                for action, btn in self.menu_buttons:
                    if btn == self.shutdown_btn:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(255, 255, 255, 0.1);
                                color: rgba(255, 255, 255, 0.7);
                                border: {self.scaling.scale(2)}px solid transparent;
                                border-radius: {self.scaling.scale(25)}px;
                                font-size: {self.scaling.scale_font(14)}px;
                                font-weight: 600;
                            }}
                            QPushButton:hover {{ background-color: #3a3a3a; }}
                        """)
                    else:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(255, 255, 255, 0.1);
                                color: rgba(255, 255, 255, 0.7);
                                border: {self.scaling.scale(2)}px solid transparent;
                                border-radius: {self.scaling.scale(25)}px;
                                font-size: {self.scaling.scale_font(24)}px;
                                font-weight: 500;
                            }}
                            QPushButton:hover {{ background-color: #3a3a3a; }}
                        """)
            else:
                self.close()
        else:
            super().keyPressEvent(event)
   
    def closeEvent(self, event):
        # Assicurati di fermare il worker se è in esecuzione
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.stop()
            self.download_worker.wait(1000) # Aspetta max 1 secondo
            
        if self.process_check_timer:
            self.process_check_timer.stop()
        if self.joystick_timer:
            self.joystick_timer.stop()
        if self.joystick_detection_timer:
            self.joystick_detection_timer.stop()
        if JOYSTICK_AVAILABLE:
            pygame.quit()
        event.accept()

def main():
    app = QApplication(sys.argv)
    # Prova a impostare un'icona (assicurati che il percorso sia corretto)
    icon_path = "assets/icons/logo48.png"
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Warning: Icona app non trovata in {icon_path}")
        
    launcher = TVLauncher()
    launcher.show()
    launcher.setFocus()
    launcher.activateWindow()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
