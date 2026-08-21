import sys
import platform
import subprocess
import pygame
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
    try:
        import alsaaudio
        VOLUME_AVAILABLE = True
    except ImportError:
        print("Warning: pyalsaaudio not installed. Install with: pip install pyalsaaudio")
        VOLUME_AVAILABLE = False
else:
    VOLUME_AVAILABLE = False


class VolumeController:
    """Cross-platform volume control with fallback methods"""
    
    def __init__(self):
        self.volume_interface = None
        self.mixer = None
        self.use_fallback = False
        
        if not VOLUME_AVAILABLE:
            return
            
        if IS_WINDOWS:
            self._init_windows()
        elif IS_LINUX:
            self._init_linux()
    
    def _init_windows(self):
        """Initialize Windows volume control with fallback"""
        if PYCAW_AVAILABLE:
            try:
                try:
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                    print("✓ Windows volume initialized (GetSpeakers)")
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
                    print("✓ Windows volume initialized (CoCreateInstance)")
                    return
                except Exception as e:
                    print(f"⚠️ CoCreateInstance failed: {e}")
                
            except Exception as e:
                print(f"⚠️ pycaw initialization failed: {e}")
        
        print("Using Windows shell command fallback")
        self.use_fallback = True
    
    def _init_linux(self):
        """Initialize Linux volume control"""
        try:
            self.mixer = alsaaudio.Mixer('Master')
            print("✓ Linux volume initialized (Master)")
        except Exception as e:
            print(f"⚠️ Master mixer failed: {e}")
            try:
                self.mixer = alsaaudio.Mixer('PCM')
                print("✓ Linux volume initialized (PCM)")
            except:
                print("❌ Could not initialize any mixer")
    
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
    
    def _get_mute_fallback_windows(self):
        """Get mute state using PowerShell (fallback for Windows)"""
        try:
            cmd = """
            Add-Type -TypeDefinition @"
            using System.Runtime.InteropServices;
            [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
            interface IAudioEndpointVolume {
                int NotImpl1(); int NotImpl2();
                int GetMute(out int pbMute);
            }
            "@
            $DeviceEnumerator = [System.Runtime.InteropServices.Marshal]::GetActiveObject('MMDeviceEnumerator');
            $AudioEndpoint = $DeviceEnumerator.GetDefaultAudioEndpoint(0, 1);
            $Volume = $AudioEndpoint.Activate([Guid]'5CDF2C82-841E-4546-9722-0CF74078229A', 0, [IntPtr]::Zero);
            $mute = 0;
            [void]$Volume.GetMute([ref]$mute);
            $mute
            """
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=2
            )
            return int(result.stdout.strip()) == 1
        except Exception as e:
            print(f"⚠️ Error getting fallback mute: {e}")
            return False
    
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
    
    def _toggle_mute_fallback_windows(self):
        """Toggle mute using PowerShell"""
        try:
            cmd = """
            $obj = New-Object -ComObject WScript.Shell;
            $obj.SendKeys([char]173)
            """
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command", cmd],
                capture_output=True,
                timeout=2
            )
        except Exception as e:
            print(f"⚠️ Fallback mute toggle failed: {e}")
    
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
            elif IS_LINUX and self.mixer:
                volume = self.mixer.getvolume()[0]
                return volume
        except Exception as e:
            print(f"⚠️ Error getting volume: {e}")
        return 50
    
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
            elif IS_LINUX and self.mixer:
                self.mixer.setvolume(level)
        except Exception as e:
            print(f"⚠️ Error setting volume: {e}")
    
    def increase_volume(self, step=5):
        """Increase volume by step"""
        current = self.get_volume()
        self.set_volume(current + step)
        return self.get_volume()
    
    def decrease_volume(self, step=5):
        """Decrease volume by step"""
        current = self.get_volume()
        self.set_volume(current - step)
        return self.get_volume()
    
    def get_mute(self):
        """Get mute state"""
        if not VOLUME_AVAILABLE:
            return False
            
        try:
            if IS_WINDOWS:
                if self.volume_interface and not self.use_fallback:
                    return self.volume_interface.GetMute()
                else:
                    return self._get_mute_fallback_windows()
            elif IS_LINUX and self.mixer:
                return self.mixer.getmute()[0] == 1
        except Exception as e:
            print(f"⚠️ Error getting mute: {e}")
        return False
    
    def toggle_mute(self):
        """Toggle mute"""
        if not VOLUME_AVAILABLE:
            return False
            
        try:
            if IS_WINDOWS:
                if self.volume_interface and not self.use_fallback:
                    current_mute = self.volume_interface.GetMute()
                    self.volume_interface.SetMute(not current_mute, None)
                    return not current_mute
                else:
                    self._toggle_mute_fallback_windows()
                    return not self.get_mute()
            elif IS_LINUX and self.mixer:
                current_mute = self.mixer.getmute()[0]
                self.mixer.setmute(0 if current_mute else 1)
                return not current_mute
        except Exception as e:
            print(f"⚠️ Error toggling mute: {e}")
        return False


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
                    stop:0 #4CAF50,
                    stop:0.5 #8BC34A,
                    stop:1 #CDDC39
                );
                border-radius: {self.scaling.scale(6)}px;
            }}
        """)
    
    def show_volume(self, volume, muted=False):
        """Show overlay with current volume"""
        if muted:
            icon = "🔇"
            text = "Muted"
        elif volume == 0:
            icon = "🔇"
            text = f"{volume}%"
        elif volume < 33:
            icon = "🔈"
            text = f"{volume}%"
        elif volume < 66:
            icon = "🔉"
            text = f"{volume}%"
        else:
            icon = "🔊"
            text = f"{volume}%"
        
        self.label.setText(f"{icon} Volume: {text}")
        self.volume_bar.setValue(volume)
        
        if muted:
             self.volume_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: rgba(50, 50, 50, 200);
                    border: none;
                    border-radius: {self.scaling.scale(6)}px;
                }}
                QProgressBar::chunk {{
                    background-color: #666666;
                    border-radius: {self.scaling.scale(6)}px;
                }}
            """)
        else:
            self.volume_bar.setStyleSheet(f"""
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

        screen = QApplication.primaryScreen().geometry()
        x = screen.width() - self.width() - self.scaling.scale(0)
        y = screen.height() - self.height() - self.scaling.scale(80) 
        
        self.move(x, y)
        self.show()
        self.raise_()
        self.hide_timer.start(2000)


class GlobalVolumeManager(QObject):
   
    
    
    
    
    
    volume_changed = pyqtSignal(int, bool)
    show_overlay = pyqtSignal(int, bool)

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
        Chiamato dal main quando il joystick è pronto
        
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
            print(f"🔊 Volume control: Joystick activated ({joystick.get_name()})")
        else:
            print("🔊 Volume control: Joystick deactivated")

    def _show_overlay(self, volume: int, muted: bool):
        self.overlay.show_volume(volume, muted)

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
                # Reset stato quando si perde focus
                self.volume_mode_active = False
                self.last_volume_buttons = {}

    def _check_controller_input(self):
        """Polling con sistema COMBO: L2/LT + D-Pad"""
        if not self.joystick or not self.launcher_has_focus:
            return

        try:
            name = self.joystick.get_name()
            is_playstation = any(x in name for x in ["Wireless Controller", "DualSense", "PS4", "PS5"])
            
            # CONTROLLO TRIGGER L2/LT
            trigger_pressed = False
            
            try:
                if is_playstation:
                    # PS4/PS5: L2 è axis 4
                    lt_axis = self.joystick.get_axis(4) if self.joystick.get_numaxes() > 4 else -1
                    trigger_pressed = lt_axis > 0.5
                else:
                    # Xbox: LT è axis 4 (o 2 su alcuni controller)
                    lt_axis = self.joystick.get_axis(4) if self.joystick.get_numaxes() > 4 else -1
                    trigger_pressed = lt_axis > 0.3
            except:
                return

            if not trigger_pressed:
                self.volume_mode_active = False
                self.last_volume_buttons = {}
                return

            self.volume_mode_active = True

            # Lettura D-Pad
            dpad_up = dpad_down = dpad_left = dpad_right = False
            
            try:
                if is_playstation:
                    # PS4/PS5: D-Pad su buttons
                    if self.joystick.get_numbuttons() > 12:
                        dpad_up = self.joystick.get_button(11)    # D-Pad Up
                        dpad_down = self.joystick.get_button(12)  # D-Pad Down
                        if self.joystick.get_numbuttons() > 14:
                            dpad_left = self.joystick.get_button(13)   # D-Pad Left
                            dpad_right = self.joystick.get_button(14)  # D-Pad Right
                else:
                    # Xbox: D-Pad su hat
                    if self.joystick.get_numhats() > 0:
                        hat = self.joystick.get_hat(0)
                        dpad_up = hat[1] == 1
                        dpad_down = hat[1] == -1
                        dpad_left = hat[0] == -1
                        dpad_right = hat[0] == 1
            except:
                return

            # Mute/Unmute con L2 + D-Pad Left/Right
            if dpad_left and not self.last_volume_buttons.get('mute_toggle', False):
                self.toggle_mute()
                self.last_volume_buttons['mute_toggle'] = True
            elif dpad_right and not self.last_volume_buttons.get('mute_toggle', False):
                if self.controller.get_mute():
                    self.toggle_mute()
                self.last_volume_buttons['mute_toggle'] = True
            elif not (dpad_left or dpad_right):
                self.last_volume_buttons['mute_toggle'] = False

            # Volume su/giù
            if dpad_up and not self.last_volume_buttons.get('up', False):
                self.increase_volume()
                self.last_volume_buttons['up'] = True
            elif dpad_down and not self.last_volume_buttons.get('down', False):
                self.decrease_volume()
                self.last_volume_buttons['down'] = True
            elif not (dpad_up or dpad_down):
                self.last_volume_buttons['up'] = False
                self.last_volume_buttons['down'] = False

        except:
            pass  # Errore silenzioso

    def increase_volume(self):
        try:
            volume = self.controller.increase_volume(5)
            muted = self.controller.get_mute()
            self.show_overlay.emit(volume, muted)
            self.volume_changed.emit(volume, muted)
        except Exception as e:
            print(f"Error increasing volume: {e}")

    def decrease_volume(self):
        try:
            volume = self.controller.decrease_volume(5)
            muted = self.controller.get_mute()
            self.show_overlay.emit(volume, muted)
            self.volume_changed.emit(volume, muted)
        except Exception as e:
            print(f"Error decreasing volume: {e}")

    def toggle_mute(self):
        try:
            muted = self.controller.toggle_mute()
            volume = self.controller.get_volume()
            self.show_overlay.emit(volume, muted)
            self.volume_changed.emit(volume, muted)
        except Exception as e:
            print(f"Error toggling mute: {e}")

    def cleanup(self):
        """Cleanup quando l'app si chiude"""
        if self.focus_check_timer:
            self.focus_check_timer.stop()
        if self.controller_timer:
            self.controller_timer.stop()
        self.overlay.hide()
        



def install_volume_control(scaling, launcher_window):
    """
    Installa il controllo volume globale (modalità passiva)
    
    Args:
        scaling: Oggetto ResponsiveScaling per UI
        launcher_window: TVLauncher instance
    
    Returns:
        GlobalVolumeManager instance
    
    Usage nel main:
        from modules.volume_overlayPAD import install_volume_control
        
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