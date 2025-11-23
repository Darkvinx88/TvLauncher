from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QDialog, QLineEdit, QMessageBox, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QProgressBar, QProgressDialog
)

# === API KEY DIALOG ===
class ApiKeyDialog(QDialog):
    def __init__(self, current_key="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("SteamGridDB API Key")
        self.setModal(True)
        self.setFixedSize(600, 300)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a; }
            QLabel { color: white; font-size: 14px; }
            QLineEdit { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: 10px; 
                border-radius: 8px; 
                font-size: 14px; 
            }
            QPushButton { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                padding: 12px 30px; 
                border-radius: 8px; 
                font-size: 14px; 
                font-weight: bold; 
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("🔑 SteamGridDB API Key")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info text
        info = QLabel(
            "To automatically download 16:9 images:\n\n"
            "1. Go to steamgriddb.com\n"
            "2. Create a free account\n"
            "3. Go to Preferences → API\n"
            "4. Generate an API Key and paste it here"
        )
        info.setStyleSheet("color: #aaa; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # API Key input
        key_label = QLabel("API Key:")
        layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setText(current_key)
        self.key_input.setPlaceholderText("Paste your API here . . .")
        layout.addWidget(self.key_input)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Custom key handling
        self.confirm_buttons = [self.save_btn, self.cancel_btn]
        self.confirm_index = [0]
        self.update_confirm_focus()
    
    def update_confirm_focus(self):
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;

                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
    
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Left:
            self.confirm_index[0] = (self.confirm_index[0] - 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Right:
            self.confirm_index[0] = (self.confirm_index[0] + 1) % 2
            self.update_confirm_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.confirm_buttons[self.confirm_index[0]].click()
        elif key == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def get_api_key(self):
        return self.key_input.text().strip()

