import os
import json
import time
import hashlib
import secrets
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QLineEdit, QComboBox,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QPainter, QBrush


PIN_LENGTH = 4

SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your primary school?",
    "What was your childhood best friend's name?",
    "What is your favourite childhood movie?",
]

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 30


# Security 


def _hash_value(value: str, salt: str) -> str:
    combined = (salt + value.strip().lower()).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()

def _generate_salt() -> str:
    return secrets.token_hex(16)


# Styles


def _base_style(scale_fn) -> str:
    s = scale_fn
    return f"""
        QDialog {{
            background-color: transparent;
        }}
        #card {{
            background-color: #1a1a1a;
            border: 2px solid #444;
            border-radius: {s(18)}px;
        }}
        QLabel {{
            color: white;
            background: transparent;
        }}
        QPushButton {{
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            border-radius: {s(10)}px;
            font-size: {s(16)}px;
            font-weight: 600;
        }}
        QLineEdit {{
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            border-radius: {s(8)}px;
            padding: {s(8)}px {s(12)}px;
            font-size: {s(16)}px;
        }}
        QComboBox {{
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            border-radius: {s(8)}px;
            padding: {s(6)}px {s(10)}px;
            font-size: {s(14)}px;
        }}
    """

def _numpad_btn_style(size: int, font_size: int, mode="normal") -> str:
    radius = size // 2
    if mode == "focused":
        return f"QPushButton {{ background-color: #3a3a3a; color: white; border: 3px solid white; border-radius: {radius}px; font-size: {font_size}px; font-weight: 700; }}"
    if mode == "backspace":
        return f"QPushButton {{ background-color: #2a2a2a; color: #ff6060; border: 2px solid #444; border-radius: {radius}px; font-size: {font_size}px; font-weight: 600; }}"
    return f"QPushButton {{ background-color: #2a2a2a; color: white; border: 2px solid #444; border-radius: {radius}px; font-size: {font_size}px; font-weight: 600; }}"


# UI 


class NumPadWidget(QWidget):
    digit_entered = pyqtSignal(str)
    backspace     = pyqtSignal()
    confirmed     = pyqtSignal()
    LAYOUT = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], ["⌫", "0", "OK"]]

    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self._focus_row, self._focus_col = 1, 1 
        self._buttons = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(self.scaling.scale(10))
        layout.setContentsMargins(0, 0, 0, 0)
        btn_size, font_size = self.scaling.scale(72), self.scaling.scale(22)

        for r, row in enumerate(self.LAYOUT):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(self.scaling.scale(10))
            btn_row = []
            for c, label in enumerate(row):
                btn = QPushButton(label)
                btn.setFixedSize(btn_size, btn_size)
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.clicked.connect(self._make_click_handler(label))
                row_layout.addWidget(btn)
                btn_row.append(btn)
            self._buttons.append(btn_row)
            layout.addLayout(row_layout)
        self._update_focus()

    def _make_click_handler(self, label):
        return lambda: self._handle_label(label)

    def _handle_label(self, label: str):
        if label == "⌫": self.backspace.emit()
        elif label == "OK": self.confirmed.emit()
        else: self.digit_entered.emit(label)

    def _update_focus(self):
        s, f = self.scaling.scale(72), self.scaling.scale(22)
        for r, row in enumerate(self._buttons):
            for c, btn in enumerate(row):
                mode = "normal"
                if r == self._focus_row and c == self._focus_col: mode = "focused"
                elif self.LAYOUT[r][c] == "⌫": mode = "backspace"
                btn.setStyleSheet(_numpad_btn_style(s, f, mode))

    def move_focus(self, dr, dc):
        self._focus_row = (self._focus_row + dr) % 4
        self._focus_col = (self._focus_col + dc) % 3
        self._update_focus()

    def press_focused(self):
        self._handle_label(self.LAYOUT[self._focus_row][self._focus_col])

