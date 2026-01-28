import sys
import json
import subprocess
import platform
import os
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
from modules.category_manager import (
    integrate_categories, 
    add_category_navigation_to_keypressevent,
    add_quick_category_shortcut,
    add_category_joystick_support
)

if getattr(sys, 'frozen', False):
    # Se è un bundle/executable
    BASE_DIR = Path(sys.executable).parent
else:
    # Se è script Python normale
    BASE_DIR = Path(__file__).parent

# ✅ FIX: Se siamo in una sottocartella 'modules', sali di un livello
if BASE_DIR.name == 'modules':
    BASE_DIR = BASE_DIR.parent
    print(f"✅ Fixed BASE_DIR from modules to: {BASE_DIR}")

# Cambia la directory di lavoro
os.chdir(BASE_DIR)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
MODULES_DIR = os.path.join(BASE_DIR, 'modules')
OLD_DIR = os.path.join(BASE_DIR, 'old')
CONFIG_FILE = os.path.join(BASE_DIR, 'launcher_apps.json')


# Try to import pygame for joystick support


# Try to import requests for image downloading
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

print(f"🖥️ Operating System: {platform.system()}")
print(f"   IS_LINUX: {IS_LINUX}")
print(f"   IS_WINDOWS: {IS_WINDOWS}")

class ResponsiveScaling:
    """Sistema di scaling responsive basato sulla risoluzione"""
    
    def __init__(self):
        self.BASE_WIDTH = 1920
        self.BASE_HEIGHT = 1080
        
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        width_scale = self.screen_width / self.BASE_WIDTH
        height_scale = self.screen_height / self.BASE_HEIGHT
        self.scale_factor = min(width_scale, height_scale)
        
        print(f"📐 Screen: {self.screen_width}x{self.screen_height}")
        print(f"📐 Scale factor: {self.scale_factor:.2f}")
    
    def scale(self, value):
        return int(value * self.scale_factor)
    
    def scale_font(self, base_size):
        return int(base_size * self.scale_factor)


