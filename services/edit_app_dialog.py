from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QFileDialog, QDialog


class EditAppDialog(QDialog):
    def __init__(self, app_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit App")
        self.setModal(True)
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 10px; border-radius: 8px; font-size: 14px; }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        name_label = QLabel("App Name:")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setText(app_data.get('name', ''))
        layout.addWidget(self.name_input)
        exe_label = QLabel("Executable Path:")
        exe_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(exe_label)
        exe_container = QHBoxLayout()
        exe_container.setSpacing(10)
        self.exe_input = QLineEdit()
        self.exe_input.setText(app_data.get('path', ''))
        exe_container.addWidget(self.exe_input, 3)
        self.exe_button = QPushButton("Browse")
        self.exe_button.clicked.connect(self.browse_exe)
        exe_container.addWidget(self.exe_button, 1)
        layout.addLayout(exe_container)
        icon_label = QLabel("Icon Image (16:9 recommended):")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(icon_label)
        icon_container = QHBoxLayout()
        icon_container.setSpacing(10)
        self.icon_input = QLineEdit()
        self.icon_input.setText(app_data.get('icon', ''))
        icon_container.addWidget(self.icon_input, 3)
        self.icon_button = QPushButton("Browse")
        self.icon_button.clicked.connect(self.browse_icon)
        icon_container.addWidget(self.icon_button, 1)
        layout.addLayout(icon_container)
        layout.addSpacing(20)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        self.save_button = QPushButton("Save")
        self.save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.confirm_buttons = [self.save_button, self.cancel_button]
        self.confirm_index = [0]
        self.update_confirm_focus()
   
    def update_confirm_focus(self):
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;;
                        color: white;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                         }
                    QPushButton:hover { background-color: #3a3a3a; }    
                    
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2a2a2a;;
                        color: white;
                        border: 2px solid #444;
                        padding: 12px 30px;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                   QPushButton:hover { background-color: #3a3a3a; }    
                    
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
   
    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Executable", "", "Executables (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.exe_input.setText(file_path)
   
    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        if file_path:
            self.icon_input.setText(file_path)
   
    def get_app_data(self):
        return {
            'name': self.name_input.text(),
            'path': self.exe_input.text(),
            'icon': self.icon_input.text()
        }

