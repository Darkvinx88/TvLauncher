import json
import subprocess

import psutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QDialog, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QPoint, QSize,
    QParallelAnimationGroup, QTimer, QCoreApplication
)
from PyQt6.QtGui import QKeyEvent, QIcon

from .add_app_dialog import AddAppDialog
from .app_tile import AppTile
from .download_worker import DownloadWorker
from .edit_app_dialog import EditAppDialog
from .program_scan_dialog import ProgramScanDialog
from .responsive_scaling import ResponsiveScaling
from .image_manager import ImageManager
from .api_key_dialog import ApiKeyDialog
from pathlib import Path

# Try to import pygame for joystick support
try:
    import pygame
    JOYSTICK_AVAILABLE = True
except ImportError:
    JOYSTICK_AVAILABLE = False
    print("Warning: pygame not installed. Joystick support disabled.")
    print("Install with: pip install pygame")

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
            self.progress_dialog = QProgressDialog("Image Searching in progress...", "Cancel", 0, 100, self)
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setWindowTitle("Adding programs")
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
                QMessageBox.information(self, "Done!", f"Added {self.added_count} program(s) successfully!")
            else:
                QMessageBox.information(self, "Info", "No new program added (may be already present).")

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
                if (not app_data['icon'] or app_data['icon'] == app_data['path']) and self.image_manager.api_key:
                    print(f"📥 Searching image for: {app_data['name']}")
                    
                    image_result = self.image_manager.get_app_image(app_data['name'], app_data['path'])
                    if image_result:
                        app_data['icon'] = image_result
                        print(f"✅ Image found: {app_data['name']}")
                    else:
                        print(f"⚠️ No image found, using exe icon")
                
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
