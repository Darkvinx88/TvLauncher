"""
Category Editor Dialog - Versione migliorata con Emoji Picker
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QColorDialog, QMessageBox, QWidget, QScrollArea,
    QGridLayout, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QColor, QPixmap, QIcon, QPainter, QBrush, QPen
from pathlib import Path


class AnimatedToggle(QCheckBox):
    """Checkbox quadrato animato con spunta"""
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self._check_progress = 0.0
        self.setFixedSize(self.scaling.scale(32), self.scaling.scale(32))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Animation
        self.animation = QPropertyAnimation(self, b"check_progress", self)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(200)
        
        self.stateChanged.connect(self._animate_check)
    
    def _animate_check(self, state):
        if state == Qt.CheckState.Checked.value:
            self.animation.setEndValue(1.0)
        else:
            self.animation.setEndValue(0.0)
        self.animation.start()
    
    @pyqtProperty(float)
    def check_progress(self):
        return self._check_progress
    
    @check_progress.setter
    def check_progress(self, value):
        self._check_progress = value
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background box
        if self.isChecked() or self._check_progress > 0:
            # Interpolate between gray and green
            gray = QColor("#2a2a2a")
            green = QColor("#4CAF50")
            if self.underMouse():
                green = QColor("#5BC157")
            
            r = int(gray.red() + (green.red() - gray.red()) * self._check_progress)
            g = int(gray.green() + (green.green() - gray.green()) * self._check_progress)
            b = int(gray.blue() + (green.blue() - gray.blue()) * self._check_progress)
            bg_color = QColor(r, g, b)
        else:
            bg_color = QColor("#2a2a2a")
            if self.underMouse():
                bg_color = QColor("#333333")
        
        # Border
        border_color = QColor("#444444")
        if self.underMouse():
            border_color = QColor("#666666")
        if self.isChecked():
            border_color = QColor("#4CAF50")
            if self.underMouse():
                border_color = QColor("#5BC157")
        
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4,
                               self.scaling.scale(6), self.scaling.scale(6))
        
        # Draw checkmark with animation
        if self._check_progress > 0:
            painter.setPen(QPen(QColor("white"), self.scaling.scale(3), 
                              Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, 
                              Qt.PenJoinStyle.RoundJoin))
            
            # Scale checkmark based on progress
            scale = self._check_progress
            
            # Checkmark coordinates (relative)
            x_offset = self.width() * 0.25
            y_offset = self.height() * 0.5
            
            # Short line (bottom-left to middle)
            x1 = int(x_offset)
            y1 = int(y_offset)
            x2 = int(x_offset + (self.width() * 0.15 * scale))
            y2 = int(y_offset + (self.height() * 0.15 * scale))
            painter.drawLine(x1, y1, x2, y2)
            
            # Long line (middle to top-right)
            if scale > 0.5:
                progress = (scale - 0.5) * 2
                x3 = int(x_offset + (self.width() * 0.45 * progress))
                y3 = int(y_offset - (self.height() * 0.25 * progress))
                painter.drawLine(x2, y2, x3, y3)
    
    def hitButton(self, pos):
        return self.contentsRect().contains(pos)



class EmojiPickerDialog(QDialog):
    """Dialog per selezionare emoji"""
    
    # Emoji comuni per categorie
    CATEGORY_EMOJIS = [
        "🎮", "🎯", "🎨", "🎬", "🎵", "📚", "💼", "🔧",
        "⚙️", "🌐", "📱", "💻", "🖥️", "⌨️", "🖱️", "🎧",
        "📷", "🎥", "📝", "📊", "📈", "📉", "🗂️", "📦",
        "🔍", "🔐", "🔒", "🔓", "🔑", "🛠️", "⚡", "🔥",
        "💡", "🌟", "⭐", "✨", "🎁", "🏆", "🎪", "🎭",
        "🎲", "🃏", "🎰", "🧩", "🎪", "🎨", "🖌️", "✏️",
        "📐", "📏", "📌", "📍", "🔖", "🏷️", "💾", "💿",
    ]
    
    def __init__(self, current_emoji, scaling, parent=None):
        super().__init__(parent)
        self.selected_emoji = current_emoji
        self.scaling = scaling
        
        self.setWindowTitle("Select Icon")
        self.setModal(True)
        self.setFixedSize(self.scaling.scale(600), self.scaling.scale(500))
        
        self.setStyleSheet("QDialog { background-color: #1a1a1a; }")
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(
            self.scaling.scale(20),
            self.scaling.scale(20),
            self.scaling.scale(20),
            self.scaling.scale(20)
        )
        layout.setSpacing(self.scaling.scale(15))
        
        # Titolo
        title = QLabel("Select an icon for your category")
        title.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(18)}px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(title)
        
        # Griglia emoji
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: 2px solid #444;
                border-radius: {self.scaling.scale(8)}px;
                background: #2a2a2a;
            }}
            QScrollBar:vertical {{
                background-color: #2a2a2a;
                width: {self.scaling.scale(10)}px;
                border-radius: {self.scaling.scale(5)}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444;
                border-radius: {self.scaling.scale(4)}px;
            }}
        """)
        
        emoji_container = QWidget()
        emoji_container.setStyleSheet("background: #2a2a2a;")
        emoji_grid = QGridLayout(emoji_container)
        emoji_grid.setSpacing(self.scaling.scale(8))
        emoji_grid.setContentsMargins(
            self.scaling.scale(10),
            self.scaling.scale(10),
            self.scaling.scale(10),
            self.scaling.scale(10)
        )
        
        # Crea bottoni emoji
        cols = 8
        for i, emoji in enumerate(self.CATEGORY_EMOJIS):
            btn = QPushButton(emoji)
            btn.setFixedSize(self.scaling.scale(50), self.scaling.scale(50))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #3a3a3a;
                    border: 2px solid #555;
                    border-radius: {self.scaling.scale(8)}px;
                    font-size: {self.scaling.scale_font(24)}px;
                }}
                QPushButton:hover {{
                    background-color: #4a4a4a;
                    border-color: white;
                }}
            """)
            btn.clicked.connect(lambda checked, e=emoji: self._select_emoji(e))
            emoji_grid.addWidget(btn, i // cols, i % cols)
        
        scroll.setWidget(emoji_container)
        layout.addWidget(scroll)
        
        # Bottoni azione
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(self.scaling.scale(10))
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setFixedHeight(self.scaling.scale(40))
        
        ok_btn = QPushButton("Select")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setFixedHeight(self.scaling.scale(40))
        
        for btn in [cancel_btn, ok_btn]:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    border-radius: {self.scaling.scale(8)}px;
                    font-size: {self.scaling.scale_font(14)}px;
                    font-weight: bold;
                    padding: {self.scaling.scale(8)}px {self.scaling.scale(20)}px;
                }}
                QPushButton:hover {{
                    background-color: #3a3a3a;
                }}
            """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _select_emoji(self, emoji):
        self.selected_emoji = emoji
        self.accept()