class PinDotsWidget(QWidget):
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling, self._count = scaling, 0
        self.setFixedHeight(self.scaling.scale(28))

    def set_count(self, n):
        self._count = n
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        dot_r, spacing = self.scaling.scale(10), self.scaling.scale(24)
        total_w = PIN_LENGTH * dot_r * 2 + (PIN_LENGTH - 1) * (spacing - dot_r * 2)
        start_x, y = (self.width() - total_w) // 2, self.height() // 2
        for i in range(PIN_LENGTH):
            x = start_x + i * spacing + dot_r
            painter.setBrush(QBrush(QColor("#4a9eff" if i < self._count else "#2a2a2a")))
            painter.setPen(QColor("white" if i < self._count else "#444444"))
            painter.drawEllipse(x - dot_r, y - dot_r, dot_r * 2, dot_r * 2)


# Dialogs


class PinEntryDialog(QDialog):
    def __init__(self, manager, parent=None, mode="verify", scaling=None):
        super().__init__(parent)
        self.manager, self.mode, self.scaling = manager, mode, scaling or _FallbackScaling()
        self._pin, self._attempts, self._locked_until = "", 0, 0.0
        
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.scaling.scale(420), self.scaling.scale(680))
        self.setStyleSheet(_base_style(self.scaling.scale))
        self._build_ui()
        self._center()

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    def _build_ui(self):
        s = self.scaling
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        card = QWidget(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setContentsMargins(s.scale(30), s.scale(30), s.scale(30), s.scale(30)); cl.setSpacing(s.scale(10))

        icon = QLabel("🔒"); icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"font-size: {s.scale(36)}px;"); cl.addWidget(icon)

        title = QLabel("Parental Control"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: {s.scale(20)}px; font-weight: 700; color: white;"); cl.addWidget(title)

        self.subtitle = QLabel("Enter your PIN to continue"); self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet(f"color: rgba(255,255,255,0.5); font-size: {s.scale(13)}px;"); cl.addWidget(self.subtitle)

        self.dots = PinDotsWidget(s); cl.addWidget(self.dots)

        self.error_label = QLabel(""); self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet(f"color: #ff6060; font-size: {s.scale(12)}px; min-height: {s.scale(15)}px;"); cl.addWidget(self.error_label)

        self.numpad = NumPadWidget(s)
        self.numpad.digit_entered.connect(self._on_digit); self.numpad.backspace.connect(self._on_backspace); self.numpad.confirmed.connect(self._on_confirm)
        cl.addWidget(self.numpad, alignment=Qt.AlignmentFlag.AlignCenter)

        cl.addSpacing(s.scale(10)) 

        self.recovery_btn = QPushButton("Forgot your PIN?")
        self.recovery_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus) 
        self.recovery_btn.setStyleSheet(f"QPushButton {{ color: #4a9eff; background: transparent; border: none; font-size: {s.scale(13)}px; text-decoration: underline; }}")
        self.recovery_btn.clicked.connect(self._open_recovery); cl.addWidget(self.recovery_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.mode == "verify":
            cl.addSpacing(s.scale(5))
            cancel = QPushButton("Cancel"); cancel.setFixedHeight(s.scale(44))
            cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cancel.clicked.connect(self.reject); cl.addWidget(cancel)

        outer.addWidget(card)

    def _on_digit(self, digit):
        if len(self._pin) < PIN_LENGTH and time.time() >= self._locked_until:
            self._pin += digit; self.dots.set_count(len(self._pin))
            if len(self._pin) == PIN_LENGTH: QTimer.singleShot(120, self._on_confirm)

    def _on_backspace(self): self._pin = self._pin[:-1]; self.dots.set_count(len(self._pin))

    def _on_confirm(self):
        if self.manager.verify_pin(self._pin): self.accept()
        else:
            self._attempts += 1; self._pin = ""; self.dots.set_count(0)
            if self._attempts >= MAX_ATTEMPTS: self._start_lockout()
            else: self.error_label.setText(f"Wrong PIN. {MAX_ATTEMPTS - self._attempts} left.")

    def _start_lockout(self):
        self._locked_until = time.time() + LOCKOUT_SECONDS; self._update_lockout()
        self.t = QTimer(self); self.t.timeout.connect(self._update_lockout); self.t.start(1000)

    def _update_lockout(self):
        rem = int(self._locked_until - time.time())
        if rem > 0: self.error_label.setText(f"Wait {rem}s.")
        else: self.t.stop(); self.error_label.setText("")

    def _open_recovery(self):
        """Nasconde il keypad e apre la procedura di recupero"""
        self.hide()
        recovery = PinRecoveryDialog(self.manager, self, scaling=self.scaling, boot_mode=(self.mode == "boot"))
        if recovery.exec() == QDialog.DialogCode.Accepted:
            setup = PinSetupDialog(self.manager, self, scaling=self.scaling, is_change=True)
            if setup.exec() == QDialog.DialogCode.Accepted:
                self.accept()
                return
        # In boot: se l'utente non completa il recovery → chiude il launcher
        if self.mode == "boot":
            self.reject()
        else:
            # In verify: chiude il PIN dialog e restituisce il focus al launcher
            self.reject()
            if self.parent():
                self.parent().raise_()
                self.parent().activateWindow()
                self.parent().setFocus()

    def keyPressEvent(self, e):
        if e.isAutoRepeat(): return
        k = e.key()
        if k == Qt.Key.Key_Up: self.numpad.move_focus(-1, 0)
        elif k == Qt.Key.Key_Down: self.numpad.move_focus(1, 0)
        elif k == Qt.Key.Key_Left: self.numpad.move_focus(0, -1)
        elif k == Qt.Key.Key_Right: self.numpad.move_focus(0, 1)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter): self.numpad.press_focused()
        elif k == Qt.Key.Key_Escape and self.mode == "verify": self.reject()

