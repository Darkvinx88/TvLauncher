"""
Window Manager Module
Gestisce la minimizzazione/ripristino del launcher quando le app vengono lanciate
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

class WindowManager:
    """Gestisce lo stato della finestra del launcher"""
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.was_minimized = False
        
    def should_minimize(self):
        """Verifica se il launcher deve essere minimizzato al lancio di un'app"""
        # Minimizza SOLO se "Always Fullscreen" è DISABILITATO
        return not self.launcher.config_data.get('fullscreen', True)
    
    def on_app_launch(self):
        """Chiamato quando viene lanciata un'app"""
        if self.should_minimize():
            
            self.was_minimized = True
            self.launcher.showMinimized()
        else:
            
            self.was_minimized = False
    
    def on_app_close(self):
        """Chiamato quando l'app viene chiusa"""
        if self.was_minimized:
            
            
            # Ripristina la finestra in FULLSCREEN (non normal)
            self.launcher.showFullScreen()
            
            # Su alcune piattaforme serve un delay per assicurarsi che torni in primo piano
            QTimer.singleShot(100, self._ensure_foreground)
            
            self.was_minimized = False
    
    def _ensure_foreground(self):
        """Assicura che il launcher torni in primo piano"""
        self.launcher.raise_()
        self.launcher.activateWindow()
        self.launcher.setFocus()