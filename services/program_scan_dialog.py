from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QListWidget, QPushButton, \
    QListWidgetItem

from services.program_scanner import ProgramScanner


class ProgramScanDialog(QDialog):
    def __init__(self, image_manager=None, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.setWindowTitle("Scan Installed Programs")
        self.setModal(True)
        self.setFixedSize(700, 650)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 8px; border-radius: 8px; font-size: 14px; }
            QListWidget { background-color: #2a2a2a; color: white; border: 2px solid #444; border-radius: 8px; font-size: 14px; padding: 5px; }
            QListWidget::item { padding: 8px; border-radius: 4px; }
            QListWidget::item:selected { background-color: #3a3a3a; }
            QListWidget::item:hover { background-color: #333; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #3a3a3a;} 
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        self.title_label = QLabel("Scanning Installed Programs in Progress...")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Progress label
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 12px;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

        # Barra di ricerca
        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by Name...")
        self.search_input.textChanged.connect(self.filter_list)
        search_box.addWidget(self.search_input)
        layout.addLayout(search_box)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)

        self.info_label = QLabel("Select which programs to add (Ctrl/Shift for multiple)")
        self.info_label.setStyleSheet("color: #aaa; font-size: 13px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add selected")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.list_widget.itemSelectionChanged.connect(self.update_add_button)

        # Avvia scansione SENZA ImageManager
        self.scanner = ProgramScanner()
        self.scanner.program_found.connect(self.add_item)
        self.scanner.scan_complete.connect(self.scan_done)
        self.scanner.progress_update.connect(self.update_progress)
        self.scanner.start()

    def add_item(self, data):
        item = QListWidgetItem(f"📦 {data['name']}")
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.list_widget.addItem(item)
        self.title_label.setText(f"Found {self.list_widget.count()} programs")

    def scan_done(self):
        self.title_label.setText(f"Scan completed — Found {self.list_widget.count()} programs")
        self.progress_label.setText("")
        self.list_widget.sortItems(Qt.SortOrder.AscendingOrder)
    
    def update_progress(self, message):
        self.progress_label.setText(message)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def update_add_button(self):
        selected = len(self.list_widget.selectedItems())
        self.add_btn.setEnabled(selected > 0)
        self.info_label.setText(f"{selected} selected" if selected > 0 else "Select the programs to add")

    def get_selected(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.list_widget.selectedItems()]
