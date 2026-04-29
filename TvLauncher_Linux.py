import sys
import json
import subprocess
import platform
import os
import random
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
from PyQt6.QtGui import QPixmap, QFont, QKeyEvent, QPainter, QColor, QIcon , QBrush
import psutil

from modules.app_reorder import integrate_reorder_mode
from modules.search_widget import QuickSearchWidget
from modules.program_scanner import ProgramScanner, ProgramScanDialog
from modules.settings_menu import SettingsMenu
from modules.window_manager import WindowManager
from modules.sound_effects import SoundManager
from modules.key_remapper import KeyMapper
from modules.tile_effects import TileGlowEffect
from modules.volume_overlay import install_volume_control
from modules.joystick_manager import JoystickManager
from modules.background_manager import BackgroundManager
from modules.responsive_scaling import ResponsiveScaling
from modules.image_manager import ImageManager
from modules.app_editor_dialog import EditAppDialog
from modules.weather_widget import (
    integrate_weather_widget,
    add_weather_to_header,
    cleanup_weather_widget
)
from modules.category_manager import (
    integrate_categories, 
    add_category_navigation_to_keypressevent,
    add_quick_category_shortcut,
    add_category_joystick_support
)
from modules.dialogs import ApiKeyDialog, SystemMenuDialog, AddAppDialog
from modules.styles import Styles
from modules.parental_control import integrate_parental_control
from modules.update_notification import check_for_updates

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

if BASE_DIR.name == 'modules':
    BASE_DIR = BASE_DIR.parent

os.chdir(BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
MODULES_DIR = os.path.join(BASE_DIR, 'modules')


# Config vive in ~/.config/TVLauncher/ 
_xdg_config_home = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
USER_DATA_DIR = _xdg_config_home / 'TVLauncher'
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = USER_DATA_DIR / 'launcher_apps.json'


TILES_DIR = USER_DATA_DIR / 'tiles'
TILES_DIR.mkdir(parents=True, exist_ok=True)

# Key mappings e scanner cache in ~/.config/TVLauncher/
KEY_MAPPINGS_FILE = USER_DATA_DIR / 'key_mappings.json'
_cache_suffix = "windows" if platform.system() == "Windows" else "linux"
SCANNER_CACHE_FILE = USER_DATA_DIR / f'scanner_cache_{_cache_suffix}.json'


_old_config = Path(BASE_DIR) / 'launcher_apps.json'
if _old_config.exists() and not CONFIG_FILE.exists():
    import shutil
    shutil.move(str(_old_config), str(CONFIG_FILE))
    print(f"Config migrated to user config folder: {CONFIG_FILE}")


def _migrate_old_tiles():
    import shutil
    old_tiles_dir = Path(BASE_DIR) / 'tiles'
    if old_tiles_dir.exists() and old_tiles_dir.is_dir():
        moved = 0
        for tile_file in old_tiles_dir.iterdir():
            dest = TILES_DIR / tile_file.name
            if not dest.exists():
                shutil.move(str(tile_file), str(dest))
                moved += 1
        if moved:
            print(f"[Migration] Moved {moved} tile(s) from app folder to {TILES_DIR}")
        try:
            old_tiles_dir.rmdir()  # rimuove solo se vuota
        except OSError:
            pass

_migrate_old_tiles()

# Auto-migrazione key_mappings.json
def _migrate_key_mappings():
    import shutil
    old_file = Path(BASE_DIR) / 'key_mappings.json'
    if old_file.exists() and not KEY_MAPPINGS_FILE.exists():
        shutil.move(str(old_file), str(KEY_MAPPINGS_FILE))
        print(f"[Migration] key_mappings.json migrated to: {KEY_MAPPINGS_FILE}")

_migrate_key_mappings()

# Auto-migrazione scanner_cache_*.json
def _migrate_scanner_cache():
    import shutil
    old_file = Path(BASE_DIR) / f'scanner_cache_{_cache_suffix}.json'
    if old_file.exists() and not SCANNER_CACHE_FILE.exists():
        shutil.move(str(old_file), str(SCANNER_CACHE_FILE))
        print(f"[Migration] scanner_cache_{_cache_suffix}.json migrated to: {SCANNER_CACHE_FILE}")

_migrate_scanner_cache()

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("Warning: requests not installed. Online image search disabled.")
    print("Install with: pip install requests")

# Detect OS
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"


def rounded_pixmap(original_path, width, height, radius=24):
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


class DownloadWorker(QThread):
    progress_update = pyqtSignal(str, int)
    app_ready = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, selected_programs, image_manager, existing_app_names):
        super().__init__()
        self.selected = selected_programs
        self.image_manager = image_manager
        self.existing = existing_app_names
        self.is_running = True

    def run(self):
        to_download = []
        for prog in self.selected:
            if prog['name'].lower() not in self.existing:
                 to_download.append(prog)
        
        total = len(to_download)
        if total == 0:
            self.progress_update.emit("Programs already present.", 100)
            self.finished.emit()
            return

        for i, prog in enumerate(to_download):
            if not self.is_running:
                break
            percent = int((i + 1) / total * 100)
            self.progress_update.emit(f"Downloading for: {prog['name']}...", percent)
            if self.image_manager.api_key and REQUESTS_AVAILABLE:
                image_result = self.image_manager.get_app_image(prog['name'], prog['path'])
                if image_result:
                    prog['icon'] = image_result
            self.app_ready.emit(prog)
        
        if self.is_running:
            self.progress_update.emit("Completed!", 100)
        else:
            self.progress_update.emit("Cancelled.", 100)
        self.finished.emit()

    def stop(self):
        print("Worker interruption requested")
        self.is_running = False


class CoverDownloadWorker(QThread):
    progress_update = pyqtSignal(str, int)
    cover_downloaded = pyqtSignal(int, str)
    finished = pyqtSignal(int)

    def __init__(self, apps_to_update, image_manager):
        super().__init__()
        self.apps_to_update = apps_to_update  
        self.image_manager = image_manager
        self.is_running = True

    def run(self):
        total = len(self.apps_to_update)
        updated_count = 0
        
        if total == 0:
            self.finished.emit(0)
            return

        for i, (app_index, app_data) in enumerate(self.apps_to_update):
            if not self.is_running:
                break
            percent = int((i + 1) / total * 100)
            self.progress_update.emit(f"Downloading: {app_data['name']}...", percent)
            image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
            if image_result and image_result != app_data['path']:
                self.cover_downloaded.emit(app_index, image_result)
                updated_count += 1
        
        if self.is_running:
            self.progress_update.emit("Complete!", 100)
        else:
            self.progress_update.emit("Cancelled.", 100)
        self.finished.emit(updated_count)

    def stop(self):
        print("🛑 Cover download worker interruption requested")
        self.is_running = False


