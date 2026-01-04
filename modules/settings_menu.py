from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QCheckBox, QDialog,
    QLineEdit, QFileDialog, QMessageBox,QRadioButton,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal, QTimer, QRectF, pyqtProperty,  QSize
from PyQt6.QtGui import QIcon, QPainter, QColor, QPen,  QPixmap
from pathlib import Path
import json
from modules.key_remapper import KeyRemapperDialog

class ResetDialog(QDialog):
    """Dialog per scegliere tipo di reset (Soft/Full)"""
    
    def __init__(self, launcher, scaling, parent=None):
        super().__init__(parent)
        self.launcher = launcher
        self.scaling = scaling
        self.selected_type = "soft"  # Default sicuro
        
        self.setWindowTitle("Choose Reset Type")
        self.setModal(True)
        self.setFixedSize(self.scaling.scale(550), self.scaling.scale(500))
        
        # Stile base del dialog
        self.setStyleSheet("""
            QDialog { 
                background-color: #1a1a1a; 
            }
        """)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(self.scaling.scale(20))
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30)
        )
        
        # === CREA IL BUTTON GROUP ===
        self.button_group = QButtonGroup(self)
        
        # Titolo
        title = QLabel("🔄 Reset Configuration")
        title.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(20)}px; 
                font-weight: bold;
                color: white;
                background: transparent;
                border: none;
            }}
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Sottotitolo
        subtitle = QLabel("Choose what you want to reset:")
        subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(13)}px;
                color: #aaa;
                background: transparent;
                border: none;
            }}
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(self.scaling.scale(20))
        
        # === OPZIONE 1: SOFT RESET ===
        soft_container = self._create_option_container(
            "Soft Reset",
            "Reset only settings to default",
            [
                "✅ Apps PRESERVED",
                "✅ Background PRESERVED", 
                "✅ API Key PRESERVED",
                "🔄 Settings reset to default"
            ],
            "soft"
        )
        layout.addWidget(soft_container)
        
        # Aggiungi al gruppo
        self.button_group.addButton(soft_container.radio)
        
        # === OPZIONE 2: FULL RESET ===
        full_container = self._create_option_container(
            "Full Reset",
            "Delete EVERYTHING (factory reset)",
            [
                "❌ ALL apps DELETED",
                "❌ Background REMOVED",
                "❌ API Key DELETED",
                "❌ All data lost forever"
            ],
            "full"
        )
        layout.addWidget(full_container)
        
        # Aggiungi al gruppo
        self.button_group.addButton(full_container.radio)
        
        layout.addStretch()
        
        # Conteggio app corrente
        apps_count = len(self.launcher.apps) if self.launcher else 0
        info = QLabel(f"💡 Current apps: {apps_count}")
        info.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(12)}px;
                color: #888;
                padding: {self.scaling.scale(10)}px;
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(6)}px;
                border: none;
            }}
        """)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # Pulsanti conferma/annulla
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scaling.scale(15))
        
        self.ok_button = QPushButton("Continue")
        self.ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px; 
                border-radius: {self.scaling.scale(8)}px; 
                font-size: {self.scaling.scale_font(14)}px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px; 
                border-radius: {self.scaling.scale(8)}px; 
                font-size: {self.scaling.scale_font(14)}px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Navigazione con tastiera
        self.confirm_buttons = [self.ok_button, self.cancel_button]
        self.confirm_index = [0]
        self.update_confirm_focus()
    
    def _create_option_container(self, title, description, details, option_type):
        """Crea un container per un'opzione di reset"""
        container = QWidget()
        container.setObjectName("resetContainer")  # Per identificarlo
        
        # Sfondo e bordo distintivi
        bg_color = "#2a2a2a" if option_type == "soft" else "#3a2020"
        border_color = "#4a9eff" if option_type == "soft" else "#ff4a4a"
        
        container.setStyleSheet(f"""
            QWidget#resetContainer {{
                background-color: {bg_color};
                border: 3px solid {border_color};
                border-radius: {self.scaling.scale(10)}px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QRadioButton {{
                background: transparent;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(container)
        layout.setSpacing(self.scaling.scale(10))
        layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        # Radio button + Titolo
        radio = QRadioButton(title)
        radio.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # ← DISABILITA FOCUS RETTANGOLO
        radio.setStyleSheet(f"""
            QRadioButton {{
                font-size: {self.scaling.scale_font(16)}px;
                font-weight: bold;
                color: white;
                spacing: {self.scaling.scale(10)}px;
                background: transparent;
                border: none;
                outline: none;
            }}
            QRadioButton::indicator {{
                width: {self.scaling.scale(20)}px;
                height: {self.scaling.scale(20)}px;
                border: 2px solid #666;
                border-radius: {self.scaling.scale(10)}px;
                background-color: #1a1a1a;
            }}
            QRadioButton::indicator:checked {{
                background-color: {border_color};
                border-color: {border_color};
            }}
            QRadioButton::indicator:hover {{
                border-color: {border_color};
            }}
        """)
        
        if option_type == "soft":
            radio.setChecked(True)
        
        radio.toggled.connect(lambda checked: self._on_radio_toggled(option_type, checked))
        layout.addWidget(radio)
        
        # Descrizione
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(13)}px;
                color: #cccccc;
                font-weight: 500;
                padding-left: {self.scaling.scale(30)}px;
                background: transparent;
                border: none;
            }}
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Spacer
        layout.addSpacing(self.scaling.scale(5))
        
        # Dettagli
        for detail in details:
            detail_label = QLabel(detail)
            detail_label.setStyleSheet(f"""
                QLabel {{
                    font-size: {self.scaling.scale_font(12)}px;
                    color: #aaaaaa;
                    padding-left: {self.scaling.scale(30)}px;
                    background: transparent;
                    border: none;
                }}
            """)
            detail_label.setWordWrap(True)
            layout.addWidget(detail_label)
        
        # Salva riferimento
        container.radio = radio
        
        return container
    
    def _on_radio_toggled(self, option_type, checked):
        """Aggiorna selezione quando si clicca un radio button"""
        if checked:
            self.selected_type = option_type
    
    def get_reset_type(self):
        """Ritorna il tipo di reset selezionato"""
        return self.selected_type
    
    def update_confirm_focus(self):
        """Gestisce focus sui pulsanti"""
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2a2a2a;
                        color: white;
                        border: 3px solid white;
                        padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px;
                        border-radius: {self.scaling.scale(8)}px;
                        font-size: {self.scaling.scale_font(14)}px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a; }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px;
                        border-radius: {self.scaling.scale(8)}px;
                        font-size: {self.scaling.scale_font(14)}px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{ background-color: #3a3a3a; }}
                """)
    
    def keyPressEvent(self, event):
        """Gestisce navigazione con tastiera/joypad"""
        if event.isAutoRepeat():
            return
        
        key = event.key()
        
        if key == Qt.Key.Key_Left:
            self.confirm_index[0] = (self.confirm_index[0] - 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Right:
            self.confirm_index[0] = (self.confirm_index[0] + 1) % 2
            self.update_confirm_focus()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.confirm_buttons[self.confirm_index[0]].click()
        elif key == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

class AnimatedToggle(QWidget):
    """Toggle switch animato con indicatore scorrevole"""
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self._checked = False
        self._circle_position = self.scaling.scale(4)
        
        width = self.scaling.scale(60)
        height = self.scaling.scale(32)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animazione per lo spostamento del cerchio
        self.animation = QPropertyAnimation(self, b"circle_position")
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.setDuration(250)
        
    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position
    
    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()
    
    def isChecked(self):
        return self._checked
    
    def setChecked(self, checked):
        if self._checked == checked:
            return
        
        self._checked = checked
        
        # Anima il movimento del cerchio
        start_x = self.scaling.scale(4) if not checked else self.scaling.scale(32)
        end_x = self.scaling.scale(32) if checked else self.scaling.scale(4)
        
        self.animation.setStartValue(start_x)
        self.animation.setEndValue(end_x)
        self.animation.start()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background track
        track_rect = QRectF(0, 0, self.width(), self.height())
        
        if self._checked:
            painter.setBrush(QColor(76, 175, 80))  # Verde quando attivo
        else:
            painter.setBrush(QColor(58, 58, 58))  # Grigio quando inattivo
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, self.scaling.scale(16), self.scaling.scale(16))
        
        # Cerchio scorrevole
        circle_y = self.scaling.scale(4)
        circle_diameter = self.scaling.scale(24)
        
        # Ombra del cerchio
        shadow_rect = QRectF(
            self._circle_position + self.scaling.scale(2), 
            circle_y + self.scaling.scale(2), 
            circle_diameter, 
            circle_diameter
        )
        painter.setBrush(QColor(0, 0, 0, 60))
        painter.drawEllipse(shadow_rect)
        
        # Cerchio bianco
        circle_rect = QRectF(
            self._circle_position, 
            circle_y, 
            circle_diameter, 
            circle_diameter
        )
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(circle_rect)
        
        # Testo ON/OFF
        painter.setPen(QColor(255, 255, 255, 200))
        font = painter.font()
        font.setPixelSize(self.scaling.scale_font(10))
        font.setBold(True)
        painter.setFont(font)
        
        if self._checked:
            painter.drawText(QRectF(self.scaling.scale(8), 0, self.scaling.scale(20), self.height()), 
                           Qt.AlignmentFlag.AlignCenter, "ON")
        else:
            painter.drawText(QRectF(self.width() - self.scaling.scale(28), 0, self.scaling.scale(24), self.height()), 
                           Qt.AlignmentFlag.AlignCenter, "OFF")
    
    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        super().mousePressEvent(event)