# === IMAGE MANAGER CLASS ===
class ImageManager:
    
    """Gestisce il download e la cache delle immagini per le app"""
    
    def __init__(self, assets_dir="assets", api_key=None):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(exist_ok=True)
        self.api_key = api_key
        
    def get_app_image(self, app_name, app_path):
        local_image = self._find_local_image(app_name)
        if local_image:
            return str(local_image)
        
        if self.api_key and REQUESTS_AVAILABLE:
            online_image = self._download_from_steamgriddb(app_name)
            if online_image:
                return str(online_image)
        
        return app_path if app_path and os.path.exists(app_path) else None
    
    def _find_local_image(self, app_name):
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
        if not self.api_key or not REQUESTS_AVAILABLE:
            return None
        
        try:
            from urllib.parse import quote
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{quote(app_name)}"
            response = requests.get(search_url, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            if not results.get('data'):
                return None
            
            game_id = results['data'][0]['id']
            
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
            
            image_url = grids['data'][0]['url']
            image_data = requests.get(image_url, timeout=10).content
            
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
        safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        return safe.strip().replace(' ', '_')


# === API KEY DIALOG ===
class ApiKeyDialog(QDialog):
    def __init__(self, current_key="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("SteamGridDB API Key")
        self.setModal(True)
        self.setFixedSize(600, 350)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
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
        
        title = QLabel("🔑 SteamGridDB API Key")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel(
            "To automatically download 16:9 images:\n\n"
            "1. Go to steamgriddb.com\n"
            "2. Create a free account\n"
            "3. Go to Preferences → API\n"
            "4. Generate a API Key and paste it here..."
        )
        info.setStyleSheet("color: #aaa; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        key_label = QLabel("API Key:")
        layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setText(current_key)
        self.key_input.setPlaceholderText("Paste the API Key here...")
        layout.addWidget(self.key_input)
        
        layout.addStretch()
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
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


# === FUNZIONE UTILITY PER ARROTONDARE PIXMAP ===
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
            self.progress_update.emit("Programs already present.", 100)
            self.finished.emit()
            return

        for i, prog in enumerate(to_download):
            if not self.is_running:
                break
            
            percent = int((i + 1) / total * 100)
            self.progress_update.emit(f"Downloading for: {prog['name']}...", percent)
            
            # Scarica immagine 16:9 (se API key c'è)
            if self.image_manager.api_key and REQUESTS_AVAILABLE:
                image_result = self.image_manager.get_app_image(prog['name'], prog['path'])
                if image_result:
                    prog['icon'] = image_result
            
            self.app_ready.emit(prog) # Invia l'app al thread principale
        
        if self.is_running:
            self.progress_update.emit("Completed!", 100)
        else:
            self.progress_update.emit("Cancelled.", 100)
            
        self.finished.emit()

    def stop(self):
        """Ferma il worker in modo sicuro"""
        print("Worker interruption requested")
        self.is_running = False

class CoverDownloadWorker(QThread):
    """Worker thread per scaricare copertine per app esistenti"""
    progress_update = pyqtSignal(str, int)  # Messaggio, percentuale
    cover_downloaded = pyqtSignal(int, str)  # app_index, new_icon_path
    finished = pyqtSignal(int)  # numero di copertine scaricate

    def __init__(self, apps_to_update, image_manager):
        super().__init__()
        self.apps_to_update = apps_to_update  # Lista di tuple (index, app_data)
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
            
            # Scarica immagine 16:9
            image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
            if image_result and image_result != app_data['path']:
                # Emetti solo se abbiamo trovato una copertina diversa dall'exe
                self.cover_downloaded.emit(app_index, image_result)
                updated_count += 1
        
        if self.is_running:
            self.progress_update.emit("Complete!", 100)
        else:
            self.progress_update.emit("Cancelled.", 100)
            
        self.finished.emit(updated_count)

    def stop(self):
        """Ferma il worker in modo sicuro"""
        print("🛑 Cover download worker interruption requested")
        self.is_running = False


class AppTile(QWidget):
    def __init__(self, app_data, scaling, parent=None):
        super().__init__(parent)
        self.app_data = app_data
        self.scaling = scaling
        self.is_focused = False
        self.glow_effect = None  # ✅ AGGIUNTO
       
        # Cache pixmap
        self._normal_pixmap = None
        self._focused_pixmap = None
       
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
        self.setGraphicsEffect(self.shadow)
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
        
        self.set_focused(False)

    def set_focused(self, focused):
        self.is_focused = focused
        icon_path = self.app_data.get('icon')
        
        if focused:
            self.setFixedSize(self.focused_width, self.focused_height)
            self.image_label.setFixedSize(self.focused_img_width, self.focused_img_height)
            
            # Cache pixmap
            if self._focused_pixmap is None and icon_path and Path(icon_path).exists():
                self._focused_pixmap = rounded_pixmap(
                    icon_path, self.focused_img_width, self.focused_img_height, self.border_radius
                )
            
            has_image = False
            if self._focused_pixmap:
                self.image_label.setPixmap(self._focused_pixmap)
                has_image = True
            else:
                self.image_label.setText(self.app_data['name'])
            
            # Stylesheet
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
            
            # ✨ NUOVO: Controlla se il glow è attivo
            glow_enabled = self._is_glow_enabled()
            
            # Imposta shadow SOLO se il glow NON è attivo
            if not glow_enabled:
                # ✨ NUOVO: Verifica che il shadow esista prima di usarlo
                if hasattr(self, 'shadow') and self.shadow:
                    try:
                        self.shadow.setBlurRadius(self.scaling.scale(25))
                        self.shadow.setYOffset(self.scaling.scale(8))
                    except RuntimeError:
                        # Shadow è stato eliminato, ricrealo
                        self._recreate_shadow()
                        self.shadow.setBlurRadius(self.scaling.scale(25))
                        self.shadow.setYOffset(self.scaling.scale(8))
            
            # Avvia glow DOPO aver configurato tutto
            if glow_enabled:
                if self.glow_effect is None:
                    from modules.tile_effects import TileGlowEffect
                    self.glow_effect = TileGlowEffect(self, self.scaling)
                self.glow_effect.start()
            
        else:
            # Ferma glow
            if self.glow_effect:
                self.glow_effect.stop()
            
            # Resto unfocused
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
            
            # ✨ NUOVO: Verifica shadow prima di usarlo
            if hasattr(self, 'shadow') and self.shadow:
                try:
                    self.shadow.setBlurRadius(self.scaling.scale(15))
                    self.shadow.setYOffset(self.scaling.scale(4))
                except RuntimeError:
                    # Shadow è stato eliminato, ricrealo
                    self._recreate_shadow()
                    self.shadow.setBlurRadius(self.scaling.scale(15))
                    self.shadow.setYOffset(self.scaling.scale(4))

    def _recreate_shadow(self):
        """Ricrea il shadow effect se è stato eliminato"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        from PyQt6.QtGui import QColor
        
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(self.scaling.scale(15))
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(self.scaling.scale(4))
        self.shadow.setColor(QColor(0, 0, 0, 180))
        self.image_label.setGraphicsEffect(self.shadow)

    def _is_glow_enabled(self):
        """Verifica se il glow è abilitato nella config"""
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'config_data'):
                    return parent.config_data.get('tile_glow', True)
                parent = parent.parent()
            return True  # Default ON
        except:
            return True


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
        self.setFixedSize(600, 520)  # ✅ Aumentata altezza
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 10px; border-radius: 8px; font-size: 14px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # App Name
        name_label = QLabel("App Name:")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setText(app_data.get('name', ''))
        layout.addWidget(self.name_input)
        
        # Executable Path
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
        
        # Icon Image
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
        
        # ✅ CATEGORIA - AGGIUNTA QUI
        from PyQt6.QtWidgets import QComboBox
        
        category_label = QLabel("Category:")
        category_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(category_label)
        
        self.category_combo = QComboBox()
        if hasattr(parent, 'category_manager'):
            self.category_combo.addItems(parent.category_manager.get_category_names())
        else:
            self.category_combo.addItems(['Games', 'Media', 'Work', 'Other'])
        
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #3a3a3a;
            }
        """)
        
        # Imposta categoria corrente
        current_category = app_data.get('category', 'Other')
        index = self.category_combo.findText(current_category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        layout.addWidget(self.category_combo)
        
        layout.addSpacing(20)
        
        # Buttons
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
                        background-color: #2a2a2a;
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
                        background-color: #2a2a2a;
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
            'icon': self.icon_input.text(),
            'category': self.category_combo.currentText()  # ✅ NUOVO
        }

class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New App")
        self.setModal(True)
        self.setFixedSize(600, 520)
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
        
        # ✅ NUOVO: Aggiungi categoria QUI (PRIMA dei pulsanti)
        category_label = QLabel("Category:")
        category_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(category_label)
        
        from PyQt6.QtWidgets import QComboBox
        self.category_combo = QComboBox()
        if hasattr(parent, 'category_manager'):
            self.category_combo.addItems(parent.category_manager.get_category_names())
        else:
            self.category_combo.addItems(['Games', 'Media', 'Programs', 'Other'])
        
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: white;
                selection-background-color: #3a3a3a;
            }
        """)
        
        # Default: Other
        index = self.category_combo.findText('Other')
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        layout.addWidget(self.category_combo)
        
        layout.addSpacing(20)
        
        # Pulsanti
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
            'icon': self.icon_input.text(),
            'category': self.category_combo.currentText()  # ✅ NUOVO
        }


class TVLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scaling = ResponsiveScaling()
        self.volume_manager = None  # Inizializza a None
        self.config_file = Path("launcher_apps.json")
        self.config_data = self.load_config()
        self.apps = self.config_data.get('apps', [])
        self.background_image = self.config_data.get('background', '')
        self.steamgriddb_api_key = self.config_data.get('steamgriddb_api_key', '')
        self.image_manager = ImageManager(api_key=self.steamgriddb_api_key)
        sound_enabled = self.load_config().get('sound_effects', False)
        self.sound_manager = SoundManager(enabled=sound_enabled)
        self.key_mapper = KeyMapper()
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
        
        
        
        # === INIZIO OTTIMIZZAZIONE #2: INIT VAR WORKER ===
        self.download_worker = None
        self.progress_dialog = None
        self.added_count = 0
        self.cover_download_worker = None
        # === FINE OTTIMIZZAZIONE #2 ===
        
        # === SCALING SYSTEM ===
        

        # Quick Search Widget (DOPO scaling!)

        self.quick_search = QuickSearchWidget(self.scaling, self)
        self.quick_search.app_selected.connect(self.on_search_app_selected)
        self.quick_search.search_closed.connect(self.on_search_closed)
        
        self.volume_manager = install_volume_control(self.scaling, self)
        
        
        


        self.joystick_manager = JoystickManager(self, self.scaling)
        self.init_ui()
        @property
        def joystick(self):
            """Backward compatibility: espone il joystick"""
            return self.joystick_manager.joystick if hasattr(self, 'joystick_manager') else None

        def simulate_key_press(self, key):
            """Backward compatibility: mantiene il vecchio metodo"""
            if hasattr(self, 'joystick_manager'):
                self.joystick_manager._simulate_key(key)

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
            screen.width(),  # Fuori schermo a destra
            0, 
            self.settings_menu.width(), 
            screen.height()
        )

        self.settings_menu.menu_closed.connect(self.on_settings_closed)
        self.settings_menu.raise_()
        self.settings_menu.setGeometry(0, 0, self.settings_menu.width(), self.height())
        show_clock = self.config_data.get('show_clock', True)
        self.toggle_clock_visibility(show_clock)
        self.build_infinite_carousel()
        

    def toggle_clock_visibility(self, visible):
        """Mostra/nascondi l'orologio nell'header mantenendo lo spazio"""
        header_layout = self.centralWidget().layout().itemAt(0).layout()
        clock_layout = header_layout.itemAt(0)
        
        if clock_layout and isinstance(clock_layout, QVBoxLayout):
            for i in range(clock_layout.count()):
                widget = clock_layout.itemAt(i).widget()
                if widget:
                    if not visible:
                        from PyQt6.QtWidgets import QGraphicsOpacityEffect
                        opacity_effect = QGraphicsOpacityEffect()
                        opacity_effect.setOpacity(0)
                        widget.setGraphicsEffect(opacity_effect)
                    else:
                        widget.setGraphicsEffect(None)   
    
    
            
   
  
   
    def disable_inputs(self):
        self.inputs_enabled = False
        print("🎮 Inputs disabled - App in focus")
   
    def enable_inputs(self):
        self.inputs_enabled = True
        print("🎮 Inputs enabled - Launcher in focus")
   
    def check_launched_process(self):
        """✅ FIXED: Controlla se il processo lanciato è ancora in esecuzione"""
        if self.launched_process is None:
            print("⚠️ check_launched_process called but no PID saved")
            return
        
        try:
            # ✅ Verifica se il processo esiste
            process = psutil.Process(self.launched_process)
            
            # ✅ Controlla se è ancora running
            if not process.is_running():
                print(f"🛑 Process {self.launched_process} is not running anymore")
                self.on_app_closed()
                return
            
            # ✅ NUOVO: Controlla anche lo stato del processo
            status = process.status()
            
            # Se è zombie, consideralo terminato
            if status == psutil.STATUS_ZOMBIE:
                print(f"🧟 Process {self.launched_process} is zombie (terminated)")
                self.on_app_closed()
                return
            
            
            
        except psutil.NoSuchProcess:
            print(f"🛑 Process {self.launched_process} no longer exists")
            self.on_app_closed()
        except psutil.AccessDenied:
            print(f"⚠️ Access denied to process {self.launched_process}")
            # Non chiamare on_app_closed qui, potrebbe essere un falso positivo
        except Exception as e:
            print(f"⚠️ Error checking process {self.launched_process}: {e}")

    def check_window_focus(self):
        
        if not IS_LINUX:
            return
        
        # ✅ Solo se gli input sono disabilitati (cioè abbiamo lanciato un'app)
        if not self.inputs_enabled:
            # ✅ Se la nostra finestra ha il focus, l'app è stata chiusa
            if self.isActiveWindow():
                
                self.on_app_closed()       
   
    def on_app_closed(self):
        """✅ FIXED: Chiamato quando l'app lanciata viene chiusa"""
        
        # ✅ Previeni chiamate multiple
        if self.inputs_enabled:
            print("⚠️ on_app_closed called but inputs already enabled")
            return
        
        print("=" * 60)
        print("✅ APP CLOSED - Restoring launcher")
        print("=" * 60)
        
        # ✅ Reset PID
        old_pid = self.launched_process
        self.launched_process = None
        print(f"   Reset PID: {old_pid} → None")
        
        # ✅ Ferma i timer di controllo
        if self.process_check_timer:
            self.process_check_timer.stop()
            self.process_check_timer = None
            print("   ✅ Process check timer stopped")
        
        if self.focus_check_timer:
            self.focus_check_timer.stop()
            self.focus_check_timer = None
            print("   ✅ Focus check timer stopped")
        
        # ✅ Notifica il window manager
        print("   📢 Notifying window manager...")
        self.window_manager.on_app_close()
        
        # ✅ Riabilita gli input
        print("   🎮 Re-enabling inputs...")
        self.enable_inputs()
        
        
        
        print("=" * 60)

    def on_settings_closed(self):
        """Chiamato quando il menu settings viene chiuso"""
        self.enable_inputs()
        self.setFocus()
        self.activateWindow()    
    
    def force_window_focus(self):
        """
        ✅ DEPRECATED: Questo metodo non dovrebbe più essere chiamato
        Il window manager gestisce tutto il ripristino
        
        Mantenuto per compatibilità ma non fa nulla di importante
        """
        print("⚠️ force_window_focus called (deprecated - window manager handles this)")
        
        # Solo assicurati che abbia il focus, ma NON cambiare lo stato fullscreen
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
        overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
        overlay.lower()
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay = overlay
        main_widget = QWidget()
        main_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        main_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # SCALING DEI MARGINI
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
        time_str = now.strftime("%H:%M")
        time_str = now.strftime("%X")
        try:
            test_time = now.strftime("%p")  # Returns AM/PM if locale uses 12-hour
            if test_time:  # If AM/PM exists, use 12-hour format
                time_str = now.strftime("%I:%M %p")
            else:  # Otherwise use 24-hour format
                time_str = now.strftime("%H:%M")
        except:
            time_str = now.strftime("%H:%M")  # Fallback to 24-hour
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
        
        # === NUOVO: SOLO ICONA INGRANAGGIO (Settings) ===
        settings_btn = QPushButton("⚙")  # Oppure usa un'icona
        settings_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        settings_btn.setFixedSize(self.scaling.scale(60), self.scaling.scale(60))
        settings_btn.setToolTip("Settings (Press S)")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: {self.scaling.scale(30)}px;
                font-size: {self.scaling.scale_font(28)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
            }}
        """)
        settings_btn.clicked.connect(lambda: self.settings_menu.open_menu(self))
        header_layout.addWidget(settings_btn)
        
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
        
        # --- INIZIO FIX ---
        # Ripristina l'allineamento originale a sinistra
        main_layout.addWidget(self.carousel_container, alignment=Qt.AlignmentFlag.AlignLeft)
        # --- FINE FIX ---
        
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

        self.sleep_btn = QPushButton("☾")  # Simbolo luna
        self.sleep_btn.setFixedSize(btn_size, btn_size)
        self.sleep_btn.setToolTip("Sleep")
        self.sleep_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.sleep_btn)

        self.shutdown_btn = QPushButton("OFF")  # Simbolo power standard
        self.shutdown_btn.setFixedSize(btn_size, btn_size)
        self.shutdown_btn.setToolTip("Shutdown")
        self.shutdown_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.shutdown_btn)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(btn_size, btn_size)
        self.close_btn.setToolTip("Close")
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button_layout.addWidget(self.close_btn)

        # Aggiorna la lista dei pulsanti (importante per la navigazione!)
        self.menu_buttons = [
            ("restart", self.restart_btn),
            ("sleep", self.sleep_btn),
            ("shutdown", self.shutdown_btn),
            ("close", self.close_btn)
        ]
        for action, btn in self.menu_buttons:
            btn.clicked.connect(lambda checked, a=action: self.execute_menu_action_direct(a))
            if btn == self.shutdown_btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: rgba(255, 255, 255, 0.7);
                        border: 2px solid transparent;
                        border-radius: {self.scaling.scale(25)}px;
                        font-size: {self.scaling.scale_font(14)}px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a;}}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: rgba(255, 255, 255, 0.7);
                        border: 2px solid transparent;
                        border-radius: {self.scaling.scale(25)}px;
                        font-size: {self.scaling.scale_font(24)}px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a;}}
                """)
        menu_layout.addWidget(button_widget)
        menu_layout.addStretch()
        main_layout.addWidget(menu_container)
        
        instructions = QLabel("Navigate: ← → ↑ ↓ or D-Pad/Stick | Launch: Enter/A | Edit: E/X | Delete: Del/Y | Search: F/LB | Exit: Esc/B")
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
        # ✨ NUOVO: Se esiste il backup (categorie attive), salva quello
        apps_to_save = getattr(self, '_all_apps_backup', self.apps)
        
        # Pulisci i dati prima di salvare
        clean_apps = []
        for app in apps_to_save:  # Usa apps_to_save invece di self.apps
            clean_app = {
                'name': str(app.get('name', '')),
                'path': str(app.get('path', '')),
                'icon': str(app.get('icon', '')),
                'category': str(app.get('category', 'Other'))  # ✨ AGGIUNGI CATEGORIA
            }
            # Rimuovi eventuali oggetti Qt che potrebbero essere stati salvati
            if not isinstance(clean_app['icon'], str):
                clean_app['icon'] = clean_app['path']
            clean_apps.append(clean_app)
        
        config_data = {
            'apps': clean_apps,
            'background': self.background_image,
            'steamgriddb_api_key': self.steamgriddb_api_key,
            'show_clock': self.config_data.get('show_clock', True),
            'auto_download': self.config_data.get('auto_download', True),
            'tile_glow': self.config_data.get('tile_glow', True),
            'sound_effects': self.config_data.get('sound_effects', False),
            'fullscreen': self.config_data.get('fullscreen', True),
        }
        
        # Salva anche le categorie
        config_data = self.category_manager.save_categories(config_data)
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)

    def _on_category_changed(self, category_index):
        """Chiamato quando cambia la categoria"""
        self.current_index = 0
        self.build_infinite_carousel()
        print(f"📂 Switched to: {self.category_manager.get_current_category()['name']}")       
   
    def set_api_key(self):
        """Apre il dialog per impostare la API key"""
        dialog = ApiKeyDialog(self.steamgriddb_api_key, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key = dialog.get_api_key()
            if new_key != self.steamgriddb_api_key:
                old_key = self.steamgriddb_api_key
                self.steamgriddb_api_key = new_key
                self.image_manager = ImageManager(api_key=self.steamgriddb_api_key)
                self.save_config()
                
                if new_key:
                    # Se è stata aggiunta una nuova API key e ci sono app
                    if not old_key and self.apps:
                        # Avvia direttamente il download (la conferma è dentro il metodo)
                        self.download_covers_for_existing_apps()
                    else:
                        QMessageBox.information(
                            self,
                            "API Key Saved",
                            "✅ API Key successfully saved!\n\n"
                            "Now you can download the 16:9 images\n"
                            "when you add a new app into the launcher."
                        )
                else:
                    QMessageBox.information(
                        self,
                        "API Key Removed",
                        "API Key removed. The Launcher will use only\n"
                        "local images and exe icons."
                    )
        
        self.setFocus()
        self.activateWindow()

    def download_covers_for_existing_apps(self):
        """Scarica le copertine per tutte le app esistenti che non ne hanno una"""
        
        # Controlla se c'è l'API key
        if not self.steamgriddb_api_key:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("API Key Required")
            msg_box.setText(
                "<div style='margin-bottom: 15px;'>"
                "You need a <b>SteamGridDB API Key</b> to download covers."
                "</div>"
                "<div>Do you want to set it now?</div>"
            )
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
            msg_box.setIcon(QMessageBox.Icon.Question)
            
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1a1a1a;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border-color: #666;
                }
                QPushButton:pressed {
                    background-color: #4a4a4a;
                }
            """)
            
            reply = msg_box.exec()
            if reply == QMessageBox.StandardButton.Yes:
                self.set_api_key()
            return
        
        # Controlla se requests è disponibile
        if not REQUESTS_AVAILABLE:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Missing Library")
            msg_box.setText(
                "<div style='margin-bottom: 15px;'>"
                "The <b>'requests'</b> library is not installed."
                "</div>"
                "<div style='color: #aaa; font-size: 12px;'>"
                "Install it with: <span style='color: #6cf;'>pip install requests</span>"
                "</div>"
            )
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1a1a1a;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border-color: #666;
                }
            """)
            
            msg_box.exec()
            return
        
        # Controlla se ci sono app
        if not self.apps:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("No Apps")
            msg_box.setText(
                "<div style='text-align: center; margin: 10px;'>"
                "Add some apps first before downloading covers! 🎮"
                "</div>"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1a1a1a;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
            """)
            
            msg_box.exec()
            return
        
        # Trova le app che necessitano di una copertina
        apps_to_update = []
        for i, app in enumerate(self.apps):
            icon_path = app.get('icon', '')
            app_path = app.get('path', '')
            
            needs_update = False
            
            if not icon_path:
                needs_update = True
            elif icon_path == app_path:
                needs_update = True
            elif icon_path.lower().endswith('.exe'):
                needs_update = True
            elif not Path(icon_path).exists():
                needs_update = True
            
            if needs_update:
                apps_to_update.append((i, app))
        
        if not apps_to_update:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("All Set!")
            msg_box.setText(
                "<div style='text-align: center; margin: 10px;'>"
                "All apps already have custom covers! ✅"
                "</div>"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #1a1a1a;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                }
            """)
            
            msg_box.exec()
            return
        
        # Mostra quante app verranno aggiornate
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Download Covers")
        msg_box.setText(
            f"<div style='margin-bottom: 15px;'>"
            f"Found <b>{len(apps_to_update)}</b> app(s) without custom covers."
            f"</div>"
            f"<div>Do you want to download covers for them?</div>"
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: 10px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-color: #666;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
        """)
        
        reply = msg_box.exec()
        
        if reply != QMessageBox.StandardButton.Yes:
            self.setFocus()
            self.activateWindow()
            return
        
        # Crea progress dialog (già con il nuovo stile)
        self.progress_dialog = QProgressDialog(
            f"Downloading covers for {len(apps_to_update)} apps...", 
            "Cancel", 
            0, 
            100, 
            self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setWindowTitle("Downloading Covers")
        self.progress_dialog.setFixedSize(self.scaling.scale(450), self.scaling.scale(150))
        self.progress_dialog.setValue(0)
        
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
        
        # Crea e avvia il worker
        self.cover_download_worker = CoverDownloadWorker(apps_to_update, self.image_manager)
        self.cover_download_worker.progress_update.connect(self._on_cover_download_progress)
        self.cover_download_worker.cover_downloaded.connect(self._on_cover_downloaded)
        self.cover_download_worker.finished.connect(self._on_cover_download_finished)
        
        self.progress_dialog.canceled.connect(self.cover_download_worker.stop)
        
        self.cover_download_worker.start()
        self.progress_dialog.show()


    # Aggiorna anche il metodo _on_cover_download_finished:
    

    def _on_cover_downloaded(self, app_index, new_icon_path):
        """Chiamato quando una copertina viene scaricata con successo"""
        if 0 <= app_index < len(self.apps):
            # Aggiorna l'icona dell'app
            self.apps[app_index]['icon'] = new_icon_path
            print(f" Cover updated for: {self.apps[app_index]['name']}")

    def _on_cover_download_finished(self, updated_count):
        """Chiamato al termine del download di tutte le copertine"""
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
        
        # Message box con nuovo stile
        msg_box = QMessageBox(self)
        
        if updated_count > 0:
            msg_box.setWindowTitle("Download Complete")
            msg_box.setText(
                f"<div style='text-align: center; margin: 10px;'>"
                f"✅ Successfully downloaded <b>{updated_count}</b> cover(s)!"
                f"</div>"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setWindowTitle("Download Complete")
            msg_box.setText(
                "<div style='text-align: center; margin: 10px;'>"
                "No new covers were downloaded."
                "</div>"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
        
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: 10px 30px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        
        msg_box.exec()
        
        self.cover_download_worker = None
        self.setFocus()
        self.activateWindow()
   
    def update_background(self):
        if self.background_image and Path(self.background_image).exists():
            self._set_scaled_background(self.background_image)
        else:
            # Default: usa uno sfondo dalla cartella assets/wallpapers
            default_wallpaper = os.path.join(ASSETS_DIR, 'wallpapers', 'default.jpg')
            if os.path.exists(default_wallpaper):  # ← CAMBIA Path() in os.path.exists()
                self._set_scaled_background(default_wallpaper)
            else:
                # Fallback se non c'è neanche il default
                self.setStyleSheet("""
                    QMainWindow {
                        background-color: #2a2a2a;
                    }
                """)
                if hasattr(self, 'overlay'):
                    self.overlay.setStyleSheet("background-color: transparent;")
                    
    def _set_scaled_background(self, image_path):
        """Imposta uno sfondo scalato per riempire la finestra"""
        from PyQt6.QtGui import QBrush  # ← Assicurati che QBrush sia importato
        
        screen = QApplication.primaryScreen().geometry()
        pixmap = QPixmap(image_path)
        
        # Scala il pixmap per riempire lo schermo (equivalente di background-size: cover)
        scaled_pixmap = pixmap.scaled(
            screen.width(), 
            screen.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Centra il pixmap se è più grande dello schermo
        if scaled_pixmap.width() > screen.width() or scaled_pixmap.height() > screen.height():
            x = (scaled_pixmap.width() - screen.width()) // 2
            y = (scaled_pixmap.height() - screen.height()) // 2
            scaled_pixmap = scaled_pixmap.copy(x, y, screen.width(), screen.height())
        
        palette = self.palette()
        brush = QBrush(scaled_pixmap)  # ← Crea QBrush dal pixmap
        palette.setBrush(self.backgroundRole(), brush)
        self.setPalette(palette)
        
        if hasattr(self, 'overlay'):
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")                
   
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
                            border: 2px solid white;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: 700;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a;}}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.95);
                            color: #000000;
                            border: 2px solid white;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(24)}px;
                            font-weight: 600;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a;}}
                    """)
            else:
                if btn == self.shutdown_btn:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.1);
                            color: rgba(255, 255, 255, 0.7);
                            border: 2px solid transparent;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: 600;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a;}}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 0.1);
                            color: rgba(255, 255, 255, 0.7);
                            border: 2px solid transparent;
                            border-radius: {self.scaling.scale(25)}px;
                            font-size: {self.scaling.scale_font(24)}px;
                            font-weight: 500;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a;}}
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
        elif action == "sleep":  # ← AGGIUNGI QUESTO
            self.confirm_action("sleep")    
   
    def confirm_action(self, action):
        action_text = {
        "restart": "Restart",
        "shutdown": "Shutdown",
        "sleep": "Suspend"
        }.get(action, action.capitalize())
    
        confirm_dialog = QDialog(self)
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
        message = QLabel(f"Are you sure you want to {action_text.lower()} the computer?")
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

    def confirm_exit_launcher(self):
        """Mostra dialog di conferma per uscita dal launcher"""
        # ✅ Attiva flag per supporto joypad
        self._exit_dialog_active = True
        
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Confirm Exit")
        confirm_dialog.setModal(True)
        confirm_dialog.setFixedSize(400, 200)
        confirm_dialog.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QPushButton { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: 12px 30px; 
                border-radius: 8px; 
                font-size: 14px; 
                font-weight: bold; 
            }
            QPushButton:focus { 
                background-color: #3a3a3a; 
                border: 3px solid white; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Messaggio
        message = QLabel("Are you sure you want to close the launcher?")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Pulsanti
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
        
        # Sistema di navigazione (identico a confirm_action)
        confirm_buttons = [yes_btn, no_btn]
        confirm_index = [1]  # Default su "No"
        
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
                        QPushButton:hover { background-color: #3a3a3a; }
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
                        QPushButton:hover { background-color: #3a3a3a; }
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
        
        # Mostra dialog
        result = confirm_dialog.exec()
        
        # ✅ Disattiva flag
        self._exit_dialog_active = False
        
        # Chiudi se confermato
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
                    # Windows: sospensione ibrida (più veloce del semplice sleep)
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)

            elif system == "Linux":
                if action == "restart":
                    # systemd (99% delle distro moderne)
                    subprocess.run(["systemctl", "reboot"], check=False)
                    # fallback per sistemi senza systemd
                    subprocess.run(["reboot"], check=False)

                elif action == "shutdown":
                    subprocess.run(["systemctl", "poweroff"], check=False)
                    subprocess.run(["shutdown", "-h", "now"], check=False)

                elif action == "sleep":
                    # Metodo universale su Linux con systemd (funziona ovunque)
                    subprocess.run(["systemctl", "suspend"], check=True)

            

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Errore", f"Comando fallito. Sei loggato con privilegi sufficienti?")
        except FileNotFoundError:
            QMessageBox.critical(self, "Errore", f"Comando non trovato. Stai usando {system}?")
        except Exception as e:
            QMessageBox.critical(self, "Errore", f"Impossibile eseguire {action}:\n{str(e)}")
   
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
            empty_label.setStyleSheet("color: #666; font-size: 18px;")
            empty_label.move(0, 100)
            return
        if self.current_index >= len(self.apps):
            self.current_index = 0
        num_apps = len(self.apps)
        
        # Se ci sono 5 o meno app, mostra solo quelle senza ripetizioni
        if num_apps <= 5:
            for i in range(num_apps):
                tile = AppTile(self.apps[i], self.scaling, self.carousel_container)
                tile.app_index = i
                is_focused = (i == self.current_index)
                tile.set_focused(is_focused)
                self.tiles.append(tile)
        else:
            # MODIFICATO: center_tile_index ora è 0 (sinistra) invece di 4 (centro)
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
        
        # Con 5 o meno app, allinea a sinistra con la focused per prima
        if num_apps <= 5:
            # MODIFICATO: Inizia dal margine sinistro invece del centro
            start_x = self.scaling.scale(5)  # Margine sinistro
            
            x_pos = int(start_x)
            for i, tile in enumerate(self.tiles):
                tile.move(int(x_pos), 22)
                # Usa la larghezza effettiva della tile (normale o focused)
                if i == self.current_index:
                    x_pos += self.focused_width + self.tile_spacing
                else:
                    x_pos += self.normal_width + self.tile_spacing
        else:
            # MODIFICATO: Usa la logica originale ma adattata per left alignment
            center_tile_index = 0
            
            # Posizione iniziale: margine sinistro
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
        
        # Con 5 o meno app: solo cambio focus e riposizionamento
        if num_apps <= 5:
            for i, tile in enumerate(self.tiles):
                tile.set_focused(i == self.current_index)
            self._position_all_tiles()  # Riposiziona dopo il cambio di dimensione
            return  # ESCE QUI, non chiama reposition_tiles
        
        # Comportamento per molte app
        self.is_animating = True
        shift_distance = self.tile_width + self.tile_spacing
        
        # CRITICAL: When moving left, we need to add the new tile BEFORE animation
        if direction == "left":
            # Pre-add the tile that will come from the left
            # We need to reuse the rightmost tile (last in array)
            last_tile = self.tiles[-1]  # Get reference but don't remove yet
            new_app_idx = self.current_index % num_apps
            last_tile.app_data = self.apps[new_app_idx]
            last_tile.app_index = new_app_idx
            
            # Invalida cache pixmap
            last_tile._normal_pixmap = None
            last_tile._focused_pixmap = None
            
            last_tile.name_label.setText(self.apps[new_app_idx]['name'])
            last_tile.set_focused(False)
            
            # Position it OFF-SCREEN to the left BEFORE moving it
            start_x = self.scaling.scale(50)
            last_tile.move(int(start_x - shift_distance), 0)
            
            # Now remove from end and insert at beginning
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
        """Riposiziona le tiles dopo l'animazione del carosello infinito"""
        num_apps = len(self.apps)
        center_tile_index = 0  # Focus is now on the left
        
        if direction == "right":
            # Moving right: remove leftmost tile, add new one to the right
            first_tile = self.tiles.pop(0)
            new_app_idx = (self.current_index + (self.max_visible_tiles - 1)) % num_apps
            first_tile.app_data = self.apps[new_app_idx]
            first_tile.app_index = new_app_idx
            
            # Invalida cache pixmap
            first_tile._normal_pixmap = None
            first_tile._focused_pixmap = None
            
            first_tile.name_label.setText(self.apps[new_app_idx]['name'])
            first_tile.set_focused(False)
            self.tiles.append(first_tile)
        else:
            # Moving left: tile was already repositioned in animate_carousel
            # We need to update the rightmost tile for the next scroll
            last_tile = self.tiles[-1]
            new_app_idx = (self.current_index + (self.max_visible_tiles - 1)) % num_apps
            last_tile.app_data = self.apps[new_app_idx]
            last_tile.app_index = new_app_idx
            
            # Invalida cache pixmap
            last_tile._normal_pixmap = None
            last_tile._focused_pixmap = None
            
            last_tile.name_label.setText(self.apps[new_app_idx]['name'])
            last_tile.set_focused(False)
            
        for i, tile in enumerate(self.tiles):
            tile.set_focused(i == center_tile_index)
            
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
            self.progress_dialog = QProgressDialog("Image searching in progress..", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Add programs")
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
        clean_app_data = {
            'name': app_data.get('name', ''),
            'path': app_data.get('path', ''),
            'icon': app_data.get('icon', ''),
            'category': self.category_manager.get_default_category()  # ✅ NUOVO
        }

        # Assicurati che 'icon' sia una stringa (percorso) e non un QPixmap
        if isinstance(clean_app_data['icon'], QPixmap):
            clean_app_data['icon'] = app_data.get('path', '')
        
        self.apps.append(clean_app_data)
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
                QMessageBox.information(self, "Done!", f"Added {self.added_count} program(s) successfully!")
            else:
                QMessageBox.information(self, "Info", "No new program added (may be already present).")

        self.download_worker = None # Pulisci il riferimento al worker
        self.added_count = 0 # Resetta contatore
        
        self.setFocus()
        self.activateWindow()

    def _on_cover_download_progress(self, message, percent):
        """Aggiorna il progress dialog per il download delle copertine"""
        if self.progress_dialog:
            self.progress_dialog.setLabelText(message)
            self.progress_dialog.setValue(percent)

    def _on_cover_downloaded(self, app_index, new_icon_path):
        """Chiamato quando una copertina viene scaricata con successo"""
        if 0 <= app_index < len(self.apps):
            #  Assicurati che sia una stringa
            self.apps[app_index]['icon'] = str(new_icon_path)
            print(f" Updated cover for: {self.apps[app_index]['name']}")     
    # ==========================================
    # === FINE OTTIMIZZAZIONE #2: METODI WORKER ===
    # ==========================================
   
    def add_app(self):
        dialog = AddAppDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_data = dialog.get_app_data()
            if app_data['name'] and app_data['path']:
                # ✅ NUOVO: Se non ha categoria, usa la default
                if not app_data.get('category'):
                    app_data['category'] = self.category_manager.get_default_category()
                
                # Download immagine (codice esistente)
                if (not app_data['icon'] or app_data['icon'] == app_data['path']) and self.image_manager.api_key and REQUESTS_AVAILABLE:
                    print(f"Searching image for: {app_data['name']}")
                    
                    image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
                    if image_result:
                        app_data['icon'] = image_result
                        print(f"✅ Image found: {app_data['name']}")
                    else:
                        print(f"⚠️ No image found, using exe icon")
                
                # ✨ FIX: AGGIUNGI SOLO AL BACKUP (se esiste), altrimenti a self.apps
                if hasattr(self, '_all_apps_backup'):
                    self._all_apps_backup.append(app_data)
                else:
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
            removed_app = self.apps[self.current_index]
            
            # ✨ FIX: RIMUOVI SOLO DAL BACKUP (se esiste), altrimenti da self.apps
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
        """✅ FIXED: Lancia l'app isolando le variabili d'ambiente"""
        if not self.apps:
            return
        
        app = self.apps[self.current_index]
        
        try:
            print(f"🚀 Launching: {app['name']}")
            print(f"   Command: {app['path']}")
            
            # ✅ FLATPAK FIX: Killa processi zombie prima di lanciare
            if 'flatpak' in app['path'].lower() or 'kodi' in app['name'].lower():
                print(f"   🧹 Cleaning up potential Flatpak/Kodi zombies...")
                try:
                    subprocess.run(['flatpak', 'kill', 'tv.kodi.Kodi'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                timeout=2)
                    
                    subprocess.run(['pkill', '-9', '-f', 'kodi'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                timeout=2)
                    
                    import time
                    time.sleep(1)
                    print(f"   ✅ Cleanup completed")
                except Exception as e:
                    print(f"   ⚠️ Cleanup warning (non-critical): {e}")
                    pass
            
            # ✅ CRITICO: Crea un ambiente pulito senza le variabili Python embedded
            clean_env = os.environ.copy()
            
            # Rimuovi SOLO le variabili Python che potrebbero causare conflitti
            # ⚠️ NON toccare LD_LIBRARY_PATH! Troppo pericoloso per Flatpak/Steam/AppImage
            env_vars_to_remove = [
                'PYTHONHOME',
                'PYTHONPATH', 
                'PYTHONEXECUTABLE',
                'PYTHONUSERBASE',
                '_PYTHON_SYSCONFIGDATA_NAME',
                '_PYTHON_PROJECT_BASE',
            ]
            
            for var in env_vars_to_remove:
                clean_env.pop(var, None)
            
            print(f"   🧹 Cleaned Python environment variables (LD_LIBRARY_PATH untouched)")
            
            # ✅ Lancia il processo con l'ambiente pulito
            process = subprocess.Popen(
                app['path'],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=clean_env  # ← IMPORTANTE: usa l'ambiente pulito
            )
            
            # ✅ Salva il PID
            self.launched_process = process.pid
            print(f"   PID: {self.launched_process}")
            
            # ✅ Disabilita input
            self.disable_inputs()
            
            # ✅ Notifica il window manager
            self.window_manager.on_app_launch()
            
            # ✅ Avvia i timer di controllo
            if self.process_check_timer:
                self.process_check_timer.stop()
            
            self.process_check_timer = QTimer()
            self.process_check_timer.timeout.connect(self.check_launched_process)
            self.process_check_timer.start(1000)
            print("   ✅ Process check timer started")
            
            if IS_LINUX:
                if self.focus_check_timer:
                    self.focus_check_timer.stop()
                
                self.focus_check_timer = QTimer()
                self.focus_check_timer.timeout.connect(self.check_window_focus)
                self.focus_check_timer.start(500)
                print("   ✅ Focus check timer started (Linux)")
            
            print(f"✅ App launched successfully with clean environment")
            
        except Exception as e:
            print(f"❌ Launch error: {e}")
            QMessageBox.critical(self, "Launch Error", f"Could not launch app:\n{str(e)}")
            self.enable_inputs()
    
        
   
    def keyPressEvent(self, event: QKeyEvent):
        # ✅ PRIMA: Controlla se il settings menu è aperto
        if add_category_navigation_to_keypressevent(self, event):
            return

        if hasattr(self, 'settings_menu') and getattr(self.settings_menu, 'is_open', False):
            self.settings_menu.keyPressEvent(event)
            return
        
        # ✅ SECONDA: Controlla se la ricerca è aperta
        if hasattr(self, 'quick_search') and self.quick_search.isVisible():
            self.quick_search.keyPressEvent(event)
            return
        
        key = event.key()
        
        # ✅ TASTO 'S' DEVE ESSERE CONTROLLATO PRIMA DI inputs_enabled!
        if key == Qt.Key.Key_S:
            if not self.inputs_enabled:
                return
            self.disable_inputs()
            self.sound_manager.navigate()
            self.settings_menu.open_menu(self)
            return
        
        # ✅ ADESSO controlla se input disabilitati
        if not self.inputs_enabled:
            return
        
        # ✅ Non permettere input se dialog progresso attivo
        if self.progress_dialog and self.progress_dialog.isVisible():
            return
        
        # ✅ APRI QUICK SEARCH CON 'F'
        if key in (Qt.Key.Key_F, Qt.Key.Key_Search, Qt.Key.Key_Menu, Qt.Key.Key_F3):
            self.sound_manager.navigate()
            self.open_quick_search()
            return
        # ------------------------------        
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
                num_apps = len(self.apps)
                if num_apps <= 5:
                    # Con poche app: scorrimento lineare
                    if self.current_index < num_apps - 1:
                        self.current_index += 1
                        self.animate_carousel("right")
                else:
                    # Con molte app: comportamento infinito ORIGINALE
                    self.current_index = (self.current_index + 1) % len(self.apps)
                    self.animate_carousel("right")
        elif key == Qt.Key.Key_Left:
            if self.is_in_menu:
                self.menu_button_index = (self.menu_button_index - 1) % len(self.menu_buttons)
                self.update_menu_focus()
            elif self.apps and not self.is_animating:
                num_apps = len(self.apps)
                if num_apps <= 5:
                    # Con poche app: scorrimento lineare
                    if self.current_index > 0:
                        self.current_index -= 1
                        self.animate_carousel("left")
                else:
                    # Con molte app: comportamento infinito ORIGINALE
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
                # ESC esce dal menu basso
                self.sound_manager.back()
                self.is_in_menu = False
                
                # Reset stili menu
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
                # ✅ ESC dalla schermata principale = conferma uscita
                self.sound_manager.navigate()
                self.confirm_exit_launcher()

    def open_quick_search(self):
        '''Apre il widget di ricerca rapida'''
        if hasattr(self, 'quick_search'):
            self.quick_search.set_apps(self.apps)
            self.quick_search.show_search()

    def on_search_app_selected(self, app_index):
        """Gestisce la selezione di un'app dalla ricerca"""
        if 0 <= app_index < len(self.apps):
            self.current_index = app_index
            self.build_infinite_carousel()

        self.enable_inputs()
        self.setFocus()
        self.activateWindow()

    def on_search_closed(self):
        """Gestisce la chiusura della ricerca"""
        self.enable_inputs()
        self.setFocus()
        self.activateWindow()

   
    def closeEvent(self, event):

        if hasattr(self, 'sound_manager'):
         self.sound_manager.cleanup()
        if hasattr(self, 'volume_manager') and self.volume_manager:
            self.volume_manager.cleanup() 
        # Assicurati di fermare i worker se sono in esecuzione
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
        if hasattr(self, 'joystick_manager'):
            self.joystick_manager.cleanup()
          
        event.accept()
    def suspend_linux(self):
        """Tenta di mettere il sistema operativo Linux in sospensione usando vari metodi."""
        
        print("Tentativo di sospensione Linux avviato...")
        
        methods = [
            # Metodo 1: Systemd standard (funziona se l'utente ha i permessi via PolicyKit)
            ["systemctl", "suspend"],
            
            # Metodo 2: D-Bus (metodo standard per ambienti desktop)
            ["dbus-send", "--system", "--print-reply", 
             "--dest=org.freedesktop.login1", 
             "/org/freedesktop/login1", 
             "org.freedesktop.login1.Manager.Suspend", 
             "boolean:true"],
            
            # Metodo 3: Sudo Systemctl (Richiede la configurazione NOPASSWD al punto 3)
            ["sudo", "systemctl", "suspend"],
        ]

        success = False
        for cmd in methods:
            try:
                print(f"Provo comando: {' '.join(cmd)}")
                # Usiamo subprocess.call per lanciare il comando. 
                # Devnull nasconde l'output non necessario.
                result = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if result == 0:
                    print("Sospensione avviata con successo.")
                    success = True
                    break 
                else:
                    print(f"Comando fallito con codice uscita: {result}")
            
            except FileNotFoundError:
                print(f"Comando {cmd[0]} non trovato sul sistema.")
            except Exception as e:
                print(f"Eccezione durante il comando: {e}")

        if not success:
            QMessageBox.critical(self, "Errore Sospensione", 
                                 "Nessun metodo di sospensione ha funzionato. \nVerifica i permessi.")    

def main():
    app = QApplication(sys.argv)
    
    icon_path = Path("assets/icons/logo48.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    launcher = TVLauncher()
    
    launcher.show()
    launcher.setFocus()
    launcher.activateWindow()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()