class PinRecoveryDialog(QDialog):
    def __init__(self, manager, parent=None, scaling=None, boot_mode=False):
        super().__init__(parent)
        self.manager, self.scaling = manager, scaling or _FallbackScaling()
        self.boot_mode = boot_mode
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.scaling.scale(420), self.scaling.scale(400))
        self.setStyleSheet(_base_style(self.scaling.scale))
        self._build_ui(); self._center()

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    def _build_ui(self):
        s = self.scaling
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        card = QWidget(); card.setObjectName("card")
        layout = QVBoxLayout(card); layout.setContentsMargins(s.scale(30), s.scale(30), s.scale(30), s.scale(30)); layout.setSpacing(s.scale(16))
        title = QLabel("🔑 Recovery"); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size: {s.scale(20)}px; font-weight: 700; color: white;"); layout.addWidget(title)
        q_lbl = QLabel(self.manager.security_question); q_lbl.setWordWrap(True); q_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        q_lbl.setStyleSheet(f"color: rgba(255,255,255,0.6); font-size: {s.scale(14)}px;"); layout.addWidget(q_lbl)
        self.answer_input = QLineEdit(); self.answer_input.setPlaceholderText("Your answer…")
        self.answer_input.setFixedHeight(s.scale(48)); layout.addWidget(self.answer_input)
        self.error_lbl = QLabel(""); self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.error_lbl.setStyleSheet("color: #ff6060;")
        layout.addWidget(self.error_lbl)
        btns = QHBoxLayout(); btns.setSpacing(s.scale(10))
        
        cancel_label = "Exit" if self.boot_mode else "Cancel"
        self.c_btn = QPushButton(cancel_label); self.c_btn.setFixedHeight(s.scale(48))
        self.c_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.c_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton("Confirm"); self.ok_btn.setFixedHeight(s.scale(48))
        self.ok_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ok_btn.setStyleSheet("QPushButton { background-color: #3a3a3a; border: 2px solid white; }")
        self.ok_btn.clicked.connect(self._verify)
        btns.addWidget(self.c_btn); btns.addWidget(self.ok_btn); layout.addLayout(btns)
        outer.addWidget(card); self.answer_input.setFocus()
        self.answer_input.installEventFilter(self)
        # Tieni traccia dei widget navigabili con frecce 
        self._focus_widgets = [self.answer_input, self.ok_btn, self.c_btn]
        self._focus_idx = 0

    def _verify(self):
        if self.manager.verify_security_answer(self.answer_input.text()): self.accept()
        else: self.error_lbl.setText("Incorrect answer.")

    def eventFilter(self, obj, e):
        """Intercetta Left/Right sul QLineEdit per navigare tra i bottoni."""
        if obj is self.answer_input and e.type() == e.Type.KeyPress:
            k = e.key()
            if k == Qt.Key.Key_Right:
                
                if self._focus_idx >= 1 or self.answer_input.cursorPosition() == len(self.answer_input.text()):
                    self._focus_idx = 1 if self._focus_idx != 1 else 1
                    self._update_focus()
                    return True
            elif k == Qt.Key.Key_Left:
                if self._focus_idx >= 1:
                    
                    self._focus_idx = 2 if self._focus_idx == 1 else 0
                    self._update_focus()
                    return True
                elif self.answer_input.cursorPosition() == 0:
                    
                    self._focus_idx = 2
                    self._update_focus()
                    return True
            elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self._focus_idx == 2: self.reject()
                else: self._verify()
                return True
        return super().eventFilter(obj, e)

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)

    def _update_focus(self):
        
        self.answer_input.setFocus()
        for i, widget in enumerate(self._focus_widgets):
            if isinstance(widget, QPushButton):
                widget.setStyleSheet("QPushButton { border: 2px solid white; }" if i == self._focus_idx else "")
            elif isinstance(widget, QLineEdit):
                
                widget.setStyleSheet("QLineEdit { border: 2px solid white; }" if self._focus_idx == 0 else "")

