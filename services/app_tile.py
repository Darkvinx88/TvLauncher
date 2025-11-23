from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsDropShadowEffect

from services.utility import rounded_pixmap


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
