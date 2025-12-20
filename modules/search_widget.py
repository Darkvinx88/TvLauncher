import os
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QSize
from PyQt6.QtGui import QFont, QKeyEvent, QColor, QPixmap, QIcon, QImage

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
    Widget di ricerca rapida con filtraggio live delle app.
    Supporta tastiera fisica e navigazione con joypad/telecomando.
    UI uniformata con la palette del launcher principale.
    """
    app_selected = pyqtSignal(int)  # Emette l'indice dell'app selezionata
    search_closed = pyqtSignal()    # Emette quando la ricerca viene chiusa
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self.apps = []  # Lista delle app da cercare
        self.filtered_indices = []  # Indici delle app filtrate
        self.current_selection = 0
        self.is_typing_mode = True  # True = digita, False = naviga risultati
        
        # Riferimento al parent per gestire input joypad
        self.launcher_parent = parent
        
        self.init_ui()
        self.hide()
    
    def init_ui(self):
        """Inizializza l'interfaccia utente con palette uniforme"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dimensioni responsive
        width = self.scaling.scale(800)
        height = self.scaling.scale(600)
        self.setFixedSize(width, height)
        
        # Container principale con sfondo scuro
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container interno - PALETTE UNIFORMATA
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
        
        # Icona ricerca
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"""
            font-size: {self.scaling.scale_font(32)}px;
        """)
        header_layout.addWidget(search_icon)
        
        # Campo di ricerca - PALETTE UNIFORMATA
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
        
        # Pulsante chiudi - PALETTE UNIFORMATA
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
        
        # Mode indicator - COLORI UNIFORMATI
        self.mode_label = QLabel("🔤 TYPING MODE")
        self.mode_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(11)}px;
            font-weight: 600;
            padding: {self.scaling.scale(5)}px {self.scaling.scale(10)}px;
        """)
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.mode_label)
        
        # === RISULTATI ===
        results_label = QLabel("Results")
        results_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(14)}px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        container_layout.addWidget(results_label)
        
        # Lista risultati - PALETTE UNIFORMATA
        self.results_list = QListWidget()
        self.results_list.setIconSize(QSize(32, 32))  # Come program_scanner
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
        
        # === FOOTER - Istruzioni ===
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
            
            # Keys - PALETTE UNIFORMATA
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
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(self.scaling.scale(50))
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, self.scaling.scale(10))
        self.container.setGraphicsEffect(shadow)
    
    def set_apps(self, apps):
        """Imposta la lista di app da cercare"""
        self.apps = apps
        self.update_results()
    
    def show_search(self):
        """Mostra il widget di ricerca con animazione"""
        if self.parent():
            # Centra rispetto al parent
            parent_rect = self.parent().geometry()
            x = (parent_rect.width() - self.width()) // 2
            y = (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        
        self.show()
        self.raise_()
        
        # Reset stato
        self.search_input.clear()
        self.search_input.setFocus()
        self.is_typing_mode = True
        self.current_selection = 0
        self.update_mode_indicator()
        self.update_results()
        
        # Animazione entrata
        self.setWindowOpacity(0)
        fade_in = QPropertyAnimation(self, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_in.start()
        self.fade_animation = fade_in
    
    def close_search(self):
        """Chiude il widget di ricerca con animazione"""
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
        """Gestisce il cambio del testo di ricerca"""
        self.update_results()
        # Auto-switch to typing mode quando si digita
        if text and not self.is_typing_mode:
            self.is_typing_mode = True
            self.update_mode_indicator()
    
    def _extract_icon_from_exe(self, exe_path):
        """Estrae l'icona da un file exe - COPIA ESATTA dal program_scanner.py"""
        try:
            from PyQt6.QtWidgets import QFileIconProvider
            from PyQt6.QtCore import QFileInfo
            
            if not exe_path or not os.path.exists(exe_path):
                return None
            
            provider = QFileIconProvider()
            file_info = QFileInfo(exe_path)
            icon = provider.icon(file_info)
            
            if not icon.isNull():
                pixmap = icon.pixmap(32, 32)
                if not pixmap.isNull():
                    return pixmap
        except Exception as e:
            print(f"Error extracting icon from {exe_path}: {e}")
        
        return None
    
    def update_results(self):
        """Aggiorna la lista dei risultati in base alla ricerca"""
        search_text = self.search_input.text().lower().strip()
        
        self.results_list.clear()
        self.filtered_indices = []

        temp_results = []  # (app_name, index, app_data)

        if not search_text:
            # Mostra tutte le app
            for i, app in enumerate(self.apps):
                temp_results.append((app["name"], i, app))
        else:
            # Filtra
            for i, app in enumerate(self.apps):
                app_name = app['name']
                if search_text in app_name.lower():
                    temp_results.append((app_name, i, app))

        # Ordina alfabeticamente
        temp_results.sort(key=lambda x: x[0].lower())

        # Aggiungi alla QListWidget dopo l'ordinamento con icone
        for name, original_index, app_data in temp_results:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, original_index)
            
            # ESTRAI ICONE DALL'EXE IN TEMPO REALE (come program_scanner)
            icon_loaded = False
            
            # Usa il campo 'path' per estrarre l'icona dall'exe
            if 'path' in app_data and app_data['path']:
                exe_path = app_data['path']
                
                # Pulisci il path da argomenti e virgolette
                if exe_path.startswith('"'):
                    # Path con virgolette: "C:\Program Files\App.exe" -arg
                    parts = exe_path.split('"')
                    if len(parts) >= 2:
                        exe_path = parts[1]
                elif ' -' in exe_path or ' /' in exe_path:
                    # Path con argomenti: C:\App.exe -arg
                    # Trova dove iniziano gli argomenti
                    for sep in [' -', ' /']:
                        if sep in exe_path:
                            exe_path = exe_path.split(sep)[0].strip()
                            break
                
                # Verifica che sia un exe valido
                if exe_path and os.path.exists(exe_path) and exe_path.lower().endswith('.exe'):
                    icon_pixmap = self._extract_icon_from_exe(exe_path)
                    
                    if icon_pixmap and not icon_pixmap.isNull():
                        scaled_icon = icon_pixmap.scaled(
                            32, 32,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        item.setIcon(QIcon(scaled_icon))
                        icon_loaded = True
            
            # Se non c'è icona, usa il placeholder
            if not icon_loaded:
                item.setText(f"🎮  {name}")
            
            self.results_list.addItem(item)
            self.filtered_indices.append(original_index)

        # Seleziona primo risultato
        if self.results_list.count() > 0:
            self.current_selection = 0
            self.results_list.setCurrentRow(0)

        # Nessun risultato
        if self.results_list.count() == 0:
            item = QListWidgetItem("❌  No apps found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results_list.addItem(item)
    
    def update_mode_indicator(self):
        """Aggiorna l'indicatore della modalità - COLORI UNIFORMATI"""
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
        """Cambia tra modalità digitazione e navigazione"""
        self.is_typing_mode = not self.is_typing_mode
        self.update_mode_indicator()
        
        if self.is_typing_mode:
            self.search_input.setFocus()
        else:
            self.results_list.setFocus()
    
    def navigate_up(self):
        """Naviga verso l'alto nei risultati"""
        if self.results_list.count() > 0:
            current = self.results_list.currentRow()
            prev_row = max(current - 1, 0)
            self.results_list.setCurrentRow(prev_row)
            # Auto-switch a navigation mode
            if self.is_typing_mode:
                self.is_typing_mode = False
                self.update_mode_indicator()
    
    def navigate_down(self):
        """Naviga verso il basso nei risultati"""
        if self.results_list.count() > 0:
            current = self.results_list.currentRow()
            next_row = min(current + 1, self.results_list.count() - 1)
            self.results_list.setCurrentRow(next_row)
            # Auto-switch a navigation mode
            if self.is_typing_mode:
                self.is_typing_mode = False
                self.update_mode_indicator()
    
    def launch_selected(self):
        """Lancia l'app selezionata"""
        if self.results_list.count() > 0 and self.filtered_indices:
            current_row = self.results_list.currentRow()
            if 0 <= current_row < len(self.filtered_indices):
                app_index = self.filtered_indices[current_row]
                self.app_selected.emit(app_index)
                self.close_search()
    
    def on_item_activated(self, item):
        """Gestisce il doppio click o Enter su un item"""
        if item and item.flags() & Qt.ItemFlag.ItemIsEnabled:
            app_index = item.data(Qt.ItemDataRole.UserRole)
            if app_index is not None:
                self.app_selected.emit(app_index)
                self.close_search()
    
    def handle_joypad_input(self, key_code):
        """Gestisce gli input dal joypad (chiamato dal parent)"""
        if key_code == Qt.Key.Key_Escape:
            self.close_search()
        elif key_code == Qt.Key.Key_Up:
            self.navigate_up()
        elif key_code == Qt.Key.Key_Down:
            self.navigate_down()
        elif key_code == Qt.Key.Key_Return or key_code == Qt.Key.Key_Enter:
            self.launch_selected()
        elif key_code == Qt.Key.Key_E:  # X button per cambio modalità
            self.switch_mode()
        elif key_code == Qt.Key.Key_Backspace:
            # Backspace in navigation mode torna a typing
            if not self.is_typing_mode:
                self.is_typing_mode = True
                self.search_input.setFocus()
                self.update_mode_indicator()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Gestisce gli input da tastiera"""
        key = event.key()
        
        # Esc chiude sempre
        if key == Qt.Key.Key_Escape:
            self.close_search()
            return
        
        # Tab cambia modalità
        if key == Qt.Key.Key_Tab:
            self.switch_mode()
            event.accept()
            return
        
        # Enter lancia l'app selezionata
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.launch_selected()
            return
        
        # Navigazione risultati (sempre attiva)
        if key == Qt.Key.Key_Down:
            self.navigate_down()
            event.accept()
            return
        
        if key == Qt.Key.Key_Up:
            self.navigate_up()
            event.accept()
            return
        
        # Backspace in navigation mode torna a typing mode
        if key == Qt.Key.Key_Backspace and not self.is_typing_mode:
            self.is_typing_mode = True
            self.search_input.setFocus()
            self.update_mode_indicator()
            # Lascia che il backspace venga processato normalmente
        
        # Qualsiasi altro carattere in navigation mode passa a typing mode
        if not self.is_typing_mode and event.text().isprintable():
            self.is_typing_mode = True
            self.search_input.setFocus()
            self.update_mode_indicator()
        
        super().keyPressEvent(event)
