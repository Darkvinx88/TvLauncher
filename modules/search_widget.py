import os
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QSize, QFileInfo
from PyQt6.QtGui import QFont, QKeyEvent, QColor, QPixmap, QIcon
from PyQt6.QtWidgets import QFileIconProvider

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    try:
        import win32api
        import win32con
        import win32gui
        import win32ui
        HAS_WIN32 = True
    except ImportError:
        HAS_WIN32 = False
        print("⚠️ win32api not available, icons will be basic")
else:
    HAS_WIN32 = False


class QuickSearchWidget(QWidget):
    """
    Quick search widget with live app filtering.
    Supports keyboard and joypad/remote navigation.
    Uses Qt Icon Theme Engine for optimal Linux performance.
    """
    app_selected = pyqtSignal(int)
    search_closed = pyqtSignal()
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self.apps = []
        self.filtered_indices = []
        self.current_selection = 0
        self.is_typing_mode = True
        
        self.launcher_parent = parent
        
        self.init_ui()
        self.hide()
    
    def init_ui(self):
        """Initialize UI with uniform palette"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        width = self.scaling.scale(800)
        height = self.scaling.scale(600)
        self.setFixedSize(width, height)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: #1a1a1a;
                border-radius: {self.scaling.scale(20)}px;
                border: {self.scaling.scale(2)}px solid #444;
            }}
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(self.scaling.scale(20))
        container_layout.setContentsMargins(
            self.scaling.scale(30),
            self.scaling.scale(30),
            self.scaling.scale(30),
            self.scaling.scale(30)
        )
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"""
            font-size: {self.scaling.scale_font(32)}px;
        """)
        header_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to search apps...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2a2a2a;
                color: white;
                border: {self.scaling.scale(2)}px solid #444;
                border-radius: {self.scaling.scale(12)}px;
                padding: {self.scaling.scale(15)}px {self.scaling.scale(20)}px;
                font-size: {self.scaling.scale_font(20)}px;
                font-weight: 500;
            }}
            QLineEdit:focus {{
                border: {self.scaling.scale(2)}px solid white;
            }}
        """)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        header_layout.addWidget(self.search_input, stretch=1)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: rgba(255, 255, 255, 0.7);
                font-size: {self.scaling.scale_font(24)}px;
                border: {self.scaling.scale(2)}px solid #444;
                border-radius: {self.scaling.scale(20)}px;
                padding: {self.scaling.scale(8)}px;
                min-width: {self.scaling.scale(40)}px;
                min-height: {self.scaling.scale(40)}px;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
                color: white;
            }}
            QPushButton:pressed {{
                background-color: #444;
            }}
        """)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.clicked.connect(self.close_search)
        header_layout.addWidget(self.close_btn)
        
        container_layout.addLayout(header_layout)
        
        self.mode_label = QLabel("🔤 TYPING MODE")
        self.mode_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(11)}px;
            font-weight: 600;
            padding: {self.scaling.scale(5)}px {self.scaling.scale(10)}px;
        """)
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.mode_label)
        
        results_label = QLabel("Results")
        results_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(14)}px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        container_layout.addWidget(results_label)
        
        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(32, 32))
        self.results_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #2a2a2a;
                border: {self.scaling.scale(2)}px solid #444;
                border-radius: {self.scaling.scale(12)}px;
                padding: {self.scaling.scale(10)}px;
                font-size: {self.scaling.scale_font(16)}px;
                outline: none;
            }}
            QListWidget::item {{
                color: rgba(255, 255, 255, 0.7);
                padding: {self.scaling.scale(15)}px {self.scaling.scale(20)}px;
                border-radius: {self.scaling.scale(8)}px;
                margin: {self.scaling.scale(2)}px 0px;
            }}
            QListWidget::item:selected {{
                background-color: #3a3a3a;
                color: white;
                font-weight: 600;
                border: {self.scaling.scale(2)}px solid white;
            }}
            QListWidget::item:hover {{
                background-color: #333;
            }}
        """)
        self.results_list.itemDoubleClicked.connect(self.on_item_activated)
        container_layout.addWidget(self.results_list, stretch=1)
        
        # === FOOTER ===
        instructions_layout = QHBoxLayout()
        instructions_layout.setSpacing(self.scaling.scale(20))
        
        instructions = [
            ("Type", "Search"),
            ("↑↓", "Navigate"),
            ("Enter/A", "Launch"),
            ("Esc/B", "Close"),
            ("Tab/X", "Mode")
        ]
        
        for key, action in instructions:
            inst_widget = QWidget()
            inst_layout = QHBoxLayout(inst_widget)
            inst_layout.setContentsMargins(0, 0, 0, 0)
            inst_layout.setSpacing(self.scaling.scale(8))
            
            key_label = QLabel(key)
            key_label.setStyleSheet(f"""
                background-color: #2a2a2a;
                color: white;
                padding: {self.scaling.scale(4)}px {self.scaling.scale(10)}px;
                border-radius: {self.scaling.scale(6)}px;
                border: {self.scaling.scale(1)}px solid #444;
                font-size: {self.scaling.scale_font(12)}px;
                font-weight: 600;
            """)
            
            action_label = QLabel(action)
            action_label.setStyleSheet(f"""
                color: rgba(255, 255, 255, 0.5);
                font-size: {self.scaling.scale_font(12)}px;
            """)
            
            inst_layout.addWidget(key_label)
            inst_layout.addWidget(action_label)
            instructions_layout.addWidget(inst_widget)
        
        instructions_layout.addStretch()
        container_layout.addLayout(instructions_layout)
        
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(self.scaling.scale(50))
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, self.scaling.scale(10))
        self.container.setGraphicsEffect(shadow)
    
    def set_apps(self, apps):
        """Set app list to search"""
        self.apps = apps
        self.update_results()
    
    def show_search(self):
        """Show search widget with animation"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = (parent_rect.width() - self.width()) // 2
            y = (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        
        self.show()
        self.raise_()
        
        self.search_input.clear()
        self.search_input.setFocus()
        self.is_typing_mode = True
        self.current_selection = 0
        self.update_mode_indicator()
        self.update_results()
        
        self.setWindowOpacity(0)
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_in.start()
        self.fade_animation = fade_in
    
    def close_search(self):
        """Close search widget with animation"""
        fade_out = QPropertyAnimation(self, b"windowOpacity")
        fade_out.setDuration(150)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        fade_out.finished.connect(self.hide)
        fade_out.finished.connect(self.search_closed.emit)
        fade_out.start()
        self.fade_animation = fade_out
    
    def on_search_text_changed(self, text):
        """Handle search text change"""
        self.update_results()
        if text and not self.is_typing_mode:
            self.is_typing_mode = True
            self.update_mode_indicator()
    
    def _load_icon_from_theme(self, app_data):
        """Load icon using Qt Icon Theme Engine - OPTIMIZED"""
        # Try multiple icon fields for compatibility
        icon_value = app_data.get('icon_name') or app_data.get('icon')
        
        if not icon_value:
            # LAST RESORT: Extract from path
            path = app_data.get('path', '')
            if path:
                # Get command name from path
                if ' ' in path:
                    cmd = path.split()[0]
                else:
                    cmd = path
                icon_value = os.path.basename(cmd)
        
        if not icon_value:
            return QIcon()
        
        if IS_WINDOWS:
            # Windows: extract from exe or load file
            if os.path.exists(icon_value):
                if icon_value.lower().endswith('.exe'):
                    provider = QFileIconProvider()
                    file_info = QFileInfo(icon_value)
                    return provider.icon(file_info)
                else:
                    return QIcon(icon_value)
            return QIcon()
        else:
            # Linux: Qt Icon Theme Engine (FAST!)
            # FIRST: Try as theme icon name (most common case)
            icon = QIcon.fromTheme(icon_value)
            if not icon.isNull():
                return icon
            
            # SECOND: If it's an absolute path, load directly
            if os.path.isabs(icon_value):
                if os.path.exists(icon_value):
                    return QIcon(icon_value)
                # Try with extensions if path doesn't exist
                for ext in ['.png', '.svg', '.xpm']:
                    if os.path.exists(icon_value + ext):
                        return QIcon(icon_value + ext)
            
            # THIRD: Try fromTheme with extensions
            for ext in ['.png', '.svg', '.xpm', '']:
                test_icon = QIcon.fromTheme(icon_value + ext)
                if not test_icon.isNull():
                    return test_icon
            
            # FOURTH: Extract icon name from path and try again
            if '/' in icon_value or '\\' in icon_value:
                icon_name = os.path.basename(icon_value)
                # Remove extension
                icon_name = os.path.splitext(icon_name)[0]
                icon = QIcon.fromTheme(icon_name)
                if not icon.isNull():
                    return icon
            
            return QIcon()
    
    def update_results(self):
        """Update results list based on search WITH ICON THEME"""
        search_text = self.search_input.text().lower().strip()
        
        self.results_list.clear()
        self.filtered_indices = []

        temp_results = []

        if not search_text:
            for i, app in enumerate(self.apps):
                temp_results.append((app["name"], i, app))
        else:
            for i, app in enumerate(self.apps):
                app_name = app['name']
                if search_text in app_name.lower():
                    temp_results.append((app_name, i, app))

        # Sort alphabetically
        temp_results.sort(key=lambda x: x[0].lower())

        # Add to QListWidget with icons
        for name, original_index, app_data in temp_results:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, original_index)
            
            # Load icon using Qt Icon Theme (FAST!)
            icon = self._load_icon_from_theme(app_data)
            
            # DEBUG: Print if icon not found
            if icon.isNull():
                print(f"⚠️  No icon for '{name}':")
                print(f"   icon: {app_data.get('icon')}")
                print(f"   icon_name: {app_data.get('icon_name')}")
            
            if not icon.isNull():
                item.setIcon(icon)
            else:
                # Fallback emoji if no icon
                item.setText(f"🎮  {name}")
            
            self.results_list.addItem(item)
            self.filtered_indices.append(original_index)

        # Select first result
        if self.results_list.count() > 0:
            self.current_selection = 0
            self.results_list.setCurrentRow(0)

        # No results
        if self.results_list.count() == 0:
            item = QListWidgetItem("❌  No apps found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results_list.addItem(item)
    
    def update_mode_indicator(self):
        """Update mode indicator"""
        if self.is_typing_mode:
            self.mode_label.setText("🔤 TYPING MODE")
            self.mode_label.setStyleSheet(f"""
                color: white;
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 600;
                padding: {self.scaling.scale(5)}px {self.scaling.scale(10)}px;
            """)
        else:
            self.mode_label.setText("🎯 NAVIGATION MODE")
            self.mode_label.setStyleSheet(f"""
                color: rgba(255, 255, 255, 0.6);
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: 600;
                padding: {self.scaling.scale(5)}px {self.scaling.scale(10)}px;
            """)
    
    def switch_mode(self):
        """Switch between typing and navigation mode"""
        self.is_typing_mode = not self.is_typing_mode
        self.update_mode_indicator()
        
        if self.is_typing_mode:
            self.search_input.setFocus()
        else:
            self.results_list.setFocus()
    
    def navigate_up(self):
        """Navigate up in results"""
        if self.results_list.count() > 0:
            current = self.results_list.currentRow()
            prev_row = max(current - 1, 0)
            self.results_list.setCurrentRow(prev_row)
            if self.is_typing_mode:
                self.is_typing_mode = False
                self.update_mode_indicator()
    
    def navigate_down(self):
        """Navigate down in results"""
        if self.results_list.count() > 0:
            current = self.results_list.currentRow()
            next_row = min(current + 1, self.results_list.count() - 1)
            self.results_list.setCurrentRow(next_row)
            if self.is_typing_mode:
                self.is_typing_mode = False
                self.update_mode_indicator()
    
    def launch_selected(self):
        """Launch selected app"""
        if self.results_list.count() > 0 and self.filtered_indices:
            current_row = self.results_list.currentRow()
            if 0 <= current_row < len(self.filtered_indices):
                app_index = self.filtered_indices[current_row]
                self.app_selected.emit(app_index)
                self.close_search()
    
    def on_item_activated(self, item):
        """Handle double click or Enter on item"""
        if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
            app_index = item.data(Qt.ItemDataRole.UserRole)
            if app_index is not None:
                self.app_selected.emit(app_index)
                self.close_search()
    
    def handle_joypad_input(self, key_code):
        """Handle joypad input (called by parent)"""
        if key_code == Qt.Key.Key_Escape:
            self.close_search()
        elif key_code == Qt.Key.Key_Up:
            self.navigate_up()
        elif key_code == Qt.Key.Key_Down:
            self.navigate_down()
        elif key_code == Qt.Key.Key_Return or key_code == Qt.Key.Key_Enter:
            self.launch_selected()
        elif key_code == Qt.Key.Key_E:  # X button for mode switch
            self.switch_mode()
        elif key_code == Qt.Key.Key_Backspace:
            if not self.is_typing_mode:
                self.is_typing_mode = True
                self.search_input.setFocus()
                self.update_mode_indicator()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input"""
        key = event.key()
        
        if key == Qt.Key.Key_Escape:
            self.close_search()
            return
        
        if key == Qt.Key.Key_Tab:
            self.switch_mode()
            event.accept()
            return
        
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.launch_selected()
            return
        
        if key == Qt.Key.Key_Down:
            self.navigate_down()
            event.accept()
            return
        
        if key == Qt.Key.Key_Up:
            self.navigate_up()
            event.accept()
            return
        
        if key == Qt.Key.Key_Backspace and not self.is_typing_mode:
            self.is_typing_mode = True
            self.search_input.setFocus()
            self.update_mode_indicator()
        
        if not self.is_typing_mode and event.text().isprintable():
            self.is_typing_mode = True
            self.search_input.setFocus()
            self.update_mode_indicator()
        
        super().keyPressEvent(event)
