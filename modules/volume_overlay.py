import sys
import platform
import subprocess
import re
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

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
    LINUX_BACKEND = None
    
    try:
        result = subprocess.run(['pactl', '--version'], capture_output=True, timeout=1)
        if result.returncode == 0:
            LINUX_BACKEND = 'pactl'
            print("Using pactl (PulseAudio/PipeWire)")
    except:
        pass
    
    if not LINUX_BACKEND:
        try:
            result = subprocess.run(['amixer', '--version'], capture_output=True, timeout=1)
            if result.returncode == 0:
                LINUX_BACKEND = 'amixer'
                print("Using amixer (ALSA)")
        except:
            pass
    
    VOLUME_AVAILABLE = LINUX_BACKEND is not None
    
    if not VOLUME_AVAILABLE:
        print("❌ No audio backend found!")
else:
    VOLUME_AVAILABLE = False


class VolumeController:
    """Cross-platform volume control"""
    
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
    
    def _init_windows(self):
        if PYCAW_AVAILABLE:
            try:
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    print("Windows volume initialized (GetSpeakers)")
                    return
                except:
                    pass
                
                try:
                    deviceEnumerator = CoCreateInstance(CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, CLSCTX_ALL)
                    device = deviceEnumerator.GetDefaultAudioEndpoint(EDataFlow.eRender.value, ERole.eMultimedia.value)
                    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    print("Windows volume initialized (CoCreateInstance)")
                    return
                except:
                    pass
            except:
                pass
        
        self.use_fallback = True
    
    def _linux_get_volume_pactl(self):
        try:
            result = subprocess.run(['pactl', 'get-sink-volume', '@DEFAULT_SINK@'],
                                  capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                match = re.search(r'(\d+)%', result.stdout)
                if match:
                    return int(match.group(1))
        except:
            pass
        return 50
    
    def _linux_set_volume_pactl(self, level):
        try:
            subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{level}%'],
                         capture_output=True, timeout=1)
        except:
            pass
    
    def _linux_get_volume_amixer(self):
        try:
            result = subprocess.run(['amixer', 'sget', 'Master'],
                                  capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    return int(match.group(1))
        except:
            pass
        return 50
    
    def _linux_set_volume_amixer(self, level):
        try:
            subprocess.run(['amixer', 'sset', 'Master', f'{level}%'],
                         capture_output=True, timeout=1)
        except:
            pass
    
    def _get_volume_fallback_windows(self):
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
            result = subprocess.run(["powershell", "-Command", cmd],
                                  capture_output=True, text=True, timeout=2)
            return int(result.stdout.strip())
        except:
            return 50
    
    def _set_volume_fallback_windows(self, level):
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
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", cmd],
                         capture_output=True, timeout=5)
        except:
            pass
    
    def get_volume(self):
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
        except:
            pass
        
        return 50
    
    def set_volume(self, level):
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
        except:
            pass
    
    def increase_volume(self, step=5):
        current = self.get_volume()
        new_volume = min(100, current + step)
        self.set_volume(new_volume)
        return self.get_volume()
    
    def decrease_volume(self, step=5):
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
   
    
    volume_changed = pyqtSignal(int)
    show_overlay = pyqtSignal(int)

    def __init__(self, scaling, launcher_window=None):
        super().__init__()
        self.scaling = scaling
        self.launcher_window = launcher_window
        self.controller = VolumeController()
        self.overlay = VolumeOverlay(scaling)
        
        self.show_overlay.connect(self._show_overlay)
        
        # Flag pubblico che il JoystickManager può leggere
        self.volume_mode_active = False
        
        

    def _show_overlay(self, volume: int):
        self.overlay.show_volume(volume)

    def is_launcher_focused(self):
        """Helper per sapere se il launcher è in focus"""
        if not self.launcher_window:
            return True
        
        return not (
            hasattr(self.launcher_window, 'launched_process') and 
            self.launcher_window.launched_process is not None
        )

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
        self.overlay.hide()


def install_volume_control(scaling, launcher_window):
    """
    
    Il polling è gestito dal JoystickManager
    
    Usage nel main (tvlauncher.py):
        self.volume_manager = install_volume_control(self.scaling, self)
    """
    if not VOLUME_AVAILABLE:
        print("⚠️ Volume control: audio backend not available")
        return None
    
    volume_manager = GlobalVolumeManager(scaling, launcher_window)
    
    
    return volume_manager