class PinSetupDialog(QDialog):
    def __init__(self, manager, parent=None, scaling=None, is_change=False):
        super().__init__(parent)
        self.manager, self.scaling, self.is_change = manager, scaling or _FallbackScaling(), is_change
        self._step, self._first_pin, self._new_pin = 1, "", ""
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.scaling.scale(420), self.scaling.scale(680))
        self.setStyleSheet(_base_style(self.scaling.scale))
        self._build_ui(); self._center()

    def _center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    def _build_ui(self):
        s = self.scaling
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        card = QWidget(); card.setObjectName("card")
        cl = QVBoxLayout(card); cl.setContentsMargins(s.scale(30), s.scale(30), s.scale(30), s.scale(30)); cl.setSpacing(s.scale(10))
        icon = QLabel("🛡️"); icon.setAlignment(Qt.AlignmentFlag.AlignCenter); icon.setStyleSheet(f"font-size: {s.scale(32)}px;"); cl.addWidget(icon)
        self.title_lbl = QLabel("New PIN"); self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet(f"font-size: {s.scale(20)}px; font-weight: 700; color: white;"); cl.addWidget(self.title_lbl)
        self.sub_lbl = QLabel("Enter a 4-digit PIN"); self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.sub_lbl.setStyleSheet(f"color: rgba(255,255,255,0.5);"); cl.addWidget(self.sub_lbl)
        self.dots = PinDotsWidget(s); cl.addWidget(self.dots)
        self.error_lbl = QLabel(""); self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); self.error_lbl.setStyleSheet("color: #ff6060;"); cl.addWidget(self.error_lbl)
        self.numpad = NumPadWidget(s)
        self.numpad.digit_entered.connect(self._on_digit); self.numpad.backspace.connect(self._on_backspace); self.numpad.confirmed.connect(self._on_confirm)
        cl.addWidget(self.numpad, alignment=Qt.AlignmentFlag.AlignCenter)
        self.question_widget = QWidget(); ql = QVBoxLayout(self.question_widget); ql.setSpacing(s.scale(8))
        self.question_combo = QComboBox(); [self.question_combo.addItem(q) for q in SECURITY_QUESTIONS]
        self.answer_input = QLineEdit(); self.answer_input.setPlaceholderText("Secret answer…")
        self.save_btn = QPushButton("Save PIN"); self.save_btn.setFixedHeight(s.scale(48)); self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.save_btn.clicked.connect(self._save_pin)
        ql.addWidget(QLabel("Security Question")); ql.addWidget(self.question_combo); ql.addWidget(QLabel("Your Answer")); ql.addWidget(self.answer_input); ql.addWidget(self.save_btn)
        self.question_widget.setVisible(False); cl.addWidget(self.question_widget)
        self.cancel_btn = QPushButton("Cancel"); self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus); self.cancel_btn.setStyleSheet("background: transparent; color: gray; border: none; font-size: 13px;"); self.cancel_btn.clicked.connect(self.reject); cl.addWidget(self.cancel_btn)
        outer.addWidget(card)

    def _on_digit(self, digit):
        if len(self._new_pin) < PIN_LENGTH:
            self._new_pin += digit; self.dots.set_count(len(self._new_pin))
            if len(self._new_pin) == PIN_LENGTH: QTimer.singleShot(120, self._on_confirm)
    def _on_backspace(self): self._new_pin = self._new_pin[:-1]; self.dots.set_count(len(self._new_pin))
    def _on_confirm(self):
        if self._step == 1:
            self._first_pin, self._new_pin, self._step = self._new_pin, "", 2
            self.title_lbl.setText("Confirm PIN"); self.dots.set_count(0)
        elif self._step == 2:
            if self._new_pin == self._first_pin:
                self._step = 3; self.numpad.hide(); self.dots.hide(); self.sub_lbl.hide()
                self.title_lbl.setText("Security Question"); self.question_widget.show(); self.answer_input.setFocus()
            else:
                self._new_pin, self._step = "", 1; self.title_lbl.setText("New PIN"); self.dots.set_count(0); self.error_lbl.setText("PINs mismatch.")
    def _save_pin(self):
        if self.answer_input.text().strip():
            self.manager.set_pin(self._first_pin, self.question_combo.currentIndex(), self.answer_input.text().strip())
            self.accept()
        else:
            self.error_lbl.setText("Answer cannot be empty.")

    def keyPressEvent(self, e):
        if e.isAutoRepeat(): return
        if self._step < 3:
            k = e.key()
            if k == Qt.Key.Key_Up: self.numpad.move_focus(-1, 0)
            elif k == Qt.Key.Key_Down: self.numpad.move_focus(1, 0)
            elif k == Qt.Key.Key_Left: self.numpad.move_focus(0, -1)
            elif k == Qt.Key.Key_Right: self.numpad.move_focus(0, 1)
            elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter): self.numpad.press_focused()
            elif k == Qt.Key.Key_Escape: self.reject()
        else:
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter): self._save_pin()
            else: super().keyPressEvent(e)


