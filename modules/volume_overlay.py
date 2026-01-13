import sys
import platform
import subprocess
import re
import pygame
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QEvent
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

try:
    import pygame
    pygame.init()
    JOYSTICK_AVAILABLE = pygame.joystick.get_count() >= 0
except ImportError:
    JOYSTICK_AVAILABLE = False
    print("Warning: pygame not installed → Controller volume control DISABLED")
except Exception as e:
    JOYSTICK_AVAILABLE = False
    print(f"Warning: pygame init failed ({e}) → Controller volume control DISABLED")

# Platform detection
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL, CoCreateInstance
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from pycaw.constants import CLSID_MMDeviceEnumerator
        from pycaw.pycaw import IMMDeviceEnumerator, EDataFlow, ERole
        PYCAW_AVAILABLE = True
    except ImportError:
        PYCAW_AVAILABLE = False
        print("Warning: pycaw not installed. Using fallback method.")
    
    VOLUME_AVAILABLE = True
    
elif IS_LINUX:
    # Try to detect which Linux audio backend is available
    LINUX_BACKEND = None
    
    # Test pactl (PulseAudio/PipeWire) - Most modern
    try:
        result = subprocess.run(
            ['pactl', '--version'],
            capture_output=True,
            timeout=1
        )
        if result.returncode == 0:
            LINUX_BACKEND = 'pactl'
            print("Using pactl (PulseAudio/PipeWire)")
    except:
        pass
    
    # Fallback to amixer (ALSA)
    if not LINUX_BACKEND:
        try:
            result = subprocess.run(
                ['amixer', '--version'],
                capture_output=True,
                timeout=1
            )
            if result.returncode == 0:
                LINUX_BACKEND = 'amixer'
                print("Using amixer (ALSA)")
        except:
            pass
    
    VOLUME_AVAILABLE = LINUX_BACKEND is not None
    
    if not VOLUME_AVAILABLE:
        print("❌ No audio backend found!")
        print("   Install: sudo apt install alsa-utils pulseaudio-utils")
else:
    VOLUME_AVAILABLE = False


