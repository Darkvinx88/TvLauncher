"""
styles.py — TV Launcher Stylesheet Constants
=============================================
Tutte le stringhe CSS estratte da tvlauncher.py.
Le costanti statiche (senza scaling) sono stringhe dirette.
Le funzioni generano stili che dipendono da valori scalati a runtime.

USO:
    from modules.styles import Styles

    widget.setStyleSheet(Styles.MSGBOX)
    btn.setStyleSheet(Styles.menu_btn_normal(scale(2), scale(25), scale_font(24)))
"""


class Styles:

    
    # Generici / layout
    

    TRANSPARENT = "background-color: transparent;"

    OVERLAY_DIM = "background-color: rgba(0, 0, 0, 0.3);"

    SEPARATOR = "background-color: rgba(255,255,255,0.2); border: none;"

    EMPTY_LABEL = "color: #666; font-size: 18px;"

    
    # Orologio (header)
    

    @staticmethod
    def clock_time(font_size: int) -> str:
        return (
            f"color: rgba(255, 255, 255, 0.9); "
            f"font-size: {font_size}px; "
            f"font-weight: 700;"
        )

    @staticmethod
    def clock_date(font_size: int) -> str:
        return (
            f"color: rgba(255, 255, 255, 0.6); "
            f"font-size: {font_size}px; "
            f"font-weight: 500;"
        )

    
    # Settings button (⚙) — due varianti
    

    @staticmethod
    def settings_btn_standalone(border_radius: int, font_size: int) -> str:
        """Versione senza batteria: pulsante standalone con sfondo overlay."""
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
            }}
        """

    @staticmethod
    def settings_btn_in_pill(border_radius: int, font_size: int) -> str:
        """Versione con batteria: ingranaggio dentro la pill, sfondo trasparente."""
        return f"""
            QPushButton {{
                background-color: transparent;
                color: rgba(255, 255, 255, 0.8);
                border: none;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                color: white;
            }}
        """

    @staticmethod
    def pill_with_battery(border_radius: int) -> str:
        """Contenitore pill batteria + ingranaggio."""
        return f"""
            QWidget {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: {border_radius}px;
            }}
        """

    
    # Menu bar inferiore
    

    @staticmethod
    def menu_bar_container(border_radius: int) -> str:
        return f"""
            QWidget {{
                background-color: rgba(20, 20, 20, 0.6);
                border-radius: {border_radius}px;
            }}
        """

    @staticmethod
    def menu_btn_normal(border: int, border_radius: int,
                        font_size: int, weight: str = "500") -> str:
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.7);
                border: {border}px solid transparent;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
                font-weight: {weight};
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """

    @staticmethod
    def menu_btn_focused(border: int, border_radius: int, font_size: int) -> str:
        return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.95);
                color: #000000;
                border: {border}px solid white;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """

    
    # Istruzioni in basso
    

    @staticmethod
    def instructions(font_size: int) -> str:
        return (
            f"color: rgba(255, 255, 255, 0.3); "
            f"font-size: {font_size}px; "
            f"background: transparent;"
        )

    
    # AppTile
    

    @staticmethod
    def tile_image_normal(border_radius: int, font_size: int) -> str:
        return f"""
            QLabel {{
                background-color: #1a1a1a;
                border-radius: {border_radius}px;
                color: #cccccc;
                font-size: {font_size}px;
                font-weight: 600;
            }}
        """

    @staticmethod
    def tile_image_focused(border: int, border_radius: int, font_size: int) -> str:
        return f"""
            QLabel {{
                background-color: #1a1a1a;
                border: {border}px solid #ffffff;
                border-radius: {border_radius}px;
                color: #ffffff;
                font-size: {font_size}px;
                font-weight: 600;
            }}
        """

    @staticmethod
    def tile_name_normal(font_size: int) -> str:
        return f"""
            QLabel {{
                color: #999999;
                font-size: {font_size}px;
                background: transparent;
                border: none;
            }}
        """

    @staticmethod
    def tile_name_focused(font_size: int) -> str:
        return f"""
            QLabel {{
                color: #ffffff;
                font-size: {font_size}px;
                font-weight: 600;
            }}
        """

    
    # QMessageBox 
    

    MSGBOX = """
        QMessageBox {
            background-color: #1a1a1a;
            color: white;
        }
        QMessageBox QLabel {
            color: white;
            font-size: 14px;
            padding: 10px;
        }
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            padding: 10px 30px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
            border-color: #666;
        }
        QPushButton:pressed {
            background-color: #4a4a4a;
        }
    """

    @staticmethod
    def msgbox(font_size_label: int, font_size_btn: int,
               padding_v: int, padding_h: int,
               border_radius: int, min_width: int) -> str:
        return f"""
            QMessageBox {{
                background-color: #1a1a1a;
                color: white;
            }}
            QMessageBox QLabel {{
                color: white;
                font-size: {font_size_label}px;
                padding: 10px;
            }}
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size_btn}px;
                font-weight: bold;
                min-width: {min_width}px;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
                border-color: #666;
            }}
            QPushButton:pressed {{
                background-color: #4a4a4a;
            }}
        """

    
    # QProgressDialog
    

    PROGRESS_DIALOG = """
        QProgressDialog {
            background-color: #1a1a1a;
            color: white;
        }
        QProgressDialog QLabel {
            color: white;
            font-size: 14px;
        }
        QProgressBar {
            background-color: #2a2a2a;
            color: white;
            border: 1px solid #444;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #3a3a3a;
            border-radius: 5px;
        }
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            padding: 8px 20px;
            border-radius: 8px;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #3a3a3a; }
    """

    @staticmethod
    def progress_dialog(font_size_label: int, font_size_btn: int,
                        padding_v: int, padding_h: int, border_radius: int) -> str:
        return f"""
            QProgressDialog {{
                background-color: #1a1a1a;
                color: white;
            }}
            QProgressDialog QLabel {{
                color: white;
                font-size: {font_size_label}px;
            }}
            QProgressBar {{
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #3a3a3a;
                border-radius: 5px;
            }}
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size_btn}px;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """

    
    # Confirm dialog (confirm_action / confirm_exit_launcher)
    

    @staticmethod
    def confirm_dialog(font_size_label: int, font_size_btn: int,
                       padding_v: int, padding_h: int, border_radius: int) -> str:
        return f"""
            QDialog {{ background-color: #1a1a1a; }}
            QLabel {{ color: white; font-size: {font_size_label}px; }}
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size_btn}px;
                font-weight: bold;
            }}
            QPushButton:focus {{
                background-color: #3a3a3a;
                border: 3px solid white;
            }}
        """

    @staticmethod
    def confirm_btn_focused(font_size: int, padding_v: int,
                            padding_h: int, border_radius: int) -> str:
        return f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 3px solid white;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """

    @staticmethod
    def confirm_btn_normal(font_size: int, padding_v: int,
                           padding_h: int, border_radius: int) -> str:
        return f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 2px solid #444;
                padding: {padding_v}px {padding_h}px;
                border-radius: {border_radius}px;
                font-size: {font_size}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #3a3a3a; }}
        """

    # Alias statici — usati da moduli esterni che non passano scaling
    CONFIRM_DIALOG = """
        QDialog { background-color: #1a1a1a; }
        QLabel { color: white; font-size: 16px; }
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:focus {
            background-color: #3a3a3a;
            border: 3px solid white;
        }
    """

    CONFIRM_BTN_FOCUSED = """
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 3px solid white;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #3a3a3a; }
    """

    CONFIRM_BTN_NORMAL = """
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 2px solid #444;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #3a3a3a; }
    """

    
    # Remove app messagebox 
    

    MSGBOX_REMOVE = """
        QMessageBox {
            background-color: #2b2b2b;
            color: #ffffff;
            padding: 15px 30px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #3a3a3a;
            color: #ffffff;
            padding: 10px 40px;
            border-radius: 8px;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #505050; }
        QPushButton:pressed { background-color: #1e90ff; }
    """