class SettingsMenu(QWidget):
    """Menu laterale con stile coerente al launcher"""
    
    menu_closed = pyqtSignal()
    config_changed = pyqtSignal(dict)
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self.is_open = False
        self.current_index = 0
        self.menu_items = []
        self.launcher = None
        
        self.config = {
            'show_clock': True,
            'sound_effects': False,
            'fullscreen': True,
        }
        
        self.init_ui()
        self.hide()
        
    def init_ui(self):
        """Inizializza UI con stile coerente"""
        self.setFixedWidth(self.scaling.scale(420))
        
        # Stile principale coerente con program_scanner
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-left: 2px solid #444;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # HEADER
        header = self._create_header()
        main_layout.addWidget(header)
        
        # SCROLLABLE CONTENT
        scroll = self._create_scroll_area()
        content = self._create_content()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # FOOTER
        footer = self._create_footer()
        main_layout.addWidget(footer)
        
        self.update_focus()
        
    def _create_header(self):
        """Header con stile coerente"""
        header = QWidget()
        header.setFixedHeight(self.scaling.scale(100))
        header.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border-bottom: 2px solid #444;
                border-left: none;
            }
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(20), 
            self.scaling.scale(30), 
            self.scaling.scale(20)
        )
        
        title = QLabel("⚙️ Settings")
        title.setStyleSheet(f"""
            color: white;
            font-size: {self.scaling.scale_font(24)}px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title)
        layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(self.scaling.scale(40), self.scaling.scale(40))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(20)}px;
                font-size: {self.scaling.scale_font(18)}px;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        close_btn.clicked.connect(self.close_menu)
        layout.addWidget(close_btn)
        
        return header
        
    def _create_scroll_area(self):
        """Scroll area con stile coerente"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 10px;
                border-radius: 5px;
                border: 1px solid #444;
            }
            QScrollBar::handle:vertical {
                background-color: #444;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        return scroll
        
    def _create_content(self):
        """Contenuto con stile coerente"""
        if self.menu_items:
             self.menu_items.clear()
        
        content = QWidget()
        content.setStyleSheet("QWidget { border: none; background-color: #1a1a1a; }")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            self.scaling.scale(20), 
            self.scaling.scale(20), 
            self.scaling.scale(20), 
            self.scaling.scale(20)
        )
        layout.setSpacing(self.scaling.scale(15))
        
        # === ACTIONS SECTION ===
        self._add_section_title(layout, "🎮 Quick Actions")
        
        icon_dir = Path("assets/icons")
        
        actions = [
            ("API Key", "Set SteamGridDB key", self._handle_api_key, icon_dir / "key.png"),
            ("Scan Programs", "Find installed apps", self._handle_scan, icon_dir / "search.png"),
            ("Add App", "Manually add an app", self._handle_add_app, icon_dir / "plus.png"),
            ("Download Covers", "Get images for existing apps", self._handle_download_covers, icon_dir / "download.png"),
            ("Set Background", "Choose wallpaper", self._handle_background, icon_dir / "image.png"),
        ]
        
        for title, desc, callback, icon_path in actions:
            btn = self._create_menu_button(title, desc, callback, str(icon_path))
            layout.addWidget(btn)
            self.menu_items.append(btn)
        
        # === APPEARANCE SECTION ===
        layout.addSpacing(self.scaling.scale(20))
        self._add_section_title(layout, "🎨 Appearance")
        
        self.clock_toggle = self._create_toggle(
            "Show Clock",
            "Display time and date in header",
            self.config['show_clock'],
            lambda val: self._handle_toggle('show_clock', val)
        )
        layout.addWidget(self.clock_toggle)
        self.menu_items.append(self.clock_toggle)
        
        # === BEHAVIOR SECTION ===
        layout.addSpacing(self.scaling.scale(20))
        self._add_section_title(layout, "⚡ Behavior")
        
        self.sound_toggle = self._create_toggle(
            "Sound Effects",
            "Play sounds on navigation",
            self.config['sound_effects'],
            lambda val: self._handle_toggle('sound_effects', val)
        )
        layout.addWidget(self.sound_toggle)
        self.menu_items.append(self.sound_toggle)
        
        self.fullscreen_toggle = self._create_toggle(
            "Always Fullscreen",
            "Fullscreen or minimize while launching apps",
            self.config['fullscreen'],
            lambda val: self._handle_toggle('fullscreen', val)
        )
        layout.addWidget(self.fullscreen_toggle)
        self.menu_items.append(self.fullscreen_toggle)
        
        # === ADVANCED SECTION ===
        layout.addSpacing(self.scaling.scale(20))
        self._add_section_title(layout, "🔧 Advanced")

        # 🎮 NUOVO: Key Remapper Button
        keyremap_btn = self._create_menu_button(
            "🎮 Key Remapper",
            "Customize keyboard/remote buttons",
            self._handle_key_remapper,
        )
        layout.addWidget(keyremap_btn)
        self.menu_items.append(keyremap_btn)
        
        backup_btn = self._create_menu_button(
            "💾 Backup Config",
            "Export your configuration",
            self._handle_backup
        )
        layout.addWidget(backup_btn)
        self.menu_items.append(backup_btn)
        
        restore_btn = self._create_menu_button(
            "📥 Restore Config",
            "Import configuration",
            self._handle_restore
        )
        layout.addWidget(restore_btn)
        self.menu_items.append(restore_btn)
        
        reset_btn = self._create_menu_button(
            "🔄 Reset Settings",
            "Restore default settings",
            self._handle_reset
        )
        layout.addWidget(reset_btn)
        self.menu_items.append(reset_btn)
        
        # === INFO SECTION ===
        layout.addSpacing(self.scaling.scale(20))
        self._add_section_title(layout, "ℹ️ Information")
        
        info_widget = self._create_info_widget()
        layout.addWidget(info_widget)

        if hasattr(info_widget, 'update_btn'):
            self.menu_items.append(info_widget.update_btn)
        
        layout.addStretch()
        
        return content
        
    def _create_footer(self):
        """Footer con stile coerente"""
        footer = QWidget()
        footer.setFixedHeight(self.scaling.scale(60))
        footer.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border-top: 2px solid #444;
                border-left: none;
            }
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(15), 
            self.scaling.scale(30), 
            self.scaling.scale(15)
        )
        
        hint = QLabel("Navigate: ↑↓ | Select: Enter/A | Close: Esc/B/Start")
        hint.setStyleSheet(f"""
            color: #aaa;
            font-size: {self.scaling.scale_font(11)}px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(hint)
        
        return footer
        
    def _add_section_title(self, layout, text):
        """Titolo sezione con stile coerente"""
        title = QLabel(text)
        title.setStyleSheet(f"""
            color: #888;
            font-size: {self.scaling.scale_font(14)}px;
            font-weight: bold;
            padding: {self.scaling.scale(10)}px 0px {self.scaling.scale(5)}px 0px;
        """)
        layout.addWidget(title)
        
    def _create_menu_button(self, title, description, callback, icon_path=None):
        """Pulsante menu con supporto icone"""
        btn = QPushButton()
        btn.setFixedHeight(self.scaling.scale(70))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(
            self.scaling.scale(15), 
            self.scaling.scale(10), 
            self.scaling.scale(15), 
            self.scaling.scale(10)
        )
        btn_layout.setSpacing(self.scaling.scale(12))
        
        # === ICONA (se fornita) ===
        if icon_path and Path(icon_path).exists():
            icon_label = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.scaling.scale(40), 
                    self.scaling.scale(40), 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                icon_label.setPixmap(scaled_pixmap)
                icon_label.setFixedSize(self.scaling.scale(40), self.scaling.scale(40))
                icon_label.setStyleSheet("background: transparent; border: none;")
                btn_layout.addWidget(icon_label)
        
        # === TESTO ===
        text_layout = QVBoxLayout()
        text_layout.setSpacing(self.scaling.scale(5))
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(14)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: #aaa;
                font-size: {self.scaling.scale_font(12)}px;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(desc_label)
        
        btn_layout.addLayout(text_layout)
        btn_layout.addStretch()
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(8)}px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        
        btn.clicked.connect(callback)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        return btn
        
    def _create_toggle(self, title, description, default_value, callback):
        """Toggle migliorato con animazione scorrevole"""
        container = QWidget()
        container.setFixedHeight(self.scaling.scale(70))
        
        container.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(8)}px;
            }}
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(
            self.scaling.scale(15), 
            self.scaling.scale(10), 
            self.scaling.scale(15), 
            self.scaling.scale(10)
        )
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(self.scaling.scale(5))
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(14)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: #aaa;
                font-size: {self.scaling.scale_font(12)}px;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # Usa il nuovo toggle animato
        toggle = AnimatedToggle(self.scaling)
        toggle.setChecked(default_value)
        
        # Wrapper per il callback
        def on_toggle_changed(event):
            toggle.setChecked(not toggle.isChecked())
            callback(toggle.isChecked())
            super(AnimatedToggle, toggle).mousePressEvent(event)
        
        toggle.mousePressEvent = on_toggle_changed
        
        layout.addWidget(toggle)
        
        container.checkbox = toggle  # Per compatibilità con codice esistente
        return container
        
    def _create_info_widget(self):
        """Widget info con stile coerente"""
        info_widget = QWidget()
        info_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(8)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(self.scaling.scale(8))

        # Pulsante Check for Updates con icona GitHub
        update_btn = QPushButton("  Check for Updates")
        update_btn.setFixedHeight(self.scaling.scale(50))
        update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Carica l'icona GitHub
        icon_path = Path("assets/icons/github.png")
        if icon_path.exists():
            icon = QIcon(str(icon_path))
            update_btn.setIcon(icon)
            update_btn.setIconSize(QSize(self.scaling.scale(20), self.scaling.scale(20)))
        
        update_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3a3a3a;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(6)}px;
                color: white;
                font-size: {self.scaling.scale_font(13)}px;
                font-weight: bold;
                text-align: left;
                padding-left: {self.scaling.scale(12)}px;
                padding-right: {self.scaling.scale(12)}px;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
                border-color: #666;
            }}
        """)
        
        update_btn.clicked.connect(self._open_github)
        update_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        info_layout.addWidget(update_btn)
        
        version_label = QLabel("Version: 0.5")
        version_label.setStyleSheet(f"color: white; font-size: {self.scaling.scale_font(13)}px;")
        info_layout.addWidget(version_label)
  
        author_label = QLabel("Made with ❤️ by Darkvinx88")
        author_label.setStyleSheet(f"color: #aaa; font-size: {self.scaling.scale_font(12)}px;")
        info_layout.addWidget(author_label)
        
        self.apps_count_label = QLabel("Apps: Loading...")
        self.apps_count_label.setStyleSheet(f"color: #888; font-size: {self.scaling.scale_font(11)}px;")
        info_layout.addWidget(self.apps_count_label)
        info_widget.update_btn = update_btn
        return info_widget
        
    # ===== HANDLERS =====
    
    def _handle_api_key(self):
        if not self.launcher:
            return
        self.close_menu()
        QTimer.singleShot(350, self.launcher.set_api_key)
        
    def _handle_scan(self):
        if not self.launcher:
            return
        self.close_menu()
        QTimer.singleShot(350, self.launcher.scan_programs)
        
    def _handle_add_app(self):
        if not self.launcher:
            return
        self.close_menu()
        QTimer.singleShot(350, self.launcher.add_app)
        
    def _handle_download_covers(self):
        if not self.launcher:
            return
        self.close_menu()
        QTimer.singleShot(350, self.launcher.download_covers_for_existing_apps)
        
    def _handle_background(self):
        if not self.launcher:
            return
        self.close_menu()
        QTimer.singleShot(350, self.launcher.set_background)

    def _open_github(self):
        """Apre la pagina GitHub del progetto"""
        import webbrowser
        github_url = "https://github.com/Darkvinx88/TvLauncher"
        
        try:
            webbrowser.open(github_url)
            print(f"🌐 Opening GitHub: {github_url}")
        except Exception as e:
            print(f"❌ Error opening browser: {e}")
            QMessageBox.warning(
                self,
                "Cannot Open Browser",
                f"Please visit manually:\n{github_url}"
            )    
        
    def _handle_toggle(self, key, value):
        self.config[key] = value
        
        if self.launcher:
            self.launcher.config_data[key] = value
            self.launcher.save_config()
            
            if key == 'show_clock':
                self.launcher.toggle_clock_visibility(value)
            elif key == 'sound_effects':
                self.launcher.sound_manager.set_enabled(value)
                # Suono di conferma se attivato
                if value:
                    self.launcher.sound_manager.select()    
    def _handle_backup(self):
        """Esporta TUTTA la configurazione in un file JSON"""
        if not self.launcher:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration",
            str(Path.home() / "launcher_backup.json"),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Get key mappings from the mapper
                key_mappings_data = None
                key_mappings_file = Path("key_mappings.json")
                if key_mappings_file.exists():
                    with open(key_mappings_file, 'r') as f:
                        key_mappings_data = json.load(f)
                
                # Salva TUTTO dal launcher
                complete_config = {
                    'apps': self.launcher.apps,
                    'background': self.launcher.background_image,
                    'steamgriddb_api_key': self.launcher.steamgriddb_api_key,
                    'show_clock': self.launcher.config_data.get('show_clock', True),
                    'sound_effects': self.launcher.config_data.get('sound_effects', False),
                    'fullscreen': self.launcher.config_data.get('fullscreen', True),
                    'key_mappings': key_mappings_data,  # ← NEW: Include key mappings
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(complete_config, f, indent=2, ensure_ascii=False)
                
                # Usa il nuovo dialog stilizzato
                self._show_success_dialog(
                    "✅ Export Complete",
                    f"Configuration exported successfully!\n\n"
                    f"📦 Exported:\n"
                    f"  • {len(complete_config['apps'])} apps\n"
                    f"  • Background image\n"
                    f"  • API Key\n"
                    f"  • Key mappings\n"  # ← NEW: Mention key mappings
                    f"  • All settings"
                )
                
            except Exception as e:
                self._show_error_dialog("Export Failed", f"Failed to export configuration:\n\n{str(e)}")
                
    def _handle_restore(self):
        """Ripristina TUTTA la configurazione da un file JSON"""
        if not self.launcher:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Configuration",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # Mostra cosa verrà importato usando il nuovo dialog
            apps_count = len(imported_config.get('apps', []))
            has_background = bool(imported_config.get('background'))
            has_api_key = bool(imported_config.get('steamgriddb_api_key'))
            has_key_mappings = bool(imported_config.get('key_mappings'))  # ← NEW
            
            # Usa il nuovo dialog di conferma stilizzato
            if self._show_confirm_dialog(
                "⚠️ Confirm Restore",
                f"This will REPLACE your current configuration:\n\n"
                f"📦 Will import:\n"
                f"  • {apps_count} apps\n"
                f"  • Background: {'Yes' if has_background else 'No'}\n"
                f"  • API Key: {'Yes' if has_api_key else 'No'}\n"
                f"  • Key Mappings: {'Yes' if has_key_mappings else 'No'}\n"  # ← NEW
                f"  • All settings\n\n"
                f"⚠️ Current data will be OVERWRITTEN!\n\n"
                f"Continue?"
            ):
                # Ripristina TUTTO
                self.launcher.apps = imported_config.get('apps', [])
                self.launcher.background_image = imported_config.get('background', '')
                self.launcher.steamgriddb_api_key = imported_config.get('steamgriddb_api_key', '')
                
                # ← NEW: Restore key mappings
                if imported_config.get('key_mappings'):
                    key_mappings_file = Path("key_mappings.json")
                    with open(key_mappings_file, 'w') as f:
                        json.dump(imported_config['key_mappings'], f, indent=2)
                    # Reload mappings
                    if hasattr(self.launcher, 'key_mapper'):
                        self.launcher.key_mapper.load_mappings()
                
                # Aggiorna config_data
                self.launcher.config_data = {
                    'apps': self.launcher.apps,
                    'background': self.launcher.background_image,
                    'steamgriddb_api_key': self.launcher.steamgriddb_api_key,
                    'show_clock': imported_config.get('show_clock', True),
                    'sound_effects': imported_config.get('sound_effects', False),
                    'fullscreen': imported_config.get('fullscreen', True),
                }
                
                # Salva su disco
                self.launcher.save_config()
                
                # Ricostruisci UI
                self.launcher.build_infinite_carousel()
                self.launcher.update_background()
                
                # Aggiorna ImageManager con nuova API key
                self.launcher.image_manager.api_key = self.launcher.steamgriddb_api_key
                
                # Sincronizza toggle nel menu settings
                self._sync_toggles_from_config(self.launcher.config_data)
                
                # Aggiorna conteggio app
                if hasattr(self, 'apps_count_label'):
                    self.apps_count_label.setText(f"Apps: {len(self.launcher.apps)}")
                
                self._show_success_dialog(
                    "✅ Restore Complete",
                    f"Configuration restored successfully!\n\n"
                    f"📦 Imported {apps_count} apps"
                    + ("\n🎮 Key mappings restored" if has_key_mappings else "")  # ← NEW
                )
                
        except json.JSONDecodeError:
            self._show_error_dialog(
                "Invalid File",
                "Invalid JSON file!\n\nPlease select a valid backup file."
            )
        except Exception as e:
            self._show_error_dialog("Restore Failed", f"Failed to import configuration:\n\n{str(e)}")
                
    def _handle_reset(self):
        """Mostra dialog per scegliere tipo di reset"""
        dialog = ResetDialog(self.launcher, self.scaling, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            reset_type = dialog.get_reset_type()
            
            if reset_type == "soft":
                self._do_soft_reset()
            elif reset_type == "full":
                self._do_full_reset()

    def _do_soft_reset(self):
        """Reset solo impostazioni (mantiene apps, background, API key)"""
        if self._show_confirm_dialog(
            "🔄 Soft Reset",
            "This will reset only preferences:\n\n"
            "✅ Your apps will be PRESERVED\n"
            "✅ Background will be PRESERVED\n"
            "✅ API Key will be PRESERVED\n\n"
            "  Settings reset to:\n"
            "  • Show Clock → ON\n"
            "  • Sound Effects → OFF\n"
            "  • Fullscreen → ON\n\n"
            "Continue?"
        ):
            # Mantiene apps, background, API key
            default_settings = {
                'show_clock': True,
                'sound_effects': False,
                'fullscreen': True,
                
            }
            
            # Aggiorna solo i settings, non tocca apps/background/api
            self.launcher.config_data.update(default_settings)
            
            # Salva
            self.launcher.save_config()
            
            # Sincronizza toggle
            self._sync_toggles_from_config(default_settings)
            
            # Applica visivamente
            self.launcher.toggle_clock_visibility(True)
            
            self._show_success_dialog(
                "✅ Soft Reset Complete",
                f"Settings reset to default!\n\n"
                f"✅ Your {len(self.launcher.apps)} apps are safe\n"
                f"✅ Background preserved\n"
                f"✅ API Key preserved"
            )

    def _do_full_reset(self):
        """Reset COMPLETO: cancella tutto"""
        # Prima conferma
        if not self._show_confirm_dialog(
            "⚠️ Full Reset",
            "DANGER: This will DELETE EVERYTHING:\n\n"
            "❌ ALL apps will be REMOVED\n"
            "❌ Background will be CLEARED\n"
            "❌ API Key will be DELETED\n"
            "❌ All settings reset to default\n\n"
            "⚠️ This action CANNOT be undone!\n\n"
            "💡 TIP: Export a backup first!\n\n"
            "Continue?"
        ):
            return
        
        # Seconda conferma per sicurezza
        if not self._show_confirm_dialog(
            "⚠️ Final Confirmation",
            "Are you ABSOLUTELY SURE?\n\n"
            "🔴 All your data will be permanently deleted!\n\n"
            f"You will lose {len(self.launcher.apps)} app(s)."
        ):
            return
        
        # Reset COMPLETO
        default_config = {
            'apps': [],
            'background': '',
            'steamgriddb_api_key': '',
            'show_clock': True,
            'sound_effects': False,
            'fullscreen': True,
            
        }
        key_mappings_file = Path("key_mappings.json")
        if key_mappings_file.exists():
            key_mappings_file.unlink()  # Delete the file
    
    # Reload default mappings
        if hasattr(self.launcher, 'key_mapper'):
            self.launcher.key_mapper.load_mappings()
        
        # Applica al launcher
        self.launcher.apps = []
        self.launcher.background_image = ''
        self.launcher.steamgriddb_api_key = ''
        self.launcher.config_data = default_config
        
        # Salva su disco
        self.launcher.save_config()
        
        # Ricostruisci UI
        self.launcher.build_infinite_carousel()
        self.launcher.update_background()
        
        # Aggiorna ImageManager
        self.launcher.image_manager.api_key = ''
        
        # Sincronizza toggle
        self._sync_toggles_from_config(default_config)
        
        # Aggiorna conteggio app
        if hasattr(self, 'apps_count_label'):
            self.apps_count_label.setText("Apps: 0")
        
        self._show_success_dialog(
            "✅ Full Reset Complete",
            "All data has been deleted.\n\n"
            "The launcher is now in its default state."
        )

    def _handle_key_remapper(self):
            """Apre il dialog per rimappare i tasti"""
            if not self.launcher:
                return
            
            # Chiudi il settings menu
            self.close_menu()
            
            # Apri il key remapper dopo un piccolo delay
            QTimer.singleShot(350, lambda: self._open_key_remapper_dialog())

    def _open_key_remapper_dialog(self):
        """Apre effettivamente il dialog del key remapper"""
        try:
            dialog = KeyRemapperDialog(self.launcher, self.scaling, self.launcher)
            
            # Quando il dialog si chiude, riapplica i nuovi mapping
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Ricarica i mapping nel launcher
                if hasattr(self.launcher, 'key_mapper'):
                    self.launcher.key_mapper.load_mappings()
                    
                    # Notifica l'utente
                    self._show_success_dialog(
                        "✅ Mappings Saved",
                        "Key mappings updated successfully!\n\n"
                        "Your new controls are now active."
                    )
        
        except Exception as e:
            print(f"❌ Error opening key remapper: {e}")
            self._show_error_dialog(
                "Error",
                f"Failed to open key remapper:\n\n{str(e)}"
            )
        
        # Riattiva input e focus
        self.launcher.setFocus()
        self.launcher.activateWindow()

        
    # ===== PUBLIC METHODS =====

    def _sync_toggles_from_config(self, config):
        """Sincronizza i toggle con i valori della config"""
        if hasattr(self, 'clock_toggle') and hasattr(self.clock_toggle, 'checkbox'):
            self.clock_toggle.checkbox.setChecked(config.get('show_clock', True))
        
        if hasattr(self, 'sound_toggle') and hasattr(self.sound_toggle, 'checkbox'):
            self.sound_toggle.checkbox.setChecked(config.get('sound_effects', False))
        
        if hasattr(self, 'fullscreen_toggle') and hasattr(self.fullscreen_toggle, 'checkbox'):
            self.fullscreen_toggle.checkbox.setChecked(config.get('fullscreen', True))
            
    def open_menu(self, launcher):
        """Apre menu SENZA ricreare content"""
        if self.is_open:
            return
            
        self.launcher = launcher
        self.is_open = True
        
        # Sincronizza config
        if hasattr(launcher, 'config_data'):
            for key in self.config:
                if key in launcher.config_data:
                    self.config[key] = launcher.config_data[key]
            self._sync_toggles_from_config(launcher.config_data)
        
        # Aggiorna solo il conteggio app
        if hasattr(launcher, 'apps'):
            self.apps_count_label.setText(f"Apps: {len(launcher.apps)}")
        
        parent_rect = launcher.geometry()
        parent_width = parent_rect.width()
        parent_height = parent_rect.height()
        
        self.setGeometry(parent_width, 0, self.width(), parent_height)
        
        self.show()
        self.raise_()
        self.setFocus()
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        start_pos = QPoint(parent_width, 0)
        end_pos = QPoint(parent_width - self.width(), 0)
        
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()
        
        self.current_index = 0
        self.update_focus()
        
    def close_menu(self):
        if hasattr(self.launcher, 'sound_manager'):
            self.launcher.sound_manager.back()  # ← Indietro
            
        if not self.is_open:
            return
        
        parent_width = self.launcher.width() if self.launcher else 1920
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        start_pos = self.pos()
        end_pos = QPoint(parent_width, 0)
        
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.finished.connect(self._on_close_finished)
        self.animation.start()
        
    def _on_close_finished(self):
        self.hide()
        self.is_open = False
        self.menu_closed.emit()
        
    def update_focus(self):
        """Focus con stile coerente"""
        for i, item in enumerate(self.menu_items):
            if i == self.current_index:
                if isinstance(item, QPushButton):
                    # Check se è il pulsante GitHub (ha l'icona)
                    if hasattr(item, 'icon') and not item.icon().isNull():
                        # Stile specifico per pulsante GitHub
                        item.setStyleSheet(f"""
                            QPushButton {{
                                background-color: #3a3a3a;
                                border: 3px solid white;
                                border-radius: {self.scaling.scale(8)}px;
                                color: white;
                                font-size: {self.scaling.scale_font(13)}px;
                                font-weight: bold;
                                text-align: left;
                                padding-left: {self.scaling.scale(12)}px;
                                padding-right: {self.scaling.scale(12)}px;
                            }}
                        """)
                    else:
                        # Stile per altri pulsanti (quick actions)
                        item.setStyleSheet(f"""
                            QPushButton {{
                                background-color: #3a3a3a;
                                border: 3px solid white;
                                border-radius: {self.scaling.scale(8)}px;
                                text-align: left;
                            }}
                        """)
                else:
                    item.setStyleSheet(f"""
                        QWidget {{
                            background-color: #3a3a3a;
                            border: 3px solid white;
                            border-radius: {self.scaling.scale(8)}px;
                        }}
                    """)
            else:
                if isinstance(item, QPushButton):
                    # Check se è il pulsante GitHub
                    if hasattr(item, 'icon') and not item.icon().isNull():
                        # Stile specifico per pulsante GitHub unfocused
                        item.setStyleSheet(f"""
                            QPushButton {{
                                background-color: #3a3a3a;
                                border: 2px solid #555;
                                border-radius: {self.scaling.scale(6)}px;
                                color: white;
                                font-size: {self.scaling.scale_font(13)}px;
                                font-weight: bold;
                                text-align: left;
                                padding-left: {self.scaling.scale(12)}px;
                                padding-right: {self.scaling.scale(12)}px;
                            }}
                            QPushButton:hover {{
                                background-color: #4a4a4a;
                                border-color: #666;
                            }}
                        """)
                    else:
                        # Stile per altri pulsanti unfocused
                        item.setStyleSheet(f"""
                            QPushButton {{
                                background-color: #2a2a2a;
                                border: 2px solid #444;
                                border-radius: {self.scaling.scale(8)}px;
                                text-align: left;
                            }}
                            QPushButton:hover {{
                                background-color: #3a3a3a;
                            }}
                        """)
                else:
                    item.setStyleSheet(f"""
                        QWidget {{
                            background-color: #2a2a2a;
                            border: 2px solid #444;
                            border-radius: {self.scaling.scale(8)}px;
                        }}
                    """)
                    
    def navigate_up(self):
        if self.current_index > 0:
            if hasattr(self.launcher, 'sound_manager'):
                self.launcher.sound_manager.navigate()
            self.current_index -= 1
            self.update_focus()
            self._ensure_visible()
            
    def navigate_down(self):
        if self.current_index < len(self.menu_items) - 1:
            if hasattr(self.launcher, 'sound_manager'):
                self.launcher.sound_manager.navigate()
            self.current_index += 1
            self.update_focus()
            self._ensure_visible()
            
    def activate_current(self):
        if hasattr(self.launcher, 'sound_manager'):
            self.launcher.sound_manager.select()  #
        current_item = self.menu_items[self.current_index]
        
        if isinstance(current_item, QPushButton):
            current_item.click()
        else:
            # Per i toggle, dobbiamo simulare il click corretto
            toggle = current_item.checkbox
            new_state = not toggle.isChecked()
            toggle.setChecked(new_state)
            
            # Trova quale toggle è e chiama il callback corretto
            if current_item == self.clock_toggle:
                self._handle_toggle('show_clock', new_state)
            elif current_item == self.sound_toggle:
                self._handle_toggle('sound_effects', new_state)
            elif current_item == self.fullscreen_toggle:
                self._handle_toggle('fullscreen', new_state)
            
    def _ensure_visible(self):
        if not self.menu_items or self.current_index >= len(self.menu_items):
            return
        
        current_item = self.menu_items[self.current_index]
        
        # Trova lo scroll area
        scroll_area = None
        parent = current_item.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                scroll_area = parent
                break
            parent = parent.parent()
        
        if not scroll_area:
            return
        
        # Calcola la posizione reale del widget (anche se annidato)
        item_y = 0
        widget = current_item
        
        # Risali la gerarchia dei widget fino al contenuto dello scroll area
        scroll_content = scroll_area.widget()
        while widget and widget != scroll_content:
            item_y += widget.y()
            widget = widget.parent()
            if widget == scroll_content:
                break
        
        item_height = current_item.height()
        viewport_height = scroll_area.viewport().height()
        scrollbar = scroll_area.verticalScrollBar()
        current_scroll = scrollbar.value()
        
        visible_top = current_scroll
        visible_bottom = current_scroll + viewport_height
        item_top = item_y
        item_bottom = item_y + item_height
        padding = self.scaling.scale(20)
        
        # Scrolla se necessario
        if item_bottom + padding > visible_bottom:
            new_scroll = item_bottom - viewport_height + padding
            scrollbar.setValue(int(new_scroll))
        elif item_top - padding < visible_top:
            new_scroll = item_top - padding
            scrollbar.setValue(int(new_scroll))
            
    def keyPressEvent(self, event):
        """Gestisce input da tastiera/controller"""
        if event.isAutoRepeat():
            return
            
        key = event.key()
        
        if key == Qt.Key.Key_Up:
            self.navigate_up()
        elif key == Qt.Key.Key_Down:
            self.navigate_down()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.activate_current()
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_S):
            self.close_menu()
        else:
            super().keyPressEvent(event)

    # ===== DIALOG HELPER METHODS =====

    def _show_confirm_dialog(self, title, message):
        """Mostra un dialog di conferma stilizzato (Yes/No)"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedSize(self.scaling.scale(550), self.scaling.scale(450))
        
        dialog.setStyleSheet("""
            QDialog { 
                background-color: #1a1a1a; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(self.scaling.scale(20))
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30)
        )
        
        # === HEADER CON TITOLO ===
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(20)}px; 
                font-weight: bold;
                color: white;
                background: transparent;
                border: none;
            }}
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        layout.addWidget(header_widget)
        
        # === MESSAGGIO IN RETTANGOLO ===
        message_widget = QWidget()
        message_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        message_layout = QVBoxLayout(message_widget)
        message_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        message_label = QLabel(message)
        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(13)}px;
                color: #cccccc;
                background: transparent;
                border: none;
            }}
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        message_label.setWordWrap(True)
        message_layout.addWidget(message_label)
        
        layout.addWidget(message_widget)
        layout.addStretch()
        
        # === PULSANTI ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scaling.scale(15))
        
        yes_button = QPushButton("Yes")
        yes_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        yes_button.clicked.connect(dialog.accept)
        
        no_button = QPushButton("No")
        no_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        no_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Navigazione con tastiera
        confirm_buttons = [yes_button, no_button]
        confirm_index = [1]  # Default su "No"
        
        def update_confirm_focus():
            for i, btn in enumerate(confirm_buttons):
                if i == confirm_index[0]:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #2a2a2a;
                            color: white;
                            border: 3px solid white;
                            padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px;
                            border-radius: {self.scaling.scale(8)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
                    """)
                else:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #2a2a2a;
                            color: white;
                            border: 2px solid #444;
                            padding: {self.scaling.scale(12)}px {self.scaling.scale(30)}px;
                            border-radius: {self.scaling.scale(8)}px;
                            font-size: {self.scaling.scale_font(14)}px;
                            font-weight: bold;
                        }}
                        QPushButton:hover {{ background-color: #3a3a3a; }}
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
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                confirm_buttons[confirm_index[0]].click()
            elif key == Qt.Key.Key_Escape:
                dialog.reject()
        
        dialog.keyPressEvent = confirm_key_handler
        update_confirm_focus()
        
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _show_success_dialog(self, title, message):
        """Mostra un dialog di successo stilizzato (solo OK)"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedSize(self.scaling.scale(500), self.scaling.scale(400))
        
        dialog.setStyleSheet("""
            QDialog { 
                background-color: #1a1a1a; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(self.scaling.scale(20))
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30)
        )
        
        # === HEADER CON TITOLO (VERDE PER SUCCESSO) ===
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a3a2a;
                border: 2px solid #4CAF50;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(20)}px; 
                font-weight: bold;
                color: #4CAF50;
                background: transparent;
                border: none;
            }}
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        layout.addWidget(header_widget)
        
        # === MESSAGGIO IN RETTANGOLO ===
        message_widget = QWidget()
        message_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        message_layout = QVBoxLayout(message_widget)
        message_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        message_label = QLabel(message)
        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(13)}px;
                color: #cccccc;
                background: transparent;
                border: none;
            }}
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        message_label.setWordWrap(True)
        message_layout.addWidget(message_label)
        
        layout.addWidget(message_widget)
        layout.addStretch()
        
        # === PULSANTE OK ===
        ok_button = QPushButton("OK")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.clicked.connect(dialog.accept)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 3px solid #4CAF50;
                padding: {self.scaling.scale(12)}px {self.scaling.scale(40)}px;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(14)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Gestione tasti
        def ok_key_handler(event):
            if event.isAutoRepeat():
                return
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
                dialog.accept()
        
        dialog.keyPressEvent = ok_key_handler
        dialog.exec()
        
    
    
    def _show_error_dialog(self, title, message):
        """Mostra un dialog di errore stilizzato (solo OK)"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setFixedSize(self.scaling.scale(500), self.scaling.scale(400))
        
        dialog.setStyleSheet("""
            QDialog { 
                background-color: #1a1a1a; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(self.scaling.scale(20))
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30)
        )
        
        # === HEADER CON TITOLO (ROSSO PER ERRORE) ===
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #3a2a2a;
                border: 2px solid #ff4a4a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(20)}px; 
                font-weight: bold;
                color: #ff4a4a;
                background: transparent;
                border: none;
            }}
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        layout.addWidget(header_widget)
        
        # === MESSAGGIO IN RETTANGOLO ===
        message_widget = QWidget()
        message_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(15)}px;
            }}
        """)
        message_layout = QVBoxLayout(message_widget)
        message_layout.setContentsMargins(
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15),
            self.scaling.scale(15)
        )
        
        message_label = QLabel(message)
        message_label.setStyleSheet(f"""
            QLabel {{
                font-size: {self.scaling.scale_font(13)}px;
                color: #cccccc;
                background: transparent;
                border: none;
            }}
        """)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        message_label.setWordWrap(True)
        message_layout.addWidget(message_label)
        
        layout.addWidget(message_widget)
        layout.addStretch()
        
        # === PULSANTE OK ===
        ok_button = QPushButton("OK")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.clicked.connect(dialog.accept)
        ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 3px solid #ff4a4a;
                padding: {self.scaling.scale(12)}px {self.scaling.scale(40)}px;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(14)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Gestione tasti
        def ok_key_handler(event):
            if event.isAutoRepeat():
                return
            key = event.key()
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
                dialog.accept()
        
        dialog.keyPressEvent = ok_key_handler
        dialog.exec()
    
    