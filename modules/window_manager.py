"""
Window Manager Module - FIXED FOR LINUX
Gestisce la minimizzazione/ripristino del launcher quando le app vengono lanciate
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
import platform

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

class WindowManager:
    """Gestisce lo stato della finestra del launcher"""
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.was_minimized = False
        self.was_fullscreen = False  # ✅ NUOVO: Traccia se era fullscreen
        
    def should_minimize(self):
        """Verifica se il launcher deve essere minimizzato al lancio di un'app"""
        # Minimizza SOLO se "Always Fullscreen" è DISABILITATO
        return not self.launcher.config_data.get('fullscreen', True)
    
    def on_app_launch(self):
        """Chiamato quando viene lanciata un'app"""
        if self.should_minimize():
            print("📽 Minimizing launcher (Always Fullscreen is OFF)")
            
            # ✅ FIX: Salva lo stato fullscreen PRIMA di minimizzare
            self.was_fullscreen = self.launcher.isFullScreen()
            self.was_minimized = True
            
            self.launcher.showMinimized()
        else:
            print("📺 Keeping launcher visible (Always Fullscreen is ON)")
            self.was_minimized = False
            self.was_fullscreen = False
    
    def on_app_close(self):
        """Chiamato quando l'app viene chiusa"""
        if self.was_minimized:
            print(f"📼 Restoring launcher (was_fullscreen: {self.was_fullscreen})")
            
            # ✅ FIX CRITICO: Leggi SEMPRE lo stato fullscreen dalla config
            # Perché self.was_fullscreen potrebbe essere False se "Always Fullscreen" era OFF
            config_fullscreen = self.launcher.config_data.get('fullscreen', True)
            
            print(f"   Config fullscreen: {config_fullscreen}")
            print(f"   Was fullscreen before minimize: {self.was_fullscreen}")
            
            # ✅ Se la config dice fullscreen=True, DEVI tornare fullscreen
            # indipendentemente da come era prima (potrebbe essere stato minimizzato)
            should_be_fullscreen = config_fullscreen or self.was_fullscreen
            
            if IS_LINUX:
                self._restore_window_state_linux(should_be_fullscreen)
            elif IS_WINDOWS:
                self._restore_window_state_windows(should_be_fullscreen)
            else:
                self._restore_generic(should_be_fullscreen)
            
            self.was_minimized = False
            self.was_fullscreen = False

    def _restore_window_state_linux(self, should_be_fullscreen):
        """
        ✅ FIX LINUX: Ripristina correttamente lo stato della finestra
        Risolve il problema del fullscreen che non ritorna
        """
        try:
            print(f"🐧 Linux restore: fullscreen={should_be_fullscreen}")
            
            # Step 1: Ripristina la finestra dalla minimizzazione
            if should_be_fullscreen:
                print("   → showFullScreen()")
                self.launcher.showFullScreen()
            else:
                print("   → showNormal()")
                self.launcher.showNormal()
            
            # Step 2: Forza l'aggiornamento dello stato (immediato)
            QTimer.singleShot(50, lambda: self._ensure_foreground_linux(should_be_fullscreen))
            
            # Step 3: Secondo tentativo se il primo fallisce
            QTimer.singleShot(250, lambda: self._double_check_fullscreen(should_be_fullscreen))
            
            # Step 4: Terzo tentativo (Linux può essere lento)
            QTimer.singleShot(500, lambda: self._triple_check_fullscreen(should_be_fullscreen))
            
        except Exception as e:
            print(f"⚠️ Error restoring window on Linux: {e}")
            # Fallback: forza fullscreen comunque se richiesto
            if should_be_fullscreen:
                self.launcher.showFullScreen()
                self._ensure_foreground_linux(should_be_fullscreen)

    def _double_check_fullscreen(self, should_be_fullscreen):
        """
        ✅ Verifica doppia per assicurarsi che il fullscreen sia attivo
        """
        if should_be_fullscreen and not self.launcher.isFullScreen():
            print("🔄 Forcing fullscreen (double check)")
            self.launcher.showFullScreen()
            self.launcher.raise_()
            self.launcher.activateWindow()
    
    def _triple_check_fullscreen(self, should_be_fullscreen):
        """
        ✅ NUOVO: Terzo controllo per sistemi Linux particolarmente lenti
        """
        if should_be_fullscreen and not self.launcher.isFullScreen():
            print("🔄🔄 Forcing fullscreen (triple check - Linux slow response)")
            self.launcher.showFullScreen()
            self.launcher.raise_()
            self.launcher.activateWindow()
            self.launcher.setFocus()

    def _ensure_foreground_linux(self, should_be_fullscreen):
        """
        ✅ MIGLIORATO: Usa metodi specifici per Linux per portare in primo piano
        """
        try:
            import subprocess
            
            # Ottieni window ID
            window_id = int(self.launcher.winId())
            hex_id = hex(window_id)
            
            print(f"   Window ID: {window_id} ({hex_id})")
            
            # Metodo 1: wmctrl (più affidabile)
            try:
                result = subprocess.run(
                    ['wmctrl', '-ia', hex_id],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    timeout=1,
                    check=False
                )
                print(f"   wmctrl result: {result.returncode}")
            except FileNotFoundError:
                print("   ⚠️ wmctrl not found")
            except Exception as e:
                print(f"   ⚠️ wmctrl error: {e}")
            
            # Metodo 2: xdotool (backup)
            try:
                result = subprocess.run(
                    ['xdotool', 'windowactivate', str(window_id)],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    timeout=1,
                    check=False
                )
                print(f"   xdotool result: {result.returncode}")
            except FileNotFoundError:
                print("   ⚠️ xdotool not found")
            except Exception as e:
                print(f"   ⚠️ xdotool error: {e}")
            
        except Exception as e:
            print(f"⚠️ Error ensuring foreground on Linux: {e}")
        
        # Fallback: metodi Qt
        self.launcher.raise_()
        self.launcher.activateWindow()
        self.launcher.setFocus()

    def _restore_window_state_windows(self, should_be_fullscreen):
        """Ripristina lo stato della finestra su Windows"""
        try:
            import win32gui
            import win32con
            
            hwnd = int(self.launcher.winId())
            
            # Ripristina dalla minimizzazione
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Porta in primo piano
            win32gui.SetForegroundWindow(hwnd)
            
            # Se deve essere fullscreen, ripristinalo
            if should_be_fullscreen:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                
        except ImportError:
            print("⚠️ win32gui not available, using Qt methods")
            self._restore_generic(should_be_fullscreen)
        except Exception as e:
            print(f"⚠️ Error on Windows restore: {e}")
            self._restore_generic(should_be_fullscreen)

    def _restore_generic(self, should_be_fullscreen):
        """Ripristino generico (fallback)"""
        if should_be_fullscreen:
            self.launcher.showFullScreen()
        else:
            self.launcher.showNormal()
        
        QTimer.singleShot(100, self._ensure_foreground_generic)

    def _ensure_foreground_generic(self):
        """Assicura che il launcher torni in primo piano (metodo generico)"""
        self.launcher.raise_()
        self.launcher.activateWindow()
        self.launcher.setFocus()