# Manager & integrazione


class ParentalControlManager:
    def __init__(self, user_data_dir: Path):
        self.config_path = user_data_dir / "parental_control.json"; self._data = self._load()
    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f: return json.load(f)
            except Exception as e:
                print(f"[ParentalControl] Warning: could not read config ({e}), using defaults.")
        return {"enabled": False, "pin_hash": "", "pin_salt": "", "security_question_index": 0, "security_answer_hash": "", "security_answer_salt": ""}
    def _save(self):
        with open(self.config_path, "w") as f: json.dump(self._data, f, indent=2)
    @property
    def is_enabled(self): return self._data.get("enabled", False)
    @property
    def is_configured(self): return bool(self._data.get("pin_hash", ""))
    @property
    def security_question(self): return SECURITY_QUESTIONS[self._data.get("security_question_index", 0)]
    def set_pin(self, pin, q_idx, ans):
        p_salt, a_salt = _generate_salt(), _generate_salt()
        self._data.update({"pin_hash": _hash_value(pin, p_salt), "pin_salt": p_salt, "security_question_index": q_idx, "security_answer_hash": _hash_value(ans, a_salt), "security_answer_salt": a_salt, "enabled": True})
        self._save()
    def disable(self): self._data["enabled"] = False; self._save()
    def verify_pin(self, pin): return _hash_value(pin, self._data.get("pin_salt", "")) == self._data.get("pin_hash", "")
    def verify_security_answer(self, ans): return _hash_value(ans, self._data.get("security_answer_salt", "")) == self._data.get("security_answer_hash", "")
    def check_boot_lock(self, parent_widget, scaling=None, launcher=None) -> bool:
        if not self.is_enabled or not self.is_configured: return True
        _launcher = launcher or parent_widget
        if _launcher is not None:
            try: _launcher.parental_control_dialog_active = True
            except: pass
        result = PinEntryDialog(self, parent_widget, mode="boot", scaling=scaling).exec() == QDialog.DialogCode.Accepted
        if _launcher is not None:
            try: _launcher.parental_control_dialog_active = False
            except: pass
        return result