class VolumeController:
    """Cross-platform volume control with fallback methods"""
    
    def __init__(self):
        self.volume_interface = None
        self.use_fallback = False
        self.linux_backend = None
        
        if not VOLUME_AVAILABLE:
            return
            
        if IS_WINDOWS:
            self._init_windows()
        elif IS_LINUX:
            self.linux_backend = LINUX_BACKEND
            print(f"🔊 Linux audio backend: {self.linux_backend}")
    
    # ============================================
    # WINDOWS INITIALIZATION
    # ============================================
    
    def _init_windows(self):
        """Initialize Windows volume control with fallback"""
        if PYCAW_AVAILABLE:
            try:
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    print("Windows volume initialized (GetSpeakers)")
                    return
                except:
                    pass
                
                try:
                    deviceEnumerator = CoCreateInstance(
                        CLSID_MMDeviceEnumerator,
                        IMMDeviceEnumerator,
                        CLSCTX_ALL
                    )
                    device = deviceEnumerator.GetDefaultAudioEndpoint(
                        EDataFlow.eRender.value, ERole.eMultimedia.value
                    )
                    interface = device.Activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                    )
                    self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    print("Windows volume initialized (CoCreateInstance)")
                    return
                except Exception as e:
                    print(f"⚠️ CoCreateInstance failed: {e}")
                
            except Exception as e:
                print(f"⚠️ pycaw initialization failed: {e}")
        
        print("Using Windows shell command fallback")
        self.use_fallback = True
    
    # ============================================
    # LINUX METHODS - pactl (PulseAudio/PipeWire)
    # ============================================
    
    def _linux_get_volume_pactl(self):
        """Get volume using pactl"""
        try:
            result = subprocess.run(
                ['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    return int(match.group(1))
        except Exception as e:
            print(f"⚠️ pactl get volume error: {e}")
        return 50
    
    def _linux_set_volume_pactl(self, level):
        """Set volume using pactl"""
        try:
            subprocess.run(
                ['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{level}%'],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            print(f"⚠️ pactl set volume error: {e}")
    
    # ============================================
    # LINUX METHODS - amixer (ALSA)
    # ============================================
    
    def _linux_get_volume_amixer(self):
        """Get volume using amixer"""
        try:
            result = subprocess.run(
                ['amixer', 'sget', 'Master'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    return int(match.group(1))
        except Exception as e:
            print(f"⚠️ amixer get volume error: {e}")
        return 50
    
    def _linux_set_volume_amixer(self, level):
        """Set volume using amixer"""
        try:
            subprocess.run(
                ['amixer', 'sset', 'Master', f'{level}%'],
                capture_output=True,
                timeout=1
            )
        except Exception as e:
            print(f"⚠️ amixer set volume error: {e}")
    
    # ============================================
    # WINDOWS FALLBACK METHODS
    # ============================================
    
    def _get_volume_fallback_windows(self):
        """Get volume using PowerShell (fallback for Windows)"""
        try:
            cmd = """
            Add-Type -TypeDefinition @"
            using System.Runtime.InteropServices;
            [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {
                int NotImpl1(); int NotImpl2();
                int GetMasterVolumeLevelScalar(out float pfLevel);
            }
            "@
            $DeviceEnumerator = [System.Runtime.InteropServices.Marshal]::GetActiveObject('MMDeviceEnumerator');
            $AudioEndpoint = $DeviceEnumerator.GetDefaultAudioEndpoint(0, 1);
            $Volume = $AudioEndpoint.Activate([Guid]'5CDF2C82-841E-4546-9722-0CF74078229A', 0, [IntPtr]::Zero);
            $level = 0.0;
            [void]$Volume.GetMasterVolumeLevelScalar([ref]$level);
            [int]($level * 100)
            """
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=2
            )
            return int(result.stdout.strip())
        except Exception as e:
            print(f"⚠️ Error getting fallback volume: {e}")
            return 50
    
    def _set_volume_fallback_windows(self, level):
        """Set volume using PowerShell with incremental adjustment"""
        try:
            current = self._get_volume_fallback_windows()
            diff = level - current
            if abs(diff) < 2:
                return
            
            direction = 175 if diff > 0 else 174
            num_presses = abs(diff) // 2
            if num_presses == 0:
                return
            
            cmd = f"""
            $obj = New-Object -ComObject WScript.Shell;
            for($i=0; $i -lt {num_presses}; $i++) {{ $obj.SendKeys([char]{direction}) }}
            """
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", cmd],
                capture_output=True,
                timeout=5
            )
        except Exception as e:
            print(f"⚠️ Fallback volume set failed: {e}")
    
    # ============================================
    # PUBLIC API - GET VOLUME
    # ============================================
    
    def get_volume(self):
        """Get current volume (0-100)"""
        if not VOLUME_AVAILABLE:
            return 50
            
        try:
            if IS_WINDOWS:
                if self.volume_interface and not self.use_fallback:
                    volume = self.volume_interface.GetMasterVolumeLevelScalar()
                    return int(volume * 100)
                else:
                    return self._get_volume_fallback_windows()
            
            elif IS_LINUX:
                if self.linux_backend == 'pactl':
                    return self._linux_get_volume_pactl()
                elif self.linux_backend == 'amixer':
                    return self._linux_get_volume_amixer()
                
        except Exception as e:
            print(f"⚠️ Error getting volume: {e}")
        
        return 50
    
    # ============================================
    # PUBLIC API - SET VOLUME
    # ============================================
    
    def set_volume(self, level):
        """Set volume (0-100)"""
        if not VOLUME_AVAILABLE:
            return
            
        level = max(0, min(100, level))
        
        try:
            if IS_WINDOWS:
                if self.volume_interface and not self.use_fallback:
                    self.volume_interface.SetMasterVolumeLevelScalar(level / 100.0, None)
                else:
                    self._set_volume_fallback_windows(level)
            
            elif IS_LINUX:
                if self.linux_backend == 'pactl':
                    self._linux_set_volume_pactl(level)
                elif self.linux_backend == 'amixer':
                    self._linux_set_volume_amixer(level)
                
        except Exception as e:
            print(f"⚠️ Error setting volume: {e}")
    
    # ============================================
    # PUBLIC API - VOLUME HELPERS
    # ============================================
    
    def increase_volume(self, step=5):
        """Increase volume by step"""
        current = self.get_volume()
        new_volume = min(100, current + step)
        self.set_volume(new_volume)
        return self.get_volume()
    
    def decrease_volume(self, step=5):
        """Decrease volume by step"""
        current = self.get_volume()
        new_volume = max(0, current - step)
        self.set_volume(new_volume)
        return self.get_volume()


class VolumeOverlay(QWidget):
    """Floating overlay that shows volume level"""
    
    def __init__(self, scaling):
        super().__init__()
        self.scaling = scaling
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self._init_ui()
        self.hide()
    
    def _init_ui(self):
        """Initialize overlay UI"""
        self.setFixedSize(self.scaling.scale(320), self.scaling.scale(100))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(
            self.scaling.scale(20),
            self.scaling.scale(15),
            self.scaling.scale(20),
            self.scaling.scale(15)
        )
        layout.setSpacing(self.scaling.scale(10))
        
        self.label = QLabel("🔊 Volume: 50%")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(self.scaling.scale_font(16))
        font.setBold(True)
        self.label.setFont(font)
        layout.addWidget(self.label)
        
        self.volume_bar = QProgressBar()
        self.volume_bar.setRange(0, 100)
        self.volume_bar.setValue(50)
        self.volume_bar.setTextVisible(False)
        self.volume_bar.setFixedHeight(self.scaling.scale(12))
        layout.addWidget(self.volume_bar)
        
        self.setLayout(layout)
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(30, 30, 30, 230);
                border-radius: {self.scaling.scale(15)}px;
            }}
            QLabel {{
                color: white;
                background: transparent;
            }}
            QProgressBar {{
                background-color: rgba(50, 50, 50, 200);
                border: none;
                border-radius: {self.scaling.scale(6)}px;
            }}
            QProgressBar::chunk {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3,
                    stop:0.5 #42A5F5,
                    stop:1 #90CAF9
                );
                border-radius: {self.scaling.scale(6)}px;
            }}
        """)
    
    def show_volume(self, volume):
        """Show overlay with current volume"""
        if volume == 0:
            icon = "🔇"
        elif volume < 33:
            icon = "🔈"
        elif volume < 66:
            icon = "🔉"
        else:
            icon = "🔊"
        
        self.label.setText(f"{icon} Volume: {volume}%")
        self.volume_bar.setValue(volume)

        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - self.scaling.scale(20)
        y = screen.height() - self.height() - self.scaling.scale(80) 
        
        self.move(x, y)
        self.show()
        self.raise_()
        self.hide_timer.start(2000)


class GlobalVolumeManager(QObject):
    """
     
    
    NON gestisce riconnessioni, NON inizializza nulla.
    Il main gli passa il joystick quando pronto.
    """
    
    volume_changed = pyqtSignal(int)
    show_overlay = pyqtSignal(int)

    def __init__(self, scaling, launcher_window=None):
        """
        Args:
            scaling: Oggetto ResponsiveScaling per UI
            launcher_window: Riferimento al TVLauncher per sapere se un'app è attiva
        """
        super().__init__()
        self.scaling = scaling
        self.launcher_window = launcher_window
        self.joystick = None  # Il main lo imposta
        self.controller = VolumeController()
        self.overlay = VolumeOverlay(scaling)
        
        self.show_overlay.connect(self._show_overlay)
        
        # Stato per modalità volume
        self.volume_mode_active = False
        self.last_volume_buttons = {}
        
        # Flag per sapere se il launcher è in focus
        self.launcher_has_focus = True
        
        # Controller polling (parte quando il main imposta il joystick)
        self.controller_timer = None
        
        # Timer per controllare focus del launcher
        self.focus_check_timer = QTimer()
        self.focus_check_timer.timeout.connect(self._check_launcher_focus)
        self.focus_check_timer.start(500)
        
        

    def set_joystick(self, joystick):
        """
         CHIAMATO DAL MAIN quando il joystick cambia
        
        Args:
            joystick: pygame.joystick.Joystick o None
        """
        if joystick == self.joystick:
            return  # Nessun cambio
        
        # Stop polling precedente
        if self.controller_timer:
            self.controller_timer.stop()
            self.controller_timer = None
        
        self.joystick = joystick
        self.volume_mode_active = False
        self.last_volume_buttons = {}
        
        if joystick is not None:
            # Avvia polling
            self.controller_timer = QTimer()
            self.controller_timer.timeout.connect(self._check_controller_input)
            self.controller_timer.start(100)
            
        else:
            print("🔊 Volume control: Joystick deactivated")

    def _show_overlay(self, volume: int):
        self.overlay.show_volume(volume)

    def _check_launcher_focus(self):
        """Controlla se il launcher ha il focus"""
        if not self.launcher_window:
            return
        
        app_is_running = (
            hasattr(self.launcher_window, 'launched_process') and 
            self.launcher_window.launched_process is not None
        )
        
        old_state = self.launcher_has_focus
        self.launcher_has_focus = not app_is_running
        
        if old_state != self.launcher_has_focus:
            if self.launcher_has_focus:
                print("🔊 Volume control: engaged")
            else:
                
                self.volume_mode_active = False
                self.last_volume_buttons = {}

    def _check_controller_input(self):
        """Polling con sistema COMBO: L2/LT + D-Pad UP/DOWN"""
        if not self.joystick or not self.launcher_has_focus:
            return

        try:
            name = self.joystick.get_name()
            is_playstation = any(x in name for x in ["Wireless Controller", "DualSense", "PS4", "PS5"])
            
            # CONTROLLO TRIGGER
            trigger_pressed = False
            
            try:
                if is_playstation:
                    lt_axis = self.joystick.get_axis(3) if self.joystick.get_numaxes() > 3 else -1
                    trigger_pressed = lt_axis > 0.5
                else:
                    lt_axis = self.joystick.get_axis(2) if self.joystick.get_numaxes() > 2 else -1
                    trigger_pressed = lt_axis > 0.3
            except:
                return

            if not trigger_pressed:
                self.volume_mode_active = False
                self.last_volume_buttons = {}
                return

            self.volume_mode_active = True

            # Lettura D-Pad (SOLO UP/DOWN)
            dpad_up = dpad_down = False
            
            try:
                if is_playstation and self.joystick.get_numbuttons() > 14:
                    dpad_up = self.joystick.get_button(11)
                    dpad_down = self.joystick.get_button(12)
                else:
                    if self.joystick.get_numhats() > 0:
                        hat = self.joystick.get_hat(0)
                        dpad_up = hat[1] == 1
                        dpad_down = hat[1] == -1
            except:
                return

            # Volume su/giù
            if dpad_up and not self.last_volume_buttons.get('up', False):
                self.increase_volume()
                self.last_volume_buttons['up'] = True
            elif dpad_down and not self.last_volume_buttons.get('down', False):
                self.decrease_volume()
                self.last_volume_buttons['down'] = True
            
            if not dpad_up and not dpad_down:
                self.last_volume_buttons['up'] = False
                self.last_volume_buttons['down'] = False

        except Exception as e:  
            pass  # Errore silenzioso

    def increase_volume(self):
        try:
            volume = self.controller.increase_volume(5)
            self.show_overlay.emit(volume)
            self.volume_changed.emit(volume)
        except Exception as e:
            print(f"Error increasing volume: {e}")

    def decrease_volume(self):
        try:
            volume = self.controller.decrease_volume(5)
            self.show_overlay.emit(volume)
            self.volume_changed.emit(volume)
        except Exception as e:
            print(f"Error decreasing volume: {e}")

    def cleanup(self):
        """Cleanup quando l'app si chiude"""
        if self.focus_check_timer:
            self.focus_check_timer.stop()
        if self.controller_timer:
            self.controller_timer.stop()
        self.overlay.hide()
        


#  FUNZIONE DI INSTALLAZIONE SEMPLIFICATA
def install_volume_control(scaling, launcher_window):
    """
    Installa il controllo volume globale (modalità passiva)
    
    Args:
        scaling: Oggetto ResponsiveScaling per UI
        launcher_window: TVLauncher instance
    
    Returns:
        GlobalVolumeManager instance
    
    Usage nel main:
        from modules.volume_overlay import install_volume_control
        
        # Dopo TVLauncher.__init__:
        self.volume_manager = install_volume_control(self.scaling, self)
        
        # In init_joystick() e detect_joystick():
        if self.volume_manager:
            self.volume_manager.set_joystick(self.joystick)
    """
    if not JOYSTICK_AVAILABLE:
        print("⚠️ Volume control: pygame non disponibile")
        return None
    
    volume_manager = GlobalVolumeManager(scaling, launcher_window)
   
    return volume_manager