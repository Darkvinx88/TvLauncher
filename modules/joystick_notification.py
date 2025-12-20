from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QScreen, QColor
from PyQt6.QtWidgets import QApplication
from pathlib import Path


class JoystickNotification(QWidget):
    """Notifica toast per connessione/disconnessione joystick con palette uniforme"""
    
    def __init__(self, parent=None, scaling=None):
        super().__init__(parent)
        self.scaling = scaling
        
        # Configurazione finestra
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Dimensioni scalate (rettangolo compatto)
        self.notification_width = self.scaling.scale(240) if scaling else 240
        self.notification_height = self.scaling.scale(73) if scaling else 73
        
        self.setFixedSize(self.notification_width, self.notification_height)
        
        # Setup UI
        self.setup_ui()
        
        # Timer per auto-chiusura
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide_notification)
        
        # Animazioni
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")

  
    def setup_ui(self):
        """Crea l'interfaccia della notifica con palette uniformata"""
        # Layout esterno trasparente
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container con sfondo - PALETTE UNIFORMATA
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border: {self.scaling.scale(2) if self.scaling else 2}px solid #444;
                border-radius: {self.scaling.scale(16) if self.scaling else 16}px;
            }}
        """)
        
        # Layout interno del container
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(
            self.scaling.scale(15) if self.scaling else 15,
            self.scaling.scale(12) if self.scaling else 12,
            self.scaling.scale(15) if self.scaling else 15,
            self.scaling.scale(12) if self.scaling else 12
        )
        layout.setSpacing(self.scaling.scale(12) if self.scaling else 12)
        
        # Icona joystick
        self.icon_label = QLabel()
        icon_size = self.scaling.scale(48) if self.scaling else 48
        self.icon_label.setFixedSize(icon_size, icon_size)
        self.icon_label.setScaledContents(True)
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.icon_label)
        
        # Testo messaggio - COLORI UNIFORMATI E CENTRATO
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(14) if self.scaling else 14}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.message_label, 1)
        
        main_layout.addWidget(self.container)
        
        # Shadow effect uniformato
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(self.scaling.scale(25) if self.scaling else 25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, self.scaling.scale(8) if self.scaling else 8)
        self.container.setGraphicsEffect(shadow)
    
    def show_notification(self, message, is_connected=True):
        """
        Mostra la notifica
        
        Args:
            message: Testo da visualizzare
            is_connected: True per connessione, False per disconnessione
        """
        # Imposta icona
        icon_path = self._get_icon_path(is_connected)
        if icon_path and Path(icon_path).exists():
            pixmap = QPixmap(icon_path)
            self.icon_label.setPixmap(pixmap)
        else:
            # Fallback: emoji Unicode - COLORI UNIFORMATI
            self.icon_label.setText("🎮" if is_connected else "❌")
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {self.scaling.scale_font(32) if self.scaling else 32}px;
                    background: transparent;
                    border: none;
                }}
            """)
        
        # Imposta messaggio
        self.message_label.setText(message)
        
        # Posizionamento usando sempre lo schermo
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            # Margini scalati per adattarsi alla risoluzione
            margin_right = self.scaling.scale(15) if self.scaling else 15
            margin_bottom = self.scaling.scale(94) if self.scaling else 94
            
            x = screen_geometry.width() - self.width() - margin_right
            y = screen_geometry.height() - self.height() - margin_bottom
            
            self.move(x, y)
        elif self.parent():
            # Fallback se primaryScreen non è disponibile
            parent_rect = self.parent().geometry()
            margin = self.scaling.scale(25) if self.scaling else 25
            x = parent_rect.width() - self.notification_width - margin
            y = parent_rect.height() - self.notification_height - margin
            self.move(x, y)
        
        # Animazione fade in
        self.opacity_effect.setOpacity(0.0)
        self.show()
        
        self.fade_animation.stop()
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
        
        # Timer per nascondere dopo 3 secondi
        self.hide_timer.stop()
        self.hide_timer.start(3000)
    
    def hide_notification(self):
        """Nasconde la notifica con fade out"""
        self.fade_animation.stop()
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
    
    def _get_icon_path(self, is_connected):
        """Restituisce il percorso dell'icona appropriata"""
        # Cerca nelle icone di sistema o custom
        base_paths = [
            "assets/icons/",
            "/usr/share/icons/",
            ""
        ]
        
        icon_name = "gamepad-connected.png" if is_connected else "gamepad-disconnected.png"
        
        for base in base_paths:
            icon_path = Path(base) / icon_name
            if icon_path.exists():
                return str(icon_path)
        
        return None


def show_joystick_connected(parent, joystick_name, scaling=None):
    """
    Helper function per mostrare notifica di joystick connesso
    
    Args:
        parent: Widget genitore
        joystick_name: Nome del joystick
        scaling: Oggetto ResponsiveScaling (opzionale)
    """
    parent.last_joystick_name = joystick_name
    notification = JoystickNotification(parent, scaling)
    notification.show_notification(
        f"Controller Connected\n{joystick_name}",
        is_connected=True
    )
    return notification


def show_joystick_disconnected(parent, joystick_name=None, scaling=None):
    """
    Helper function per mostrare notifica di joystick disconnesso
    Compatibile con chiamate legacy
    """

    # Se il nome non è valido, recupera l’ultimo salvato
    if not isinstance(joystick_name, str):
        joystick_name = getattr(parent, "last_joystick_name", "Unknown Controller")

    notification = JoystickNotification(parent, scaling)
    notification.show_notification(
        f"Controller Disconnected\n{joystick_name}",
        is_connected=False
    )
    return notification