class _FallbackScaling:
    def scale(self, v): return v

def integrate_parental_control(launcher, user_data_dir: Path = None):
    if user_data_dir is None:
        # Windows: APPDATA, Linux/Mac: XDG_CONFIG_HOME o ~/.config
        if os.name == 'nt':
            user_data_dir = Path(os.environ.get("APPDATA", Path.home())) / "TVLauncher"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME", "")
            user_data_dir = (Path(xdg) if xdg else Path.home() / ".config") / "TVLauncher"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    launcher.parental_control = ParentalControlManager(user_data_dir)
    launcher.parental_control_dialog_active = False

    def _set_pc_active(val: bool):
        launcher.parental_control_dialog_active = val

    def _exec_pc(dialog):
        """Esegue un dialog PC settando e resettando il flag sul launcher."""
        _set_pc_active(True)
        result = dialog.exec()
        _set_pc_active(False)
        return result

    def open_parental_control_settings():
        mgr, s = launcher.parental_control, launcher.scaling
        if mgr.is_configured and mgr.is_enabled:
            if _exec_pc(PinEntryDialog(mgr, launcher, mode="verify", scaling=s)) != QDialog.DialogCode.Accepted: return
        if mgr.is_configured:
            menu = QDialog(launcher)
            menu.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint); menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            menu.setFixedSize(s.scale(420), s.scale(320)); menu.setStyleSheet(_base_style(s.scale))
            outer = QVBoxLayout(menu); outer.setContentsMargins(0, 0, 0, 0)
            card = QWidget(); card.setObjectName("card"); outer.addWidget(card)
            layout = QVBoxLayout(card); layout.setContentsMargins(s.scale(24), s.scale(24), s.scale(24), s.scale(24)); layout.setSpacing(s.scale(12))
            lbl = QLabel("🛡️ Parental Control active"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); lbl.setStyleSheet(f"font-size: {s.scale(18)}px; font-weight: 700;"); layout.addWidget(lbl)
            def _btn(text, color="#2a2a2a", t_color="white"):
                b = QPushButton(text); b.setFixedHeight(s.scale(50)); b.setStyleSheet(f"QPushButton {{ background-color: {color}; color: {t_color}; border: 1px solid #444; }}"); layout.addWidget(b); return b
            _btn("Change PIN").clicked.connect(lambda: (menu.done(1)))
            _btn("Disable Parental Control", "#2a1a1a", "#ff8080").clicked.connect(lambda: (menu.done(2)))
            _btn("Cancel").clicked.connect(menu.reject)
            res = _exec_pc(menu)
            if res == 1: _exec_pc(PinSetupDialog(mgr, launcher, scaling=s, is_change=True))
            elif res == 2: mgr.disable()
        else: _exec_pc(PinSetupDialog(mgr, launcher, scaling=s))

    launcher.open_parental_control_settings = open_parental_control_settings