class CategoryEditorDialog(QDialog):
    """Dialog per modificare/aggiungere/rimuovere categorie"""
    
    def __init__(self, category_manager, scaling, parent=None):
        super().__init__(parent)
        self.category_manager = category_manager
        self.scaling = scaling
        self.selected_index = -1
        self.is_new_category = False
        self.current_emoji = "📦"
        
        self.setWindowTitle("Category Manager")
        self.setModal(True)
        self.setFixedSize(self.scaling.scale(900), self.scaling.scale(950))
        
        self.setStyleSheet("QDialog { background-color: #0f0f0f; }")
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        main_layout.addWidget(header)
        
        # Content
        scroll = self._create_scroll_area()
        content = self._create_content()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # Footer
        footer = self._create_footer()
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)
        self._refresh_list()
    
    def _create_header(self):
        """Header con icona"""
        header = QWidget()
        header.setFixedHeight(self.scaling.scale(125))
        header.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-bottom: 2px solid #444;
            }
        """)
        
        layout = QVBoxLayout(header)
        
        layout.setContentsMargins(
            self.scaling.scale(40), self.scaling.scale(25),
            self.scaling.scale(40), self.scaling.scale(25)
        )
        
        # Titolo container
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent; border: none;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setSpacing(self.scaling.scale(15))
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Icona
        icon_label = QLabel()
        icon_path = Path("assets/icons/folder.png")
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(
                self.scaling.scale(40), self.scaling.scale(40),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            icon_label.setPixmap(scaled_pixmap)
        else:
            icon_label.setText("📁")
            icon_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-size: {self.scaling.scale_font(36)}px;
                    background: transparent;
                    border: none;
                }}
            """)
        title_layout.addWidget(icon_label)
        
        # Titolo
        title = QLabel("Category Manager")
        title.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(36)}px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
        """)
        title_layout.addWidget(title)
        title_layout.addStretch()
        
        layout.addWidget(title_container)
        
        # Sottotitolo
        subtitle = QLabel("Add, edit, or remove app categories")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.5);
                font-size: {self.scaling.scale_font(15)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(subtitle)
        
        return header
    
    def _create_scroll_area(self):
        """Scroll area"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: #0f0f0f;
            }}
            QScrollBar:vertical {{
                background-color: #2a2a2a;
                width: {self.scaling.scale(10)}px;
                border-radius: {self.scaling.scale(5)}px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444;
                border-radius: {self.scaling.scale(4)}px;
                min-height: {self.scaling.scale(40)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #555;
            }}
        """)
        
        return scroll
    
    def _create_content(self):
        """Content con sezioni"""
        content = QWidget()
        content.setStyleSheet("background: #1a1a1a")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            self.scaling.scale(40), self.scaling.scale(15),
            self.scaling.scale(40), self.scaling.scale(15)
        )
        layout.setSpacing(self.scaling.scale(25))
        
        # Sezione: Current Categories
        section_header = self._create_section_header(
            "Current Categories",
            "Select a category to edit"
        )
        layout.addWidget(section_header)
        
        # Lista categorie
        self.category_list = QListWidget()
        self.category_list.setFixedHeight(self.scaling.scale(250))
        self.category_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(15)}px;
                padding: {self.scaling.scale(15)}px;
                font-size: {self.scaling.scale_font(15)}px;
            }}
            QListWidget::item {{
                padding: {self.scaling.scale(15)}px;
                border-radius: {self.scaling.scale(8)}px;
                margin: {self.scaling.scale(3)}px 0px;
            }}
            QListWidget::item:selected {{
                background-color: #3a3a3a;
                border: 3px solid white;
            }}
            QListWidget::item:hover {{
                background-color: #353535;
            }}
        """)
        self.category_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.category_list.itemClicked.connect(self._on_category_selected)
        layout.addWidget(self.category_list)
        
        # Sezione: Edit Category
        section_header2 = self._create_section_header(
            "Edit Category",
            "Modify name, icon, and color"
        )
        layout.addWidget(section_header2)
        
        # Editor
        editor = self._create_editor()
        layout.addWidget(editor)
        
        layout.addStretch()
        
        return content
    
    def _create_section_header(self, title, description):
        """Section header"""
        header = QWidget()
        header.setFixedHeight(self.scaling.scale(60))
        header.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(header)
        layout.setSpacing(self.scaling.scale(5))
        layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(18)}px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.4);
                font-size: {self.scaling.scale_font(12)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(desc_label)
        
        return header
    
    def _create_editor(self):
        """Editor fields"""
        editor = QWidget()
        editor.setFixedHeight(self.scaling.scale(260))
        editor.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(12)}px;
            }}
        """)
        
        layout = QVBoxLayout(editor)
        layout.setSpacing(self.scaling.scale(5))
        layout.setContentsMargins(
            self.scaling.scale(25), self.scaling.scale(10),
            self.scaling.scale(25), self.scaling.scale(10)
        )
        
        # Name row
        name_row = self._create_name_row()
        layout.addWidget(name_row)
        
        # Icon row (con emoji picker)
        icon_row = self._create_icon_row()
        layout.addWidget(icon_row)
        
        # Color row
        color_row = self._create_color_row()
        layout.addWidget(color_row)
        
        # Default category toggle
        default_row = self._create_default_row()
        layout.addWidget(default_row)
        
        return editor
    
    def _create_name_row(self):
        """Campo nome"""
        row = QWidget()
        row.setFixedHeight(self.scaling.scale(60))
        row.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.scaling.scale(15))
        
        # Label
        label_container = QWidget()
        label_container.setStyleSheet("background: transparent; border: none;")
        label_layout = QVBoxLayout(label_container)
        label_layout.setSpacing(self.scaling.scale(3))
        label_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Name")
        label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(15)}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(label)
        
        hint = QLabel("Category display name")
        hint.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.35);
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(hint)
        label_layout.addStretch()
        
        layout.addWidget(label_container, 1)
        
        # Input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Games")
        self.name_input.setFixedHeight(self.scaling.scale(45))
        self.name_input.setFixedWidth(self.scaling.scale(300))
        self.name_input.textChanged.connect(self._on_field_changed)
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1a1a1a;
                color: white;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(8)}px;
                padding: {self.scaling.scale(10)}px {self.scaling.scale(15)}px;
                font-size: {self.scaling.scale_font(14)}px;
            }}
            QLineEdit:focus {{
                border-color: white;
            }}
        """)
        
        layout.addWidget(self.name_input)
        
        return row
    
    def _create_icon_row(self):
        """Riga icona con emoji picker"""
        row = QWidget()
        row.setFixedHeight(self.scaling.scale(75))
        row.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.scaling.scale(15))
        
        # Label
        label_container = QWidget()
        label_container.setStyleSheet("background: transparent; border: none;")
        label_layout = QVBoxLayout(label_container)
        label_layout.setSpacing(self.scaling.scale(3))
        label_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Icon")
        label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(15)}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(label)
        
        hint = QLabel("Category icon")
        hint.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.35);
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(hint)
        label_layout.addStretch()
        
        layout.addWidget(label_container, 1)
        
        # Preview icona corrente
        self.icon_preview = QLabel(self.current_emoji)
        self.icon_preview.setFixedSize(self.scaling.scale(60), self.scaling.scale(45))
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setStyleSheet(f"""
            QLabel {{
                background-color: #1a1a1a;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(28)}px;
            }}
        """)
        layout.addWidget(self.icon_preview)
        
        # Bottone per aprire picker
        self.icon_picker_btn = QPushButton("Choose Icon")
        self.icon_picker_btn.setFixedSize(self.scaling.scale(140), self.scaling.scale(45))
        self.icon_picker_btn.clicked.connect(self._open_emoji_picker)
        self.icon_picker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3a3a3a;
                color: white;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(13)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
            }}
        """)
        layout.addWidget(self.icon_picker_btn)
        
        return row
    
    def _create_color_row(self):
        """Riga colore"""
        row = QWidget()
        row.setFixedHeight(self.scaling.scale(75))
        row.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.scaling.scale(15))
        
        # Label
        label_container = QWidget()
        label_container.setStyleSheet("background: transparent; border: none;")
        label_layout = QVBoxLayout(label_container)
        label_layout.setSpacing(self.scaling.scale(3))
        label_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Color")
        label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(15)}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(label)
        
        hint = QLabel("Category accent color")
        hint.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.35);
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(hint)
        label_layout.addStretch()
        
        layout.addWidget(label_container, 1)
        
        # Color input
        self.color_input = QLineEdit()
        self.color_input.setPlaceholderText("#4CAF50")
        self.color_input.setFixedHeight(self.scaling.scale(45))
        self.color_input.setFixedWidth(self.scaling.scale(150))
        self.color_input.textChanged.connect(self._on_field_changed)
        self.color_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #1a1a1a;
                color: white;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(8)}px;
                padding: {self.scaling.scale(10)}px {self.scaling.scale(15)}px;
                font-size: {self.scaling.scale_font(14)}px;
            }}
            QLineEdit:focus {{
                border-color: white;
            }}
        """)
        layout.addWidget(self.color_input)
        
        # Pick button
        self.color_picker_btn = QPushButton("Pick Color")
        self.color_picker_btn.setFixedSize(self.scaling.scale(100), self.scaling.scale(45))
        self.color_picker_btn.clicked.connect(self._pick_color)
        self.color_picker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #3a3a3a;
                color: white;
                border: 2px solid #555;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(13)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
            }}
        """)
        layout.addWidget(self.color_picker_btn)
        
        return row
    
    def _create_default_row(self):
        """Riga per mark as default"""
        row = QWidget()
        row.setFixedHeight(self.scaling.scale(60))
        row.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.scaling.scale(15))
        
        # Label
        label_container = QWidget()
        label_container.setStyleSheet("background: transparent; border: none;")
        label_layout = QVBoxLayout(label_container)
        label_layout.setSpacing(self.scaling.scale(3))
        label_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Default Category")
        label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(15)}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(label)
        
        hint = QLabel("Show this category at launcher startup")
        hint.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.35);
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        label_layout.addWidget(hint)
        label_layout.addStretch()
        
        layout.addWidget(label_container, 1)
        
        # Animated Toggle Switch
        self.default_checkbox = AnimatedToggle(self.scaling)
        layout.addWidget(self.default_checkbox)
        
        return row

    
    def _create_footer(self):
        """Footer con pulsanti"""
        footer = QWidget()
        footer.setFixedHeight(self.scaling.scale(90))
        footer.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-top: 2px solid #444;
            }
        """)
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(
            self.scaling.scale(40), self.scaling.scale(25),
            self.scaling.scale(40), self.scaling.scale(25)
        )
        layout.setSpacing(self.scaling.scale(20))
        
        # Hint
        hint = QLabel("Navigate: ↑↓  •  Select: Enter  •  Close: Esc")
        hint.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.4);
                font-size: {self.scaling.scale_font(13)}px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scaling.scale(12))
        
        self.add_btn = QPushButton("+ Add")
        self.add_btn.clicked.connect(self._add_category)
        self.add_btn.setFixedSize(self.scaling.scale(100), self.scaling.scale(50))
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self._save_category)
        self.save_btn.setEnabled(False)
        self.save_btn.setFixedSize(self.scaling.scale(100), self.scaling.scale(50))
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self._delete_category)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setFixedSize(self.scaling.scale(110), self.scaling.scale(50))
        
        for btn in [self.add_btn, self.save_btn, self.delete_btn]:
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2a2a2a;
                    color: white;
                    border: 2px solid #444;
                    border-radius: {self.scaling.scale(8)}px;
                    font-size: {self.scaling.scale_font(14)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #3a3a3a;
                }}
                QPushButton:disabled {{
                    background-color: #1a1a1a;
                    color: #666;
                    border-color: #333;
                }}
            """)
        
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
        
        # Close button
        self.close_btn = QPushButton("Close")
        save_icon_path = Path("assets/icons/backup.png")
        if save_icon_path.exists():
            self.close_btn.setIcon(QIcon(str(save_icon_path)))
            self.close_btn.setIconSize(QSize(self.scaling.scale(24), self.scaling.scale(24)))
        
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setFixedSize(self.scaling.scale(150), self.scaling.scale(55))
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        layout.addWidget(self.close_btn)
        
        return footer
    
    # ===== METODI FUNZIONALI =====
    
    def _refresh_list(self):
        """Aggiorna la lista categorie"""
        self.category_list.clear()
        
        for i, category in enumerate(self.category_manager.categories):
            # Skip "All"
            if category['name'] == 'All':
                continue
            
            # Mostra marker se è default
            is_default = category.get('is_default', False)
            display_name = f"{category['icon']} {category['name']}"
            if is_default:
                display_name += " ⭐"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.category_list.addItem(item)
    
    def _on_category_selected(self, item):
        """Quando selezioni una categoria"""
        index = item.data(Qt.ItemDataRole.UserRole)
        self.selected_index = index
        self.is_new_category = False
        
        category = self.category_manager.categories[index]
        
        self.name_input.setText(category['name'])
        self.current_emoji = category.get('icon', '📦')
        self.icon_preview.setText(self.current_emoji)
        self.color_input.setText(category['color'])
        self.default_checkbox.setChecked(category.get('is_default', False))
        
        self.save_btn.setEnabled(True)
        self.delete_btn.setEnabled(len(self.category_manager.categories) > 2)
    
    def _on_field_changed(self):
        """Quando modifichi un campo"""
        has_name = bool(self.name_input.text().strip())
        self.save_btn.setEnabled(has_name)
    
    def _open_emoji_picker(self):
        """Apre emoji picker dialog"""
        picker = EmojiPickerDialog(self.current_emoji, self.scaling, self)
        if picker.exec() == QDialog.DialogCode.Accepted:
            self.current_emoji = picker.selected_emoji
            self.icon_preview.setText(self.current_emoji)
            self._on_field_changed()
    
    def _pick_color(self):
        """Apre color picker"""
        current_color = QColor(self.color_input.text() if self.color_input.text() else "#4CAF50")
        
        color_dialog = QColorDialog(current_color, self)
        color_dialog.setWindowTitle("Pick a Color")
        color_dialog.setStyleSheet("""
            QColorDialog {
                background-color: #1a1a1a;
            }
            QWidget {
                background-color: #1a1a1a;
                color: white;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: 8px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        
        if color_dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                self.color_input.setText(color.name())
    
    def _add_category(self):
        """Aggiungi nuova categoria"""
        self.category_list.clearSelection()
        
        self.name_input.clear()
        self.current_emoji = "📦"
        self.icon_preview.setText(self.current_emoji)
        self.color_input.setText("#4CAF50")
        self.default_checkbox.setChecked(False)
        
        self.selected_index = -1
        self.is_new_category = True
        
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        
        self.name_input.setFocus()
    
    def _save_category(self):
        """Salva categoria"""
        name = self.name_input.text().strip()
        icon = self.current_emoji
        color = self.color_input.text().strip()
        is_default = self.default_checkbox.isChecked()
        
        # Validazione
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Category name cannot be empty!")
            return
        
        if not color or not color.startswith('#'):
            color = "#4CAF50"
        
        # Controlla duplicati
        for i, cat in enumerate(self.category_manager.categories):
            if cat['name'].lower() == name.lower() and i != self.selected_index:
                QMessageBox.warning(self, "Duplicate", f"Category '{name}' already exists!")
                return
        
        
        if is_default:
            for cat in self.category_manager.categories:
                cat['is_default'] = False
        
        new_category = {
            "name": name,
            "icon": icon,
            "color": color,
            "is_default": is_default
        }
        
        if self.selected_index >= 0 and not self.is_new_category:
            # Modifica esistente
            old_name = self.category_manager.categories[self.selected_index]['name']
            self.category_manager.categories[self.selected_index] = new_category
            print(f"Category updated: {old_name} → {name}")
        else:
            # Nuova categoria
            self.category_manager.categories.append(new_category)
            print(f"Category added: {name}")
        
        self.is_new_category = False
        self.selected_index = -1
        
        self.name_input.clear()
        self.current_emoji = "📦"
        self.icon_preview.setText(self.current_emoji)
        self.color_input.setText("#4CAF50")
        self.default_checkbox.setChecked(False)
        
        self._refresh_list()
        self.save_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def _delete_category(self):
        """Elimina categoria"""
        if self.selected_index < 0:
            return
        
        category = self.category_manager.categories[self.selected_index]
        
        if category['name'] == 'All':
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete 'All' category!")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete category '{category['name']}'?\n\nApps in this category will be moved to 'Other'.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.category_manager.categories.pop(self.selected_index)
            print(f"Category deleted: {category['name']}")
            
            self._refresh_list()
            self.selected_index = -1
            self.is_new_category = False
            self.name_input.clear()
            self.current_emoji = "📦"
            self.icon_preview.setText(self.current_emoji)
            self.color_input.clear()
            self.default_checkbox.setChecked(False)
            self.save_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

# INTEGRAZIONE NEL SETTINGS MENU


def add_category_editor_to_settings(settings_menu):
    """Aggiunge il pulsante al Settings Menu"""
    from pathlib import Path
    icon_dir = Path("assets/icons")
    
    manage_cat_btn = settings_menu._create_menu_button(
        "Manage Categories",
        "Customize category names, icons, and colors",
        lambda: _open_category_editor(settings_menu),
        icon_dir / "folder.png"
    )
    
    content = settings_menu.findChild(QVBoxLayout)
    if content:
        for i in range(content.count()):
            widget = content.itemAt(i).widget()
            if widget and isinstance(widget, QLabel) and "Behavior" in widget.text():
                content.insertWidget(i - 1, manage_cat_btn)
                settings_menu.menu_items.append(manage_cat_btn)
                break