class AppTile(QWidget):
    def __init__(self, app_data, scaling, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.scaling = scaling
        self.is_focused = False
        self.glow_effect = None  
        self._normal_pixmap = None
        self._focused_pixmap = None
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
        layout.setSpacing(self.scaling.scale(8))
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.normal_img_width, self.normal_img_height)
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.image_label.setStyleSheet(
            Styles.tile_image_normal(self.border_radius, self.scaling.scale_font(18))
        )
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(self.scaling.scale(15))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(self.scaling.scale(4))
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(self.shadow)
        layout.addWidget(self.image_label)
        self.name_label = QLabel(app_data['name'])
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setMaximumWidth(self.normal_width)
        self.name_label.setStyleSheet(
            Styles.tile_name_normal(self.scaling.scale_font(14))
        )
        layout.addWidget(self.name_label)
        self.setLayout(layout)
        self.set_focused(False)

    def set_focused(self, focused):
        self.is_focused = focused
        icon_path = self.app_data.get('icon')
        
        if focused:
            self.setFixedSize(self.focused_width, self.focused_height)
            self.image_label.setFixedSize(self.focused_img_width, self.focused_img_height)
            if self._focused_pixmap is None and icon_path and Path(icon_path).exists():
                self._focused_pixmap = rounded_pixmap(
                    icon_path, self.focused_img_width, self.focused_img_height, self.border_radius
                )
            if self._focused_pixmap:
                self.image_label.setPixmap(self._focused_pixmap)
            else:
                self.image_label.setText(self.app_data['name'])
            self.image_label.setStyleSheet(
                Styles.tile_image_focused(self.scaling.scale(3), self.border_radius, self.scaling.scale_font(18))
            )
            self.name_label.setStyleSheet(
                Styles.tile_name_focused(self.scaling.scale_font(15))
            )
            glow_enabled = self._is_glow_enabled()
            if not glow_enabled:
                if hasattr(self, 'shadow') and self.shadow:
                    try:
                        self.shadow.setBlurRadius(self.scaling.scale(25))
                        self.shadow.setYOffset(self.scaling.scale(8))
                    except RuntimeError:
                        self._recreate_shadow()
                        self.shadow.setBlurRadius(self.scaling.scale(25))
                        self.shadow.setYOffset(self.scaling.scale(8))
            if glow_enabled:
                if self.glow_effect is None:
                    from modules.tile_effects import TileGlowEffect
                    self.glow_effect = TileGlowEffect(self, self.scaling)
                self.glow_effect.start()
        else:
            if self.glow_effect:
                self.glow_effect.stop()
            self.setFixedSize(self.normal_width, self.normal_height)
            self.image_label.setFixedSize(self.normal_img_width, self.normal_img_height)
            if self._normal_pixmap is None and icon_path and Path(icon_path).exists():
                self._normal_pixmap = rounded_pixmap(
                    icon_path, self.normal_img_width, self.normal_img_height, self.border_radius
                )
            if self._normal_pixmap:
                self.image_label.setPixmap(self._normal_pixmap)
            else:
                self.image_label.setText(self.app_data['name'])
            self.image_label.setStyleSheet(
                Styles.tile_image_normal(self.border_radius, self.scaling.scale_font(18))
            )
            self.name_label.setStyleSheet(
                Styles.tile_name_normal(self.scaling.scale_font(14))
            )
            if hasattr(self, 'shadow') and self.shadow:
                try:
                    self.shadow.setBlurRadius(self.scaling.scale(15))
                    self.shadow.setYOffset(self.scaling.scale(4))
                except RuntimeError:
                    self._recreate_shadow()
                    self.shadow.setBlurRadius(self.scaling.scale(15))
                    self.shadow.setYOffset(self.scaling.scale(4))

    def _recreate_shadow(self):
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(self.scaling.scale(15))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(self.scaling.scale(4))
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.image_label.setGraphicsEffect(self.shadow)

    def invalidate_cache(self):
        """Invalida la cache delle pixmap — da chiamare quando l'icona cambia."""
        self._normal_pixmap = None
        self._focused_pixmap = None
        self.set_focused(self.is_focused)

    def _is_glow_enabled(self):
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'config_data'):
                    return parent.config_data.get('tile_glow', True)
                parent = parent.parent()
            return True
        except:
            return True


class TVLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scaling = ResponsiveScaling()
        self.volume_manager = None
        self.config_file = CONFIG_FILE
        self.config_data = self.load_config()
        
        integrate_weather_widget(self, BASE_DIR)
        
        if hasattr(self, 'weather_widget') and self.weather_widget:
            weather_city = self.config_data.get('weather_city', 'Milan')
            weather_country = self.config_data.get('weather_country_code', 'IT')
            weather_units = self.config_data.get('weather_units', 'metric')
            show_weather = self.config_data.get('show_weather', False)
            self.weather_widget.setVisible(show_weather)
            self.weather_widget.set_location(weather_city, weather_country)
            self.weather_widget.set_units(weather_units)
        
        self.apps = self.config_data.get('apps', [])
        self.steamgriddb_api_key = self.config_data.get('steamgriddb_api_key', '')
        
        self.background_manager = BackgroundManager(
            parent=self,
            config_data=self.config_data,
            assets_dir=ASSETS_DIR
        )
        
        self.image_manager = ImageManager(api_key=self.steamgriddb_api_key, tiles_dir=TILES_DIR)
        sound_enabled = self.config_data.get('sound_effects', False)
        self.sound_manager = SoundManager(enabled=sound_enabled)
        self.key_mapper = KeyMapper(config_file=KEY_MAPPINGS_FILE)
        self.key_mapper.install_event_filter(QApplication.instance())
        self.current_index = 0
        self.tiles = []
        self.menu_button_index = 0
        self.is_in_menu = False
        self.animation_group = None
        self.is_animating = False
        self.joystick_manager = JoystickManager(self, self.scaling)
        self.launched_process = None
        self.process_check_timer = None
        self.focus_check_timer = None
        self.inputs_enabled = True
        self.download_worker = None
        self.progress_dialog = None
        self.added_count = 0
        self.cover_download_worker = None
        self.quick_search = QuickSearchWidget(self.scaling, self)
        self.quick_search.app_selected.connect(self.on_search_app_selected)
        self.quick_search.search_closed.connect(self.on_search_closed)
        
        self.volume_manager = install_volume_control(self.scaling, self)

        self.init_ui()

        self.normal_width = self.scaling.scale(360)
        self.normal_height = self.scaling.scale(260)
        self.focused_width = self.scaling.scale(400)
        self.focused_height = self.scaling.scale(288)

        integrate_reorder_mode(self)
        self.settings_menu = SettingsMenu(self.scaling, self)
        integrate_categories(self)
        add_quick_category_shortcut(self)
        add_category_joystick_support(self) 
        
        self.window_manager = WindowManager(self)
        screen = QApplication.primaryScreen().geometry()
        self.settings_menu.setGeometry(
            screen.width(), 0,
            self.settings_menu.width(),
            screen.height()
        )
        self.settings_menu.menu_closed.connect(self.on_settings_closed)
        self.settings_menu.raise_()
        self.settings_menu.setGeometry(0, 0, self.settings_menu.width(), self.height())
        show_clock = self.config_data.get('show_clock', True)
        self.toggle_clock_visibility(show_clock)
        
        if hasattr(self, 'weather_widget') and self.weather_widget:
            self.weather_widget.setVisible(self.config_data.get('show_weather', False))
        self.build_infinite_carousel()
        
        if hasattr(self, 'overlay'):
            self.background_manager.initialize(overlay=self.overlay)
        else:
            self.background_manager.initialize()
        
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        # Auto-download cover all'avvio se esiste una API key
        if self.steamgriddb_api_key:
            QTimer.singleShot(2000, self._auto_download_covers_on_startup)

        # Controllo aggiornamenti in background (3 secondi dopo l'avvio)
        QTimer.singleShot(3000, lambda: check_for_updates(self, self.scaling))

        # Parental Control — inizializza il manager (non mostra nulla qui)
        integrate_parental_control(self, USER_DATA_DIR)

    

    def _msgbox_style(self):
        """Stile MSGBOX con font e padding responsive."""
        s = self.scaling
        return Styles.msgbox(
            font_size_label=s.scale_font(14),
            font_size_btn=s.scale_font(13),
            padding_v=s.scale(10),
            padding_h=s.scale(30),
            border_radius=s.scale(8),
            min_width=s.scale(80),
        )

    def _progress_style(self):
        """Stile PROGRESS_DIALOG con font e padding responsive."""
        s = self.scaling
        return Styles.progress_dialog(
            font_size_label=s.scale_font(13),
            font_size_btn=s.scale_font(13),
            padding_v=s.scale(8),
            padding_h=s.scale(20),
            border_radius=s.scale(8),
        )

   

    def _auto_download_covers_on_startup(self):
        """Download missing covers on startup with a progress dialog."""
        if not self.steamgriddb_api_key or not self.apps:
            return
        if self.cover_download_worker and self.cover_download_worker.isRunning():
            return

        apps_to_update = []
        for i, app in enumerate(self.apps):
            icon_path = app.get('icon', '')
            app_path = app.get('path', '')
            needs_update = False
            if not icon_path:
                needs_update = True
            elif icon_path == app_path:
                needs_update = True
            elif icon_path.lower().endswith(('.exe', '.sh', '.AppImage')):
                needs_update = True
            elif not Path(icon_path).exists():
                needs_update = True
            if needs_update:
                apps_to_update.append((i, app))

        if not apps_to_update:
            return

        print(f"[Startup] Auto-downloading covers for {len(apps_to_update)} app(s)...")

        self.progress_dialog = QProgressDialog(
            f"Downloading covers for {len(apps_to_update)} app(s)...",
            "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setWindowTitle("Downloading Covers")
        self.progress_dialog.setMinimumSize(self.scaling.scale(450), self.scaling.scale(150))
        self.progress_dialog.setMaximumWidth(self.scaling.scale(600))
        self.progress_dialog.setValue(0)
        self.progress_dialog.setStyleSheet(self._progress_style())

        self.cover_download_worker = CoverDownloadWorker(apps_to_update, self.image_manager)
        self.cover_download_worker.progress_update.connect(self._on_cover_download_progress)
        self.cover_download_worker.cover_downloaded.connect(self._on_cover_downloaded)
        self.cover_download_worker.finished.connect(self._on_startup_cover_download_finished)
        self.progress_dialog.canceled.connect(self.cover_download_worker.stop)
        self.cover_download_worker.start()
        self.progress_dialog.show()

    def _on_startup_cover_download_finished(self, updated_count):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        if updated_count > 0:
            print(f"[Startup] Downloaded {updated_count} cover(s). Refreshing carousel...")
            self.save_config()
            self.build_infinite_carousel()
        self.cover_download_worker = None
        self.setFocus()
        self.activateWindow()

    def toggle_clock_visibility(self, visible):
        clock_widgets = [
            getattr(self, 'time_label', None),
            getattr(self, 'date_label', None),
        ]
        for widget in clock_widgets:
            if widget is None:
                continue
            if not visible:
                from PyQt6.QtWidgets import QGraphicsOpacityEffect
                opacity_effect = QGraphicsOpacityEffect()
                opacity_effect.setOpacity(0)
                widget.setGraphicsEffect(opacity_effect)
            else:
                widget.setGraphicsEffect(None)
    
    def update_clock(self):
        from datetime import datetime
        import locale
        now = datetime.now()
        try:
            test_time = now.strftime("%p")
            if test_time:
                time_str = now.strftime("%I:%M %p")
            else:
                time_str = now.strftime("%H:%M")
        except:
            time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d %B %Y")
        parts = date_str.split()
        if len(parts) >= 2:
            parts[1] = parts[1].capitalize()
            date_str = " ".join(parts)
        if hasattr(self, 'time_label') and self.time_label:
            self.time_label.setText(time_str)
        if hasattr(self, 'date_label') and self.date_label:
            self.date_label.setText(date_str)   

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
                return
            status = process.status()
            if status == psutil.STATUS_ZOMBIE:
                self.on_app_closed()
                return
        except psutil.NoSuchProcess:
            self.on_app_closed()
        except psutil.AccessDenied:
            pass
        except Exception as e:
            print(f"⚠️ Error checking process {self.launched_process}: {e}")

    def check_window_focus(self):
        if not IS_LINUX:
            return
        if not self.inputs_enabled:
            if self.isActiveWindow():
                self.on_app_closed()       
   
    def on_app_closed(self):
        if self.inputs_enabled:
            return
        old_pid = self.launched_process
        self.launched_process = None
        if self.process_check_timer:
            self.process_check_timer.stop()
            self.process_check_timer = None
        if self.focus_check_timer:
            self.focus_check_timer.stop()
            self.focus_check_timer = None
        self.window_manager.on_app_close()
        self.enable_inputs()

    def on_settings_closed(self):
        self.config_data = self.load_config()
        self.background_manager.load_config(self.config_data)
        show_clock = self.config_data.get('show_clock', True)
        self.toggle_clock_visibility(show_clock)
        self.build_infinite_carousel()
        self.enable_inputs()
        self.setFocus()
        self.activateWindow()

    def force_window_focus(self):
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def init_ui(self):
        self.setWindowTitle("TV Launcher")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if hasattr(self, 'joystick_manager') and self.joystick_manager.joystick:
            print(f"🎮 Joystick ready: {self.joystick_manager.joystick.get_name()}")
        else:
            print("⚠️ No joystick detected - using keyboard only")
        screen = QApplication.primaryScreen().geometry()
        self.setFixedSize(screen.width(), screen.height())
        self.update_background()
        overlay = QWidget(self)
        overlay.setGeometry(0, 0, screen.width(), screen.height())
        overlay.setStyleSheet(Styles.OVERLAY_DIM)
        overlay.lower()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay = overlay
        main_widget = QWidget()
        main_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        main_widget.setStyleSheet(Styles.TRANSPARENT)
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(
            self.scaling.scale(5),
            self.scaling.scale(48),
            self.scaling.scale(5),
            self.scaling.scale(48)
        )
        main_layout.setSpacing(0)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(
            self.scaling.scale(43), 0,
            self.scaling.scale(43), 0
        )
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, '')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'C')
            except:
                pass
        now = datetime.now()
        try:
            test_time = now.strftime("%p")
            if test_time:
                time_str = now.strftime("%I:%M %p")
            else:
                time_str = now.strftime("%H:%M")
        except:
            time_str = now.strftime("%H:%M")
        date_str = now.strftime("%d %B %Y")
        parts = date_str.split()
        if len(parts) >= 2:
            parts[1] = parts[1].capitalize()
            date_str = " ".join(parts)
        self.time_label = QLabel(time_str)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(Styles.clock_time(self.scaling.scale_font(48)))
        self.date_label = QLabel(date_str)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.date_label.setStyleSheet(Styles.clock_date(self.scaling.scale_font(22)))
        clock_layout = QVBoxLayout()
        clock_layout.addWidget(self.time_label)
        clock_layout.addWidget(self.date_label)
        header_layout.addLayout(clock_layout)
        add_weather_to_header(self, header_layout)
        header_layout.addStretch()
        if hasattr(self, 'weather_widget'):
            header_layout.addWidget(self.weather_widget)

        from modules.battery_widget import BatteryWidget
        _show_battery = BatteryWidget.battery_available()

        pill_widget = QWidget()
        pill_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        pill_layout = QHBoxLayout(pill_widget)
        pill_layout.setContentsMargins(
            self.scaling.scale(14), 0,
            self.scaling.scale(14), 0
        )
        pill_layout.setSpacing(self.scaling.scale(10))
        pill_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = self.scaling.scale(60)
        gear_size = self.scaling.scale(46)
        pill_widget.setFixedHeight(btn_size)

        if _show_battery:
            self.header_battery = BatteryWidget(self.scaling, parent=pill_widget)
            self.header_battery.setFixedHeight(btn_size)
            self.header_battery.setMinimumWidth(self.scaling.scale(90))
            self.header_battery.setVisible(True)
            pill_layout.addWidget(self.header_battery, 0, Qt.AlignmentFlag.AlignVCenter)
            sep = QLabel()
            sep.setFixedSize(self.scaling.scale(1), self.scaling.scale(32))
            sep.setStyleSheet(Styles.SEPARATOR)
            pill_layout.addWidget(sep, 0, Qt.AlignmentFlag.AlignVCenter)

        settings_btn = QPushButton("⚙")
        settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        settings_btn.setToolTip("Settings (Press S)")
        settings_btn.clicked.connect(lambda: self.settings_menu.open_menu(self))

        if not _show_battery:
            pill_widget.setFixedSize(btn_size, btn_size)
            pill_layout.setContentsMargins(0, 0, 0, 0)
            settings_btn.setFixedSize(btn_size, btn_size)
            settings_btn.setStyleSheet(Styles.settings_btn_standalone(
                self.scaling.scale(30), self.scaling.scale_font(28)
            ))
            pill_widget.setStyleSheet(Styles.TRANSPARENT)
        else:
            settings_btn.setFixedSize(gear_size, gear_size)
            settings_btn.setStyleSheet(Styles.settings_btn_in_pill(
                self.scaling.scale(23), self.scaling.scale_font(28)
            ))
            pill_widget.setStyleSheet(Styles.pill_with_battery(self.scaling.scale(30)))

        pill_layout.addWidget(settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        pill_wrapper = QWidget()
        pill_wrapper.setStyleSheet(Styles.TRANSPARENT)
        wrapper_layout = QVBoxLayout(pill_wrapper)
        wrapper_layout.setContentsMargins(0, self.scaling.scale(27), 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(pill_widget)

        header_layout.addWidget(pill_wrapper, 0, Qt.AlignmentFlag.AlignVCenter)
        
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(40)
        main_layout.addStretch(3)
        
        self.carousel_container = QWidget()
        self.carousel_container.setFixedHeight(self.scaling.scale(310))
        visible_width = (5 * self.scaling.scale(400)) + (4 * self.scaling.scale(5))
        self.carousel_container.setFixedWidth(visible_width)
        self.carousel_container.setStyleSheet(Styles.TRANSPARENT)
        self.max_visible_tiles = 9
        self.tile_width = self.scaling.scale(360)
        self.tile_spacing = self.scaling.scale(17)
        
        main_layout.addWidget(self.carousel_container, alignment=Qt.AlignmentFlag.AlignLeft)
        main_layout.addSpacing(20)
        main_layout.addStretch(1)
        
        menu_container = QWidget()
        menu_container.setStyleSheet(Styles.TRANSPARENT)
        menu_layout = QHBoxLayout(menu_container)
        menu_layout.setContentsMargins(0, 0, 0, self.scaling.scale(20))
        menu_layout.addStretch()
        button_widget = QWidget()
        button_widget.setStyleSheet(Styles.menu_bar_container(self.scaling.scale(32)))
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

        self.sleep_btn = QPushButton("☾")
        self.sleep_btn.setFixedSize(btn_size, btn_size)
        self.sleep_btn.setToolTip("Sleep")
        self.sleep_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.sleep_btn)

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
            ("sleep", self.sleep_btn),
            ("shutdown", self.shutdown_btn),
            ("close", self.close_btn)
        ]
        for action, btn in self.menu_buttons:
            btn.clicked.connect(lambda checked, a=action: self.execute_menu_action_direct(a))
            if btn == self.shutdown_btn:
                btn.setStyleSheet(Styles.menu_btn_normal(
                    self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(14), "600"
                ))
            else:
                btn.setStyleSheet(Styles.menu_btn_normal(
                    self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(24), "500"
                ))
        menu_layout.addWidget(button_widget)
        menu_layout.addStretch()
        main_layout.addWidget(menu_container)
        
        instructions = QLabel("Navigate: ← → ↑ ↓ or D-Pad/Stick | Launch: Enter/A | Edit: E/X | Delete: Del/Y | Search: F/LB | Exit: Esc/B")
        instructions.setStyleSheet(Styles.instructions(self.scaling.scale_font(11)))
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
        apps_to_save = getattr(self, '_all_apps_backup', self.apps)
        clean_apps = []
        for app in apps_to_save:
            clean_app = {
                'name': str(app.get('name', '')),
                'path': str(app.get('path', '')),
                'icon': str(app.get('icon', '')),
                'category': str(app.get('category', 'Other'))  
            }
            if not isinstance(clean_app['icon'], str):
                clean_app['icon'] = clean_app['path']
            clean_apps.append(clean_app)
        
        config_data = {
            'apps': clean_apps,
            'steamgriddb_api_key': self.steamgriddb_api_key,
            'show_clock': self.config_data.get('show_clock', True),
            'auto_download': self.config_data.get('auto_download', True),
            'tile_glow': self.config_data.get('tile_glow', True),
            'sound_effects': self.config_data.get('sound_effects', False),
            'fullscreen': self.config_data.get('fullscreen', True),
            'show_weather': self.config_data.get('show_weather', False),
        }
        config_data['weather_city'] = self.config_data.get('weather_city', 'Milan')
        config_data['weather_country_code'] = self.config_data.get('weather_country_code', 'IT')
        config_data['weather_units'] = self.config_data.get('weather_units', 'metric')
        
        if hasattr(self, 'background_manager') and self.background_manager is not None:
            background_config = self.background_manager.get_config()
            config_data.update(background_config)
        else:
            config_data['background'] = self.config_data.get('background', '')
            config_data['auto_change_wallpaper'] = self.config_data.get('auto_change_wallpaper', False)
            config_data['wallpaper_interval'] = self.config_data.get('wallpaper_interval', 180000)
        
        if hasattr(self, 'category_manager'):
            config_data = self.category_manager.save_categories(config_data)
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def refresh_widgets_from_config(self):
        self.config_data = self.load_config()
        if hasattr(self, 'weather_widget') and self.weather_widget:
            weather_city = self.config_data.get('weather_city', 'Milan')
            weather_country = self.config_data.get('weather_country_code', 'IT')
            weather_units = self.config_data.get('weather_units', 'metric')
            show_weather = self.config_data.get('show_weather', False)
            self.weather_widget.setVisible(show_weather)
            self.weather_widget.set_location(weather_city, weather_country)
            self.weather_widget.set_units(weather_units)
        if hasattr(self, 'settings_menu') and self.settings_menu:
            for i in range(self.settings_menu.list_layout.count()):
                item = self.settings_menu.list_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, '_refresh_toggle'):
                        widget._refresh_toggle()

    def _on_category_changed(self, category_index):
        self.current_index = 0
        self.build_infinite_carousel()

    

    def _make_confirm_dialog(self, title, message_text):
        """Crea un dialog di conferma responsive riutilizzabile."""
        s = self.scaling
        btn_font = s.scale_font(14)
        lbl_font = s.scale_font(16)
        pad_v    = s.scale(12)
        pad_h    = s.scale(30)
        radius   = s.scale(8)

        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle(title)
        confirm_dialog.setModal(True)
        confirm_dialog.setFixedSize(s.scale(400), s.scale(200))
        confirm_dialog.setStyleSheet(
            Styles.confirm_dialog(lbl_font, btn_font, pad_v, pad_h, radius)
        )

        layout = QVBoxLayout()
        layout.setSpacing(s.scale(20))
        layout.setContentsMargins(s.scale(30), s.scale(30), s.scale(30), s.scale(30))

        message = QLabel(message_text)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(message)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(s.scale(15))

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
        confirm_index = [1]  # default su "No"

        def update_confirm_focus():
            for i, btn in enumerate(confirm_buttons):
                if i == confirm_index[0]:
                    btn.setStyleSheet(
                        Styles.confirm_btn_focused(btn_font, pad_v, pad_h, radius)
                    )
                else:
                    btn.setStyleSheet(
                        Styles.confirm_btn_normal(btn_font, pad_v, pad_h, radius)
                    )

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
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                confirm_buttons[confirm_index[0]].click()
            elif key == Qt.Key.Key_Escape:
                confirm_dialog.reject()
            else:
                super(confirm_dialog.__class__, confirm_dialog).keyPressEvent(event)

        confirm_dialog.keyPressEvent = confirm_key_handler
        update_confirm_focus()
        return confirm_dialog

    def _make_info_dialog(self, title, message_text):
        """Dialog personalizzato per messaggi informativi (solo OK) — dimensioni responsive."""
        s = self.scaling
        btn_font = s.scale_font(14)
        lbl_font = s.scale_font(15)
        pad_v    = s.scale(10)
        pad_h    = s.scale(30)
        radius   = s.scale(8)

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setModal(True)
        dlg.setFixedSize(s.scale(400), s.scale(200))
        dlg.setStyleSheet(Styles.confirm_dialog(lbl_font, btn_font, pad_v, pad_h, radius))

        layout = QVBoxLayout()
        layout.setSpacing(s.scale(20))
        layout.setContentsMargins(s.scale(30), s.scale(30), s.scale(30), s.scale(30))

        message = QLabel(message_text)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        message.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(message)

        ok_btn = QPushButton("OK")
        ok_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_btn.clicked.connect(dlg.accept)
        ok_btn.setStyleSheet(Styles.confirm_btn_focused(btn_font, pad_v, pad_h, radius))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        dlg.setLayout(layout)

        def key_handler(event):
            if event.isAutoRepeat():
                return
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
                dlg.accept()
            else:
                super(dlg.__class__, dlg).keyPressEvent(event)

        dlg.keyPressEvent = key_handler
        return dlg

    def _make_question_dialog(self, title, message_text):
        """Dialog Yes/No responsive. Usa dialog.exec() == QDialog.DialogCode.Accepted per Yes."""
        return self._make_confirm_dialog(title, message_text)

    

    def set_api_key(self):
        dialog = ApiKeyDialog(self.steamgriddb_api_key, self, scaling=self.scaling)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key = dialog.get_api_key()
            if new_key != self.steamgriddb_api_key:
                old_key = self.steamgriddb_api_key
                self.steamgriddb_api_key = new_key
                self.image_manager = ImageManager(api_key=self.steamgriddb_api_key, tiles_dir=TILES_DIR)
                self.save_config()
                
                if new_key:
                    if not old_key and self.apps:
                        self.download_covers_for_existing_apps()
                    else:
                        self._make_info_dialog(
                            "API Key Saved",
                            "API Key successfully saved!<br><br>"
                            "Now you can download the 16:9 images<br>"
                            "when you add a new app into the launcher."
                        ).exec()
                else:
                    self._make_info_dialog(
                        "API Key Removed",
                        "API Key removed. The Launcher will use only<br>"
                        "local images and exe icons."
                    ).exec()
        self.setFocus()
        self.activateWindow()

    def download_covers_for_existing_apps(self):
        """Scarica le copertine per tutte le app esistenti che non ne hanno una."""
        if not self.steamgriddb_api_key:
            dlg = self._make_question_dialog(
                "API Key Required",
                "You need a <b>SteamGridDB API Key</b> to download covers.<br><br>"
                "Do you want to set it now?"
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.set_api_key()
            return
        
        if not REQUESTS_AVAILABLE:
            self._make_info_dialog(
                "Missing Library",
                "The <b>'requests'</b> library is not installed.<br><br>"
                "<span style='color:#aaa;'>Install it with: "
                "<span style='color:#6cf;'>pip install requests</span></span>"
            ).exec()
            return
        
        if not self.apps:
            self._make_info_dialog(
                "No Apps",
                "Add some apps first before downloading covers!"
            ).exec()
            return
        
        apps_to_update = []
        for i, app in enumerate(self.apps):
            icon_path = app.get('icon', '')
            app_path = app.get('path', '')
            needs_update = False
            if not icon_path:
                needs_update = True
            elif icon_path == app_path:
                needs_update = True
            elif not self.is_image_or_icon(icon_path):
                needs_update = True
            elif not Path(icon_path).exists():
                needs_update = True
            if needs_update:
                apps_to_update.append((i, app))
        
        if not apps_to_update:
            self._make_info_dialog(
                "All Set!",
                "All apps already have custom covers!"
            ).exec()
            return
        
        dlg = self._make_question_dialog(
            "Download Covers",
            f"Found <b>{len(apps_to_update)}</b> app(s) without custom covers.<br><br>"
            "Do you want to download covers for them?"
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            self.setFocus()
            self.activateWindow()
            return
        
        self.progress_dialog = QProgressDialog(
            f"Downloading covers for {len(apps_to_update)} apps...",
            "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setWindowTitle("Downloading Covers")
        self.progress_dialog.setMinimumSize(self.scaling.scale(450), self.scaling.scale(150))
        self.progress_dialog.setMaximumWidth(self.scaling.scale(600))
        self.progress_dialog.setValue(0)
        self.progress_dialog.setStyleSheet(self._progress_style())
        
        self.cover_download_worker = CoverDownloadWorker(apps_to_update, self.image_manager)
        self.cover_download_worker.progress_update.connect(self._on_cover_download_progress)
        self.cover_download_worker.cover_downloaded.connect(self._on_cover_downloaded)
        self.cover_download_worker.finished.connect(self._on_cover_download_finished)
        self.progress_dialog.canceled.connect(self.cover_download_worker.stop)
        self.cover_download_worker.start()
        self.progress_dialog.show()

    def is_image_or_icon(self, path: str) -> bool:
        
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            return False

        
        _IMAGE_MAGIC = [
            b'\x89PNG',            # PNG
            b'\xff\xd8\xff',       # JPEG
            b'GIF87a',             # GIF87a
            b'GIF89a',             # GIF89a
            b'BM',                 # BMP
            b'II*\x00',            # TIFF little-endian
            b'MM\x00*',            # TIFF big-endian
            b'\x00\x00\x01\x00',  # ICO
            b'\x00\x00\x02\x00',  # CUR
            b'\x00\x00\x00\x0cftyp',  # HEIC/HEIF (ftyp box)
        ]
        try:
            with open(path, 'rb') as f:
                header = f.read(16)
            if any(header.startswith(sig) for sig in _IMAGE_MAGIC):
                return True
            
            if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
                return True
        except OSError:
            return False

        ext = os.path.splitext(path)[1].lower()
        image_extensions = {
            '.png', '.jpg', '.jpeg', '.jpe', '.jfif',
            '.gif', '.bmp', '.webp', '.tiff', '.tif',
            '.ico', '.cur', '.svg', '.xpm', '.icns',
            '.apng', '.avif', '.heic', '.heif',
        }
        return ext in image_extensions

    def _on_cover_download_progress(self, message, percent):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(percent)

    def _on_cover_downloaded(self, app_index, new_icon_path):
        if 0 <= app_index < len(self.apps):
            self.apps[app_index]['icon'] = new_icon_path
            print(f"✅ Cover updated for: {self.apps[app_index]['name']}")
            for tile in self.tiles:
                if getattr(tile, 'app_index', None) == app_index:
                    tile.app_data['icon'] = str(new_icon_path)
                    tile.invalidate_cache()

    def _on_cover_download_finished(self, updated_count):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        self.save_config()
        for tile in self.tiles:
            if hasattr(tile, 'glow_effect') and tile.glow_effect:
                try:
                    tile.glow_effect.stop()
                except:
                    pass
        self.build_infinite_carousel()
        
        msg_text = (
            f"Successfully downloaded <b>{updated_count}</b> cover(s)!"
            if updated_count > 0
            else "No new covers were downloaded."
        )
        self._make_info_dialog("Download Complete", msg_text).exec()
        
        self.cover_download_worker = None
        self.setFocus()
        self.activateWindow()

    def update_background(self, fade=False):
        self.background_manager.update_background(fade)
        
    def set_background(self):
        if self.background_manager.set_background_from_dialog():
            self.save_config()
        self.setFocus()
        self.activateWindow()
    
    def start_wallpaper_rotation(self):
        self.background_manager.start_wallpaper_rotation()
    
    def stop_wallpaper_rotation(self):
        self.background_manager.stop_wallpaper_rotation()
    
    def change_random_wallpaper(self):
        self.background_manager.change_random_wallpaper()
    
    def toggle_wallpaper_rotation(self, enabled):
        self.background_manager.toggle_wallpaper_rotation(enabled)
        self.save_config()

    def update_menu_focus(self):
        for i, (action, btn) in enumerate(self.menu_buttons):
            if i == self.menu_button_index:
                if btn == self.shutdown_btn:
                    btn.setStyleSheet(Styles.menu_btn_focused(
                        self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(14)
                    ))
                else:
                    btn.setStyleSheet(Styles.menu_btn_focused(
                        self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(24)
                    ))
            else:
                if btn == self.shutdown_btn:
                    btn.setStyleSheet(Styles.menu_btn_normal(
                        self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(14), "600"
                    ))
                else:
                    btn.setStyleSheet(Styles.menu_btn_normal(
                        self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(24), "500"
                    ))
   
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
        elif action == "sleep":
            self.confirm_action("sleep")

    def confirm_action(self, action):
        action_text = {
            "restart": "Restart",
            "shutdown": "Shutdown",
            "sleep": "Suspend"
        }.get(action, action.capitalize())

        confirm_dialog = self._make_confirm_dialog(
            f"Confirm {action_text}",
            f"Are you sure you want to {action_text.lower()} the computer?"
        )
        if confirm_dialog.exec() == QDialog.DialogCode.Accepted:
            self.execute_power_action(action)

    def confirm_exit_launcher(self):
        self._exit_dialog_active = True
        confirm_dialog = self._make_confirm_dialog(
            "Confirm Exit",
            "Are you sure you want to close the launcher?"
        )
        result = confirm_dialog.exec()
        self._exit_dialog_active = False
        if result == QDialog.DialogCode.Accepted:
            self.close()

    def execute_power_action(self, action):
        import platform
        system = platform.system()
        try:
            if system == "Windows":
                if action == "restart":
                    subprocess.run(["shutdown", "/r", "/t", "0"], shell=True)
                elif action == "shutdown":
                    subprocess.run(["shutdown", "/s", "/t", "0"], shell=True)
                elif action == "sleep":
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
            elif system == "Linux":
                if action == "restart":
                    subprocess.run(["systemctl", "reboot"], check=False)
                    subprocess.run(["reboot"], check=False)
                elif action == "shutdown":
                    subprocess.run(["systemctl", "poweroff"], check=False)
                    subprocess.run(["shutdown", "-h", "now"], check=False)
                elif action == "sleep":
                    subprocess.run(["systemctl", "suspend"], check=True)
        except subprocess.CalledProcessError:
            self._make_info_dialog(
                "Error",
                "Command failed. Do you have sufficient privileges?"
            ).exec()
        except FileNotFoundError:
            self._make_info_dialog(
                "Error",
                f"Command not found. Are you running {system}?"
            ).exec()
        except Exception as e:
            self._make_info_dialog(
                "Error",
                f"Cannot execute {action}:<br>{str(e)}"
            ).exec()
   
    def build_infinite_carousel(self):
        for tile in self.tiles:
            if hasattr(tile, 'glow_effect') and tile.glow_effect:
                try:
                    tile.glow_effect.stop()
                    tile.glow_effect = None
                except:
                    pass
        for tile in self.tiles:
            tile.setParent(None)
            tile.deleteLater()
        self.tiles.clear()
        if not self.apps:
            empty_label = QLabel("No apps added yet. Press '+ Add App' to get started!", self.carousel_container)
            empty_label.setStyleSheet(Styles.EMPTY_LABEL)
            empty_label.move(0, 100)
            return
        if self.current_index >= len(self.apps):
            self.current_index = 0
        num_apps = len(self.apps)
        
        if num_apps <= 5:
            for i in range(num_apps):
                tile = AppTile(self.apps[i], self.scaling, self.carousel_container)
                tile.app_index = i
                is_focused = (i == self.current_index)
                tile.set_focused(is_focused)
                self.tiles.append(tile)
        else:
            center_tile_index = 0
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
        num_apps = len(self.apps)
        if num_apps <= 5:
            start_x = self.scaling.scale(5)
            x_pos = int(start_x)
            for i, tile in enumerate(self.tiles):
                tile.move(int(x_pos), 22)
                if i == self.current_index:
                    x_pos += self.focused_width + self.tile_spacing
                else:
                    x_pos += self.normal_width + self.tile_spacing
        else:
            start_x = self.scaling.scale(5)
            x_pos = int(start_x)
            for i, tile in enumerate(self.tiles):
                tile.move(int(x_pos), 22)
                x_pos += tile.width() + self.tile_spacing

    def animate_carousel(self, direction):
        if self.is_animating or not self.tiles:
            return
        self.sound_manager.navigate()
        num_apps = len(self.apps)
        if num_apps <= 5:
            for i, tile in enumerate(self.tiles):
                tile.set_focused(i == self.current_index)
            self._position_all_tiles()
            return
        self.is_animating = True
        shift_distance = self.tile_width + self.tile_spacing
        if direction == "left":
            last_tile = self.tiles[-1]
            new_app_idx = self.current_index % num_apps
            last_tile.app_data = self.apps[new_app_idx]
            last_tile.app_index = new_app_idx
            last_tile._normal_pixmap = None
            last_tile._focused_pixmap = None
            last_tile.name_label.setText(self.apps[new_app_idx]['name'])
            last_tile.set_focused(False)
            start_x = self.scaling.scale(50)
            last_tile.move(int(start_x - shift_distance), 0)
            self.tiles.pop()
            self.tiles.insert(0, last_tile)
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
        center_tile_index = 0
        if direction == "right":
            first_tile = self.tiles.pop(0)
            new_app_idx = (self.current_index + (self.max_visible_tiles - 1)) % num_apps
            first_tile.app_data = self.apps[new_app_idx]
            first_tile.app_index = new_app_idx
            first_tile._normal_pixmap = None
            first_tile._focused_pixmap = None
            first_tile.name_label.setText(self.apps[new_app_idx]['name'])
            first_tile.set_focused(False)
            self.tiles.append(first_tile)
        else:
            last_tile = self.tiles[-1]
            new_app_idx = (self.current_index + (self.max_visible_tiles - 1)) % num_apps
            last_tile.app_data = self.apps[new_app_idx]
            last_tile.app_index = new_app_idx
            last_tile._normal_pixmap = None
            last_tile._focused_pixmap = None
            last_tile.name_label.setText(self.apps[new_app_idx]['name'])
            last_tile.set_focused(False)
        for i, tile in enumerate(self.tiles):
            tile.set_focused(i == center_tile_index)
        self._position_all_tiles()
        self.is_animating = False
   
    def scan_programs(self):
        dialog = ProgramScanDialog(self.image_manager, self, scaling=self.scaling, cache_file=SCANNER_CACHE_FILE)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.get_selected()
            if not selected:
                self.setFocus()
                self.activateWindow()
                return
            self.added_count = 0
            self.progress_dialog = QProgressDialog("Image searching in progress..", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Add programs")
            self.progress_dialog.setMinimumSize(self.scaling.scale(450), self.scaling.scale(150))
            self.progress_dialog.setMaximumWidth(self.scaling.scale(600))
            self.progress_dialog.setValue(0)
            self.progress_dialog.setStyleSheet(self._progress_style())

            existing_names = {app['name'].lower() for app in self.apps}
            self.download_worker = DownloadWorker(selected, self.image_manager, existing_names)
            self.download_worker.app_ready.connect(self._on_app_ready_from_scan)
            self.download_worker.progress_update.connect(self._on_download_progress)
            self.download_worker.finished.connect(self._on_download_finished)
            self.progress_dialog.canceled.connect(self.download_worker.stop)
            self.download_worker.start()
            self.progress_dialog.show()
        else:
            self.setFocus()
            self.activateWindow()

    def _on_app_ready_from_scan(self, app_data):
        clean_app_data = {
            'name': app_data.get('name', ''),
            'path': app_data.get('path', ''),
            'icon': app_data.get('icon', ''),
            'category': self.category_manager.get_default_category()
        }
        if isinstance(clean_app_data['icon'], QPixmap):
            clean_app_data['icon'] = app_data.get('path', '')
        self.apps.append(clean_app_data)
        self.added_count += 1
    
    def _on_download_progress(self, message, percent):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(percent)

    def _on_download_finished(self):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        self.save_config()
        self.build_infinite_carousel()
        
        if self.download_worker and self.download_worker.is_running:
            if self.added_count > 0:
                self._make_info_dialog("Done!", f"Added <b>{self.added_count}</b> program(s) successfully!").exec()
            else:
                self._make_info_dialog("Info", "No new program added (may be already present).").exec()

        self.download_worker = None
        self.added_count = 0
        self.setFocus()
        self.activateWindow()

    def add_app(self):
        dialog = AddAppDialog(self, scaling=self.scaling)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_data = dialog.get_app_data()
            if app_data['name'] and app_data['path']:
                if not app_data.get('category'):
                    app_data['category'] = self.category_manager.get_default_category()
                if (not app_data['icon'] or app_data['icon'] == app_data['path']) and self.image_manager.api_key and REQUESTS_AVAILABLE:
                    print(f"Searching image for: {app_data['name']}")
                    image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
                    if image_result:
                        app_data['icon'] = image_result
                        print(f"✅ Image found: {app_data['name']}")
                    else:
                        print(f"⚠️ No image found, using exe icon")
                if hasattr(self, '_all_apps_backup'):
                    self._all_apps_backup.append(app_data)
                else:
                    self.apps.append(app_data)
                self.save_config()
                self.build_infinite_carousel()
            else:
                self._make_info_dialog(
                    "Invalid Input",
                    "Please provide at least a name and executable path."
                ).exec()
        self.setFocus()
        self.activateWindow()
   
    def edit_current_app(self):
        if not self.apps:
            return
        dialog = EditAppDialog(self.apps[self.current_index], self, scaling=self.scaling)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_data = dialog.get_app_data()
            if app_data['name'] and app_data['path']:
                self.apps[self.current_index] = app_data
                self.save_config()
                self.build_infinite_carousel()
            else:
                self._make_info_dialog(
                    "Invalid Input",
                    "Please provide at least a name and executable path."
                ).exec()
        self.setFocus()
        self.activateWindow()
   
    def remove_current_app(self):
        if not self.apps:
            return

        dlg = self._make_question_dialog(
            "Remove App",
            f"Remove '<b>{self.apps[self.current_index]['name']}</b>'?"
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            removed_app = self.apps[self.current_index]
            if hasattr(self, '_all_apps_backup'):
                self._all_apps_backup = [app for app in self._all_apps_backup
                                         if app['name'] != removed_app['name']]
            else:
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
            print(f"🚀 Launching: {app['name']}")
            print(f"   Command: {app['path']}")
            launch_command = self._get_launch_command(app['path'])
            if 'flatpak' in app['path'].lower() or 'kodi' in app['name'].lower():
                try:
                    subprocess.run(['flatpak', 'kill', 'tv.kodi.Kodi'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                    subprocess.run(['pkill', '-9', '-f', 'kodi'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                    import time
                    time.sleep(1)
                except Exception as e:
                    print(f"   ⚠️ Cleanup warning (non-critical): {e}")
            clean_env = os.environ.copy()
            for var in ['PYTHONHOME', 'PYTHONPATH', 'PYTHONEXECUTABLE',
                        'PYTHONUSERBASE', '_PYTHON_SYSCONFIGDATA_NAME', '_PYTHON_PROJECT_BASE']:
                clean_env.pop(var, None)
            process = subprocess.Popen(
                launch_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=clean_env
            )
            self.launched_process = process.pid
            print(f"   PID: {self.launched_process}")
            self.disable_inputs()
            self.window_manager.on_app_launch()
            if self.process_check_timer:
                self.process_check_timer.stop()
            self.process_check_timer = QTimer()
            self.process_check_timer.timeout.connect(self.check_launched_process)
            self.process_check_timer.start(1000)
            if IS_LINUX:
                if self.focus_check_timer:
                    self.focus_check_timer.stop()
                self.focus_check_timer = QTimer()
                self.focus_check_timer.timeout.connect(self.check_window_focus)
                self.focus_check_timer.start(500)
            print(f"✅ App launched successfully with clean environment")
        except Exception as e:
            print(f"❌ Launch error: {e}")
            self._make_info_dialog("Launch Error", f"Could not launch app:<br>{str(e)}").exec()
            self.enable_inputs()
    
    def _get_launch_command(self, path):
        path = str(path).strip()
        if path.endswith('.desktop'):
            exec_cmd = self._extract_desktop_exec(path)
            if exec_cmd:
                return exec_cmd
            else:
                raise Exception(f"Could not extract Exec command from .desktop file: {path}")
        elif path.endswith('.sh'):
            try:
                os.chmod(path, 0o755)
            except Exception as e:
                print(f"   ⚠️ Could not set executable permission: {e}")
            return f"bash '{path}'"
        else:
            return path
    
    def _extract_desktop_exec(self, desktop_file):
        try:
            with open(desktop_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('Exec='):
                        exec_line = line.split('=', 1)[1].strip()
                        for var in ['%f', '%F', '%u', '%U', '%i', '%c', '%k']:
                            exec_line = exec_line.replace(var, '')
                        exec_line = ' '.join(exec_line.split())
                        return exec_line
        except Exception as e:
            print(f"   ❌ Error reading .desktop file: {e}")
        return None

    def keyPressEvent(self, event: QKeyEvent):
        if add_category_navigation_to_keypressevent(self, event):
            return
        if hasattr(self, 'settings_menu') and getattr(self.settings_menu, 'is_open', False):
            self.settings_menu.keyPressEvent(event)
            return
        if hasattr(self, 'quick_search') and self.quick_search.isVisible():
            self.quick_search.keyPressEvent(event)
            return

        key = event.key()

        if key == Qt.Key.Key_S:
            if not self.inputs_enabled:
                return
            self.disable_inputs()
            self.sound_manager.navigate()
            self.settings_menu.open_menu(self)
            return

        if not self.inputs_enabled:
            return
        if self.progress_dialog and self.progress_dialog.isVisible():
            return

        if key in (Qt.Key.Key_F, Qt.Key.Key_Search, Qt.Key.Key_Menu, Qt.Key.Key_F3):
            self.sound_manager.navigate()
            self.open_quick_search()
            return

        if key == Qt.Key.Key_Down:
            if not self.is_in_menu:
                self.is_in_menu = True
                self.menu_button_index = 0
                self.update_menu_focus()

        elif key == Qt.Key.Key_Up:
            if self.is_in_menu:
                self.is_in_menu = False
                self._reset_menu_styles()

        elif key == Qt.Key.Key_Right:
            if self.is_in_menu:
                self.menu_button_index = (self.menu_button_index + 1) % len(self.menu_buttons)
                self.update_menu_focus()
            elif self.apps and not self.is_animating:
                num_apps = len(self.apps)
                if num_apps <= 5:
                    if self.current_index < num_apps - 1:
                        self.current_index += 1
                        self.animate_carousel("right")
                else:
                    self.current_index = (self.current_index + 1) % num_apps
                    self.animate_carousel("right")

        elif key == Qt.Key.Key_Left:
            if self.is_in_menu:
                self.menu_button_index = (self.menu_button_index - 1) % len(self.menu_buttons)
                self.update_menu_focus()
            elif self.apps and not self.is_animating:
                num_apps = len(self.apps)
                if num_apps <= 5:
                    if self.current_index > 0:
                        self.current_index -= 1
                        self.animate_carousel("left")
                else:
                    self.current_index = (self.current_index - 1) % num_apps
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
                self.sound_manager.back()
                self.is_in_menu = False
                self._reset_menu_styles()
            else:
                self.sound_manager.navigate()
                self.confirm_exit_launcher()

    def _reset_menu_styles(self):
        for action, btn in self.menu_buttons:
            if btn == self.shutdown_btn:
                btn.setStyleSheet(Styles.menu_btn_normal(
                    self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(14), "600"
                ))
            else:
                btn.setStyleSheet(Styles.menu_btn_normal(
                    self.scaling.scale(2), self.scaling.scale(25), self.scaling.scale_font(24), "500"
                ))

    def open_quick_search(self):
        if hasattr(self, 'quick_search'):
            self.quick_search.set_apps(self.apps)
            self.quick_search.show_search()

    def on_search_app_selected(self, app_index):
        if 0 <= app_index < len(self.apps):
            self.current_index = app_index
            self.build_infinite_carousel()
        self.enable_inputs()
        self.setFocus()
        self.activateWindow()

    def on_search_closed(self):
        self.enable_inputs()
        self.setFocus()
        self.activateWindow()

    def closeEvent(self, event):
        if hasattr(self, 'sound_manager'):
            self.sound_manager.cleanup()
        if hasattr(self, 'volume_manager') and self.volume_manager:
            self.volume_manager.cleanup()
        if hasattr(self, 'background_manager'):
            self.background_manager.cleanup()
        if self.download_worker and self.download_worker.isRunning():
            self.download_worker.stop()
            self.download_worker.wait(1000)
        if self.cover_download_worker and self.cover_download_worker.isRunning():
            self.cover_download_worker.stop()
            self.cover_download_worker.wait(1000)
        if self.process_check_timer:
            self.process_check_timer.stop()
        if self.focus_check_timer:
            self.focus_check_timer.stop()
        if hasattr(self, 'clock_timer') and self.clock_timer:
            self.clock_timer.stop()
        if hasattr(self, 'joystick_manager'):
            self.joystick_manager.cleanup()
        cleanup_weather_widget(self)
        event.accept()

    def suspend_linux(self):
        methods = [
            ["systemctl", "suspend"],
            ["dbus-send", "--system", "--print-reply",
             "--dest=org.freedesktop.login1",
             "/org/freedesktop/login1",
             "org.freedesktop.login1.Manager.Suspend",
             "boolean:true"],
            ["sudo", "systemctl", "suspend"],
        ]
        success = False
        for cmd in methods:
            try:
                result = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result == 0:
                    success = True
                    break
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Eccezione durante il comando: {e}")
        if not success:
            self._make_info_dialog(
                "Suspension Error",
                "No suspension method worked.<br>Check your system privileges."
            ).exec()


def main():
    app = QApplication(sys.argv)
    icon_path = "assets/icons/logo48.png"
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Warning: App icon not found in {icon_path}")
    launcher = TVLauncher()

    # Parental Control boot lock 
    # Il launcher è già costruito (e nascosto) ma non ancora mostrato.
    # check_boot_lock() mostra il PIN dialog e ritorna:
    #   True  → PIN corretto (o non configurato) → si procede normalmente
    #   False → utente ha chiuso/annullato        → si esce senza mostrare il launcher
    if not launcher.parental_control.check_boot_lock(None, scaling=launcher.scaling, launcher=launcher):
        sys.exit(0)
    

    launcher.show()
    launcher.setFocus()
    launcher.activateWindow()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
