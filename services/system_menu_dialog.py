from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton, QVBoxLayout


class SystemMenuDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        parent_rect = parent.geometry()
        dialog_width = 250
        dialog_height = 100
        self.setGeometry(
            parent_rect.width() - dialog_width - 40,
            parent_rect.height() - dialog_height - 40,
            dialog_width,
            dialog_height
        )
        self.current_index = 0
        self.buttons = []
        main_widget = QWidget()
        main_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 220);
                border-radius: 50px;
            }
        """)
        layout = QHBoxLayout(main_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        self.restart_btn = QPushButton("↻")
        self.restart_btn.setFixedSize(60, 60)
        self.restart_btn.setToolTip("Restart")
        self.buttons.append(("restart", self.restart_btn))
        layout.addWidget(self.restart_btn)
        self.shutdown_btn = QPushButton("⏻")
        self.shutdown_btn.setFixedSize(60, 60)
        self.shutdown_btn.setToolTip("Shutdown")
        self.buttons.append(("shutdown", self.shutdown_btn))
        layout.addWidget(self.shutdown_btn)
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(60, 60)
        self.close_btn.setToolTip("Close")
        self.buttons.append(("close", self.close_btn))
        layout.addWidget(self.close_btn)
        for action, btn in self.buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a2a2a;
                    color: white;
                    border: 3px solid #444;
                    border-radius: 30px;
                    font-size: 24px;
                }
                
                QPushButton:hover {
                        background-color: #3a3a3a;}
            """)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(main_widget)
        self.setLayout(dialog_layout)
        self.update_focus()
   
    def update_focus(self):
        for i, (action, btn) in enumerate(self.buttons):
            if i == self.current_index:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        color: #1a1a1a;
                        border: 4px solid white;
                        border-radius: 30px;
                        font-size: 24px;
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
                        border: 3px solid #444;
                        border-radius: 30px;
                        font-size: 24px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;}
                """)
   
    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            return
        key = event.key()
        if key == Qt.Key.Key_Right:
            self.current_index = (self.current_index + 1) % len(self.buttons)
            self.update_focus()
        elif key == Qt.Key.Key_Left:
            self.current_index = (self.current_index - 1) % len(self.buttons)
            self.update_focus()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            action = self.buttons[self.current_index][0]
            if action == "close":
                self.reject()
            else:
                self.selected_action = action
                self.accept()
        elif key == Qt.Key.Key_Escape or key == Qt.Key.Key_M:
            self.reject()
        else:
            super().keyPressEvent(event)
   
    def get_selected_action(self):
        return getattr(self, 'selected_action', 'close')

