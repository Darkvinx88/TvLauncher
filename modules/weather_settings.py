from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QLineEdit, QComboBox, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from pathlib import Path


class WeatherSettingsDialog(QDialog):
    """Dialog per configurare le impostazioni meteo (senza API key!)"""
    
    def __init__(self, launcher, scaling, parent=None):
        super().__init__(parent)
        self.launcher = launcher
        self.scaling = scaling
        
        # Carica configurazione attuale
        self.load_current_config()
        
        self.setWindowTitle("Weather Settings")
        self.setModal(True)
        self.setFixedSize(self.scaling.scale(600), self.scaling.scale(632))
        
        
        self.setStyleSheet("""
            QDialog { 
                background-color: #1a1a1a; 
            }
        """)
        
        self.init_ui()
        
        # Navigazione con tastiera
        self.confirm_buttons = [self.save_btn, self.cancel_btn]
        self.confirm_index = [0]
        self.update_confirm_focus()
    
    def load_current_config(self):
        """Carica la configurazione corrente dal launcher.config_data"""
        
        self.current_config = {
            'city': 'Milan',
            'country_code': 'IT',
            'units': 'metric',
        }
        
        # Se il launcher ha config_data, usa quei valori
        if hasattr(self.launcher, 'config_data') and self.launcher.config_data:
            self.current_config['city'] = self.launcher.config_data.get('weather_city', 'Milan')
            self.current_config['country_code'] = self.launcher.config_data.get('weather_country_code', 'IT')
            self.current_config['units'] = self.launcher.config_data.get('weather_units', 'metric')

    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(self.scaling.scale(25))
        layout.setContentsMargins(
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30), 
            self.scaling.scale(30)
        )
        
        
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
                padding: {self.scaling.scale(20)}px;
            }}
        """)
        header_layout = QVBoxLayout(header_widget)
        header_layout.setSpacing(self.scaling.scale(10))
        
        title = QLabel("🌤️ Weather Configuration")
        title.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(20)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Powered by Open-Meteo")
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: #4a9eff;
                font-size: {self.scaling.scale_font(13)}px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_widget)

        # === FORM CONTAINER ===
        form_container = QWidget()
        form_container.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
            }}
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(self.scaling.scale(5))
        form_layout.setContentsMargins(
            self.scaling.scale(20),
            self.scaling.scale(20),
            self.scaling.scale(20),
            self.scaling.scale(20)
        )

        field_h = self.scaling.scale(38)
        label_style = f"""
            QLabel {{
                color: #aaaaaa;
                font-size: {self.scaling.scale_font(11)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """
        input_style = f"""
            QLineEdit {{
                background-color: #1a1a1a;
                color: white;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(6)}px;
                font-size: {self.scaling.scale_font(14)}px;
                padding-left: {self.scaling.scale(10)}px;
                padding-right: {self.scaling.scale(10)}px;
            }}
            QLineEdit:focus {{
                border: 2px solid #4a9eff;
            }}
        """

        # === CITY INPUT ===
        city_label = QLabel("📍 CITY")
        city_label.setStyleSheet(label_style)
        form_layout.addWidget(city_label)

        self.city_input = QLineEdit()
        self.city_input.setFixedHeight(field_h)
        self.city_input.setText(self.current_config['city'])
        self.city_input.setPlaceholderText("e.g., Milan, London, Tokyo...")
        self.city_input.setStyleSheet(input_style)
        form_layout.addWidget(self.city_input)

        form_layout.addSpacing(self.scaling.scale(28))

        # === COUNTRY CODE INPUT ===
        country_label = QLabel("🌍 COUNTRY CODE (optional, e.g. IT, US, GB)")
        country_label.setStyleSheet(label_style)
        form_layout.addWidget(country_label)

        self.country_input = QLineEdit()
        self.country_input.setFixedHeight(field_h)
        self.country_input.setText(self.current_config['country_code'])
        self.country_input.setPlaceholderText("e.g., IT, US, GB, JP...")
        self.country_input.setMaxLength(2)
        self.country_input.setStyleSheet(input_style)
        form_layout.addWidget(self.country_input)

        form_layout.addSpacing(self.scaling.scale(28))

        # === UNITS COMBO ===
        units_label = QLabel("🌡️ TEMPERATURE UNITS")
        units_label.setStyleSheet(label_style)
        form_layout.addWidget(units_label)

        self.units_combo = QComboBox()
        self.units_combo.setFixedHeight(field_h)
        self.units_combo.addItem("Celsius (°C)", "metric")
        self.units_combo.addItem("Fahrenheit (°F)", "imperial")

        # Imposta l'unità corrente
        current_units = self.current_config['units']
        index = 0 if current_units == "metric" else 1
        self.units_combo.setCurrentIndex(index)

        self.units_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: #1a1a1a;
                color: white;
                border: 2px solid #444;
                border-radius: {self.scaling.scale(6)}px;
                font-size: {self.scaling.scale_font(14)}px;
                padding-left: {self.scaling.scale(10)}px;
            }}
            QComboBox:focus {{
                border: 2px solid #4a9eff;
            }}
            QComboBox::drop-down {{
                border: none;
                width: {self.scaling.scale(30)}px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: {self.scaling.scale(10)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #1a1a1a;
                color: white;
                selection-background-color: #4a9eff;
                border: 2px solid #444;
            }}
        """)
        form_layout.addWidget(self.units_combo)
        form_layout.addSpacing(self.scaling.scale(14))

        layout.addWidget(form_container)
        
        # === INFO FOOTER ===
        info_footer = QLabel("Weather updates automatically every 30 minutes")
        info_footer.setStyleSheet(f"""
            QLabel {{
                color: #888;
                font-size: {self.scaling.scale_font(12)}px;
                background: transparent;
                border: none;
                padding: {self.scaling.scale(10)}px;
            }}
        """)
        info_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_footer)
        
        layout.addStretch()
        
        # === BUTTONS (stile KeyRemapper) ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(self.scaling.scale(15))
        
        self.save_btn = QPushButton("💾 Save and Apply")
        self.save_btn.setFixedHeight(self.scaling.scale(50))
        self.save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("✖ Cancel")
        self.cancel_btn.setFixedHeight(self.scaling.scale(50))
        self.cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def save_settings(self):
        """Salva le impostazioni meteo"""
        city = self.city_input.text().strip()
        country_code = self.country_input.text().strip().upper()
        units = self.units_combo.currentData()
        
        # Validazione
        if not city:
            QMessageBox.warning(
                self, 
                "Missing Information", 
                "Please enter a city name."
            )
            return
        
        # Debug: controlla se launcher è valido
        if not self.launcher:
            print("❌ ERROR: self.launcher is None!")
            QMessageBox.critical(
                self,
                "Error",
                "Internal error: launcher reference is None.\nPlease restart the launcher."
            )
            return
        
       
        # Aggiorna config_data
        self.launcher.config_data['weather_city'] = city
        self.launcher.config_data['weather_country_code'] = country_code
        self.launcher.config_data['weather_units'] = units
        
        # Applica la configurazione al widget PRESERVANDO LA VISIBILITÀ
        if hasattr(self.launcher, 'weather_widget') and self.launcher.weather_widget:
            # Salva lo stato di visibilità corrente
            was_visible = self.launcher.weather_widget.isVisible()
            
            # Applica la nuova configurazione
            self.launcher.weather_widget.set_location(city, country_code)
            self.launcher.weather_widget.set_units(units)
            
            # Ripristina la visibilità salvata
            self.launcher.weather_widget.setVisible(was_visible)
        
        # Salva tutto nel launcher_apps.json
        self.launcher.save_config()
        
        # Mostra conferma con dialog stilato
        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Settings Saved")
        confirm_dialog.setModal(True)
        confirm_dialog.setFixedSize(self.scaling.scale(380), self.scaling.scale(220))
        confirm_dialog.setStyleSheet("QDialog { background-color: #1a1a1a; }")

        dlg_layout = QVBoxLayout(confirm_dialog)
        dlg_layout.setSpacing(self.scaling.scale(16))
        dlg_layout.setContentsMargins(
            self.scaling.scale(25), self.scaling.scale(25),
            self.scaling.scale(25), self.scaling.scale(25)
        )

        # Card contenuto
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: #2a2a2a;
                border-radius: {self.scaling.scale(10)}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(self.scaling.scale(8))
        card_layout.setContentsMargins(
            self.scaling.scale(20), self.scaling.scale(18),
            self.scaling.scale(20), self.scaling.scale(18)
        )

        title_lbl = QLabel("✅ Settings Saved!")
        title_lbl.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: {self.scaling.scale_font(16)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title_lbl)

        units_label_str = 'Celsius' if units == 'metric' else 'Fahrenheit'
        info_lbl = QLabel(f"City: {city}\nUnits: {units_label_str}\n\nWeather updated! ✓")
        info_lbl.setStyleSheet(f"""
            QLabel {{
                color: #aaaaaa;
                font-size: {self.scaling.scale_font(13)}px;
                background: transparent;
                border: none;
            }}
        """)
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(info_lbl)

        dlg_layout.addWidget(card)

        # Pulsante OK
        ok_btn = QPushButton("OK")
        ok_btn.setFixedHeight(self.scaling.scale(42))
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a2a2a;
                color: white;
                border: 3px solid white;
                border-radius: {self.scaling.scale(8)}px;
                font-size: {self.scaling.scale_font(14)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3a3a3a;
            }}
        """)
        ok_btn.clicked.connect(confirm_dialog.accept)
        dlg_layout.addWidget(ok_btn)

        confirm_dialog.exec()
        
        self.accept()
    
    def update_confirm_focus(self):
        """Aggiorna il focus dei pulsanti (stile KeyRemapper)"""
        for i, btn in enumerate(self.confirm_buttons):
            if i == self.confirm_index[0]:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #2a2a2a;
                        color: white;
                        border: 3px solid white;
                        border-radius: {self.scaling.scale(8)}px;
                        font-size: {self.scaling.scale_font(14)}px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: #3a3a3a;
                    }}
                """)
            else:
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
                """)
    
    def keyPressEvent(self, event):
        """Gestisce navigazione con tastiera"""
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




def add_weather_settings_to_menu(settings_menu, launcher):
   
    from pathlib import Path
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap
    from modules.settings_menu import AnimatedToggle

    scaling  = settings_menu.scaling
    icon_dir = Path("assets/icons")

    
    container = QWidget()
    container.setFixedHeight(scaling.scale(70))
    container.setStyleSheet(f"""
        QWidget {{
            background-color: #2a2a2a;
            border: 2px solid #444;
            border-radius: {scaling.scale(8)}px;
        }}
    """)

    layout = QHBoxLayout(container)
    layout.setSpacing(scaling.scale(12))
    layout.setContentsMargins(
        scaling.scale(15), scaling.scale(10),
        scaling.scale(15), scaling.scale(10)
    )

    
    icon_path = icon_dir / "weather.png"
    if icon_path.exists():
        icon_lbl = QLabel()
        px = QPixmap(str(icon_path))
        if not px.isNull():
            icon_lbl.setPixmap(px.scaled(
                scaling.scale(40), scaling.scale(40),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        icon_lbl.setFixedSize(scaling.scale(40), scaling.scale(40))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

    
    text_layout = QVBoxLayout()
    text_layout.setSpacing(scaling.scale(5))

    title_lbl = QLabel("Weather Settings")
    title_lbl.setStyleSheet(f"""
        QLabel {{
            color: white;
            font-size: {scaling.scale_font(14)}px;
            font-weight: bold;
            background: transparent;
            border: none;
        }}
    """)
    desc_lbl = QLabel("Show widget · tap to configure")
    desc_lbl.setStyleSheet(f"""
        QLabel {{
            color: #aaa;
            font-size: {scaling.scale_font(12)}px;
            background: transparent;
            border: none;
        }}
    """)
    text_layout.addWidget(title_lbl)
    text_layout.addWidget(desc_lbl)
    layout.addLayout(text_layout)
    layout.addStretch()

    
    def _read_state():
        if settings_menu.launcher and hasattr(settings_menu.launcher, 'config_data'):
            return settings_menu.launcher.config_data.get('show_weather', False)
        return False

    toggle = AnimatedToggle(scaling)
    toggle.setChecked(_read_state())

    def on_toggle_changed(event):
        new_val = not toggle.isChecked()
        toggle.setChecked(new_val)
        lnch = settings_menu.launcher
        if lnch:
            if hasattr(lnch, 'config_data'):
                lnch.config_data['show_weather'] = new_val
            if hasattr(lnch, 'save_config'):
                lnch.save_config()
            if hasattr(lnch, 'weather_widget') and lnch.weather_widget:
                lnch.weather_widget.setVisible(new_val)
            elif hasattr(lnch, 'toggle_weather_visibility'):
                lnch.toggle_weather_visibility(new_val)

    toggle.mousePressEvent = on_toggle_changed
    layout.addWidget(toggle)

    container.checkbox = toggle  

    
    def _mouse_press(event):
        child = container.childAt(event.pos())
        if child is toggle or (child is not None and child.parent() is toggle):
            return
        current_launcher = settings_menu.launcher
        if current_launcher:
            _open_weather_settings(current_launcher, scaling, settings_menu)

    container.mousePressEvent = _mouse_press
    container.setCursor(Qt.CursorShape.PointingHandCursor)

    def _on_enter_press():
        """Callback chiamato quando si preme Enter sul container"""
        current_launcher = settings_menu.launcher
        if current_launcher:
            _open_weather_settings(current_launcher, scaling, settings_menu)
    
    
    container._on_enter_press = _on_enter_press
    
    container._refresh_toggle = lambda: toggle.setChecked(_read_state())

    return container


def _open_weather_settings(launcher, scaling, parent):
    """Apre il dialog delle impostazioni meteo"""
    if not launcher:
        print("❌ Launcher is None in _open_weather_settings!")
        return
    
    dialog = WeatherSettingsDialog(launcher, scaling, parent)
    dialog.exec()
