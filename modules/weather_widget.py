from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap
import json
from pathlib import Path

# Try to import requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️ requests not installed. Weather widget disabled.")
    print("Install with: pip install requests")


class WeatherFetcher(QThread):
    """Thread separato per fetch API senza bloccare l'UI"""
    weather_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, city, country_code, units, latitude=None, longitude=None):
        super().__init__()
        self.city = city
        self.country_code = country_code
        self.units = units
        self.latitude = latitude
        self.longitude = longitude
    
    def run(self):
        """Esegue la richiesta API in background"""
        if not REQUESTS_AVAILABLE:
            self.error_occurred.emit("requests library not installed")
            return
        
        # Se non abbiamo coordinate, proviamo a geocodificare la città
        if self.latitude is None or self.longitude is None:
            coords = self._geocode_city()
            if not coords:
                self.error_occurred.emit(f"Could not find coordinates for {self.city}")
                return
            self.latitude, self.longitude = coords
        
        # Prova prima Open-Meteo 
        success = self._fetch_open_meteo()
        
        if not success:
            # Fallback a wttr.in
            print("   Trying fallback: wttr.in...")
            success = self._fetch_wttr()
        
        if not success:
            self.error_occurred.emit("All weather services failed")
    
    def _geocode_city(self):
        """Ottiene coordinate GPS da nome città usando Open-Meteo Geocoding (gratuito)"""
        try:
            location = f"{self.city},{self.country_code}" if self.country_code else self.city
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                'name': self.city,
                'count': 1,
                'language': 'en',
                'format': 'json'
            }
            
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    result = data['results'][0]
                    lat = result['latitude']
                    lon = result['longitude']
                    print(f"   Found: {result.get('name', self.city)}")
                    return (lat, lon)
            
            return None
            
        except Exception as e:
            print(f"   Geocoding error: {e}")
            return None
    
    def _fetch_open_meteo(self):
        """Fetch da Open-Meteo"""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
           
            
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'current_weather': 'true',
                'windspeed_unit': 'kmh',
                'timezone': 'auto'
            }
            
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                
                weather_data = self._parse_open_meteo(data)
                
                # Determina unità per il log
                temp_celsius = weather_data['temp_celsius']
                if self.units == 'imperial':
                    temp_display = round((temp_celsius * 9/5) + 32)
                    unit = "°F"
                else:
                    temp_display = round(temp_celsius)
                    unit = "°C"
                
                self.weather_received.emit(weather_data)
                print(f"Open-Meteo: {temp_display}{unit} - {weather_data['condition']}")
                return True
            else:
                print(f"Open-Meteo error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Open-Meteo exception: {e}")
            return False
    
    def _fetch_wttr(self):
        """Fetch da wttr.in (FALLBACK)"""
        try:
            location = f"{self.city},{self.country_code}" if self.country_code else self.city
            url = f"https://wttr.in/{location}"
            params = {
                'format': 'j1'  # JSON format
            }
            
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Converti in formato standardizzato
                weather_data = self._parse_wttr(data)
                
                # Determina unità per il log
                temp_celsius = weather_data['temp_celsius']
                if self.units == 'imperial':
                    temp_display = round((temp_celsius * 9/5) + 32)
                    unit = "°F"
                else:
                    temp_display = round(temp_celsius)
                    unit = "°C"
                
                self.weather_received.emit(weather_data)
                print(f"wttr.in: {temp_display}{unit} - {weather_data['condition']}")
                return True
            else:
                print(f"wttr.in error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"wttr.in exception: {e}")
            return False
    
    def _parse_open_meteo(self, data):
        """Converte dati Open-Meteo in formato standardizzato"""
        current = data['current_weather']
        
       
        temp_celsius = current['temperature']
        
        # Mappa codici meteo Open-Meteo a condizioni leggibili
        weather_codes = {
            0: ('Clear sky', '01d'),
            1: ('Mainly clear', '02d'),
            2: ('Partly cloudy', '02d'),
            3: ('Overcast', '03d'),
            45: ('Foggy', '50d'),
            48: ('Foggy', '50d'),
            51: ('Light drizzle', '09d'),
            53: ('Drizzle', '09d'),
            55: ('Heavy drizzle', '09d'),
            61: ('Light rain', '10d'),
            63: ('Rain', '10d'),
            65: ('Heavy rain', '10d'),
            71: ('Light snow', '13d'),
            73: ('Snow', '13d'),
            75: ('Heavy snow', '13d'),
            77: ('Snow grains', '13d'),
            80: ('Light showers', '09d'),
            81: ('Showers', '09d'),
            82: ('Heavy showers', '09d'),
            85: ('Light snow showers', '13d'),
            86: ('Snow showers', '13d'),
            95: ('Thunderstorm', '11d'),
            96: ('Thunderstorm with hail', '11d'),
            99: ('Thunderstorm with hail', '11d'),
        }
        
        code = current.get('weathercode', 0)
        condition, icon_code = weather_codes.get(code, ('Unknown', '01d'))
        
        return {
            'temp_celsius': temp_celsius,  # Salva temperatura in Celsius
            'condition': condition,
            'icon': icon_code,
            'humidity': 0,
            'feels_like_celsius': temp_celsius
        }
    
    def _parse_wttr(self, data):
        """Converte dati wttr.in in formato standardizzato"""
        current = data['current_condition'][0]
        
        # wttr fornisce sia Celsius che Fahrenheit
        temp_c = float(current['temp_C'])
        temp_f = float(current['temp_F'])
        
        # Salva sempre Celsius come valore base
        temp_celsius = temp_c
        
        # Converti descrizione wttr in icon code approssimativo
        desc = current['weatherDesc'][0]['value'].lower()
        icon_code = self._weather_desc_to_icon(desc)
        
        return {
            'temp_celsius': temp_celsius,  # Salva temperatura in Celsius
            'condition': current['weatherDesc'][0]['value'],
            'icon': icon_code,
            'humidity': int(current.get('humidity', 0)),
            'feels_like_celsius': float(current['FeelsLikeC'])
        }
    
    def _weather_desc_to_icon(self, description):
        """Converte descrizione testuale in codice icona"""
        desc = description.lower()
        
        if 'clear' in desc or 'sunny' in desc:
            return '01d'
        elif 'partly cloudy' in desc or 'partly cloud' in desc:
            return '02d'
        elif 'cloudy' in desc or 'overcast' in desc:
            return '03d'
        elif 'rain' in desc or 'drizzle' in desc:
            return '10d'
        elif 'thunder' in desc or 'storm' in desc:
            return '11d'
        elif 'snow' in desc:
            return '13d'
        elif 'mist' in desc or 'fog' in desc:
            return '50d'
        else:
            return '02d'


class WeatherWidget(QWidget):
    """Widget meteo che mostra temperatura e condizioni attuali"""
    
    # Signal emesso quando i dati meteo vengono aggiornati
    weather_updated = pyqtSignal(dict)
    
    def __init__(self, scaling, parent=None):
        super().__init__(parent)
        self.scaling = scaling
        self.city = "Rome"  # Default city
        self.country_code = "IT"  # Default country
        self.units = "metric"  # metric = Celsius, imperial = Fahrenheit
        
        # Coordinate GPS (cache per evitare geocoding ripetuto)
        self.latitude = None
        self.longitude = None
        
        # Thread per fetch API
        self.fetcher = None
        
        # Timer per aggiornamento automatico (ogni 30 minuti)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.fetch_weather)
        self.update_timer.setInterval(30 * 60 * 1000)  # 30 minuti
        
        # Timer per fetch ritardato (può essere fermato)
        self.delayed_fetch_timer = QTimer()
        self.delayed_fetch_timer.setSingleShot(True)
        self.delayed_fetch_timer.timeout.connect(self.fetch_weather)
        
        # Dati meteo attuali
        self.current_weather = {
            'temp': '--',
            'condition': 'Loading...',
            'icon': '01d',
            'humidity': '--',
            'feels_like': '--'
        }
        
        # Flag visibilità controllata dall'utente (default: False = nascosto)
        self._user_visible = False
        
        # Opacity effect + animazione fade-in
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        
        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setDuration(400)  # 400ms – morbido ma non lento
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.init_ui()
        
    def setVisible(self, visible):
        """Override: salva la scelta dell'utente.
        
        Se visible=True ma non ci sono ancora dati reali, tiene il widget
        nascosto (opacity=0) e aspetta che _update_weather_data faccia il fade-in.
        Se i dati ci sono già (es. cambio unità), fa subito il fade-in.
        """
        self._user_visible = visible
        
        if visible and self.city:
            # Avvia fetch e timer se non già attivi
            if not self.update_timer.isActive():
                self.delayed_fetch_timer.start(2000)
                self.update_timer.start()
            
            # Mostra il widget solo se abbiamo già dati reali
            if self.current_weather.get('temp_celsius') is not None:
                super().setVisible(True)
                self._fade_in()
            else:
                # Rimane nascosto: apparirà con fade-in in _update_weather_data
                super().setVisible(False)
        else:
            # Widget disattivato – ferma tutto e nascondi
            if self.update_timer.isActive():
                self.update_timer.stop()
            if self.delayed_fetch_timer.isActive():
                self.delayed_fetch_timer.stop()
            if self.fetcher and self.fetcher.isRunning():
                self.fetcher.quit()
                self.fetcher.wait(1000)
            self._fade_anim.stop()
            self._opacity_effect.setOpacity(0.0)
            super().setVisible(False)
    
    def _fade_in(self):
        """Avvia l'animazione di fade-in da opacità corrente a 1.0"""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        
    def init_ui(self):
        """Inizializza l'interfaccia del widget"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.scaling.scale(2))
        
        # Container principale
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, self.scaling.scale(20), 0)  
        container_layout.setSpacing(self.scaling.scale(12))
        
        # Layout verticale per icona + città
        icon_city_layout = QVBoxLayout()
        icon_city_layout.setSpacing(self.scaling.scale(2))
        icon_city_layout.setContentsMargins(0, 0, 0, 0)
        icon_city_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        # Icona meteo
        self.weather_icon = QLabel()
        self.weather_icon.setFixedSize(self.scaling.scale(64), self.scaling.scale(64))
        self.weather_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_weather_emoji("☁️")  # Default icon
        
        # Nome città (sotto l'icona)
        self.city_label = QLabel(self.city.title())
        self.city_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.city_label.setWordWrap(True)
        self.city_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.7);
            font-size: {self.scaling.scale_font(14)}px;
            font-weight: 600;
        """)
        
        icon_city_layout.addWidget(self.weather_icon)
        icon_city_layout.addWidget(self.city_label)
        
        # Info meteo (temperatura + condizione)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(self.scaling.scale(2))
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        # Temperatura (stessa altezza dell'icona)
        self.temp_label = QLabel("--°")
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.temp_label.setMinimumHeight(self.scaling.scale(64))
        self.temp_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {self.scaling.scale_font(36)}px;
            font-weight: 700;
        """)
        
        self.condition_label = QLabel("Loading...")
        self.condition_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.condition_label.setWordWrap(True)
        self.condition_label.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.6);
            font-size: {self.scaling.scale_font(14)}px;
            font-weight: 500;
        """)
        
        info_layout.addWidget(self.temp_label)
        info_layout.addWidget(self.condition_label)
        
        container_layout.addLayout(icon_city_layout)
        container_layout.addLayout(info_layout)
        
        layout.addWidget(container)
        
        # Nascondi il widget finché non ci sono dati validi
        self.hide()
    
    def _set_weather_emoji(self, emoji):
        """Imposta l'emoji del meteo"""
        # Assicurati che la font size sia almeno 1
        font_size = max(self.scaling.scale_font(48), 1)
        self.weather_icon.setStyleSheet(f"""
            font-size: {font_size}px;
        """)
        self.weather_icon.setText(emoji)
    
    def set_location(self, city, country_code=""):
        """Imposta la località per le previsioni"""
        self.city = city.strip()
        self.country_code = country_code.strip()
        
        # Aggiorna la label della città
        if hasattr(self, 'city_label'):
            self.city_label.setText(self.city.title())
        
        # Reset coordinate (verranno ri-geocodificate)
        self.latitude = None
        self.longitude = None
        
        if self.city:
            
            if self._user_visible and not self.delayed_fetch_timer.isActive():
                self.delayed_fetch_timer.start(2000)
            
            # Avvia il timer di aggiornamento solo se visibile
            if self._user_visible and not self.update_timer.isActive():
                self.update_timer.start()
        else:
            self.update_timer.stop()
            self.delayed_fetch_timer.stop()
            self.hide()
    
    def set_units(self, units):
        """Imposta le unità di misura (metric/imperial)"""
        old_units = self.units
        self.units = units
        
        
        
        
        if self.current_weather.get('temp_celsius') is not None:
            temp_celsius = self.current_weather['temp_celsius']
            
            if self.units == 'imperial':
                temp = round((temp_celsius * 9/5) + 32)
                unit_symbol = "°F"
            else:
                temp = round(temp_celsius)
                unit_symbol = "°C"
            
            # Aggiorna i dati interni
            self.current_weather['temp'] = temp
            
            # Aggiorna l'UI
            self.temp_label.setText(f"{temp}{unit_symbol}")
            
            print(f"   Temperature display updated: {temp}{unit_symbol}")
            
            was_visible = self.isVisible()
            
            # Forza aggiornamento immediato
            self.temp_label.update()
            self.temp_label.repaint()
            self.update()
            self.repaint()
            
            if was_visible and self._user_visible:
                if not self.isVisible():
                    super().setVisible(True)
                self._fade_in()
            
            # Forza anche il parent a ridisegnarsi
            if self.parent():
                self.parent().update()
                self.parent().repaint()
                
        elif self.city and self._user_visible:
            print(f"   No existing data, fetching weather...")
            # Usa il delayed timer per evitare fetch duplicati se setVisible/set_location
            # sono stati chiamati poco prima (si sovrascrive la schedulazione esistente)
            self.delayed_fetch_timer.stop()
            self.delayed_fetch_timer.start(100)
    
    def fetch_weather(self):
        """Effettua la richiesta API per ottenere il meteo"""
        if not REQUESTS_AVAILABLE:
            print("⚠️ Weather: requests library not available")
            return
            
        if not self.city:
            print("⚠️ Weather: city not set")
            return
        
        # Se c'è già un fetch in corso, aspetta
        if self.fetcher and self.fetcher.isRunning():
            return
        
        # Crea e avvia il thread di fetch
        self.fetcher = WeatherFetcher(
            self.city, 
            self.country_code, 
            self.units,
            self.latitude,
            self.longitude
        )
        self.fetcher.weather_received.connect(self._update_weather_data)
        self.fetcher.error_occurred.connect(self._show_error_message)
        self.fetcher.start()
    
    def _show_error_message(self, error_msg):
        """Mostra un messaggio di errore"""
        print(f"❌ Weather: {error_msg}")
        self._show_error()
    
    def _update_weather_data(self, data):
        """Aggiorna i dati meteo dal JSON dell'API"""
        try:
            
            if self.fetcher:
                self.latitude = self.fetcher.latitude
                self.longitude = self.fetcher.longitude
            
            # Ottieni temperatura in Celsius dall'API
            temp_celsius = data.get('temp_celsius', data.get('temp', 0))
            
            # Converti in base alle unità CORRENTI del widget
            if self.units == 'imperial':
                temp = round((temp_celsius * 9/5) + 32)
                unit_symbol = "°F"
                print(f"   Converted: {temp_celsius}°C → {temp}°F")
            else:
                temp = round(temp_celsius)
                unit_symbol = "°C"
                
            
            condition = data['condition']
            icon_code = data['icon']
            
            # Aggiorna i dati interni
            self.current_weather = {
                'temp': temp,
                'temp_celsius': temp_celsius,  
                'condition': condition,
                'icon': icon_code,
                'humidity': data.get('humidity', 0),
                'feels_like': temp
            }
            
            # Aggiorna UI
            self.temp_label.setText(f"{temp}{unit_symbol}")
            self.condition_label.setText(condition)
            
            # Imposta l'emoji in base al codice icona
            emoji = self._get_weather_emoji(icon_code)
            self._set_weather_emoji(emoji)
            
            # Mostra il widget con fade-in solo se l'utente lo ha abilitato
            if self._user_visible:
                if not self.isVisible():
                    super().setVisible(True)
                self._fade_in()
            
            # Emetti il segnale
            self.weather_updated.emit(self.current_weather)
            
        except KeyError as e:
            print(f"❌ Missing weather data field: {e}")
            self._show_error()
    
    def _get_weather_emoji(self, icon_code):
        """Converte il codice icona in emoji"""
        # Mappatura codici icona -> Emoji
        icon_map = {
            '01d': '☀️',   # clear sky day
            '01n': '🌙',   # clear sky night
            '02d': '⛅',   # few clouds day
            '02n': '☁️',   # few clouds night
            '03d': '☁️',   # scattered clouds
            '03n': '☁️',
            '04d': '☁️',   # broken clouds
            '04n': '☁️',
            '09d': '🌧️',  # shower rain
            '09n': '🌧️',
            '10d': '🌦️',  # rain day
            '10n': '🌧️',  # rain night
            '11d': '⛈️',  # thunderstorm
            '11n': '⛈️',
            '13d': '❄️',   # snow
            '13n': '❄️',
            '50d': '🌫️',  # mist
            '50n': '🌫️',
        }
        
        return icon_map.get(icon_code, '🌤️')  # Default icon
    
    def _show_error(self):
        """Mostra uno stato di errore"""
        self.temp_label.setText("--°")
        self.condition_label.setText("No data")
        self._set_weather_emoji("❌")
    
    def stop(self):
        """Ferma il timer di aggiornamento"""
        if self.update_timer.isActive():
            self.update_timer.stop()
        
        # Ferma il thread di fetch se in esecuzione
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.quit()
            self.fetcher.wait(1000)
    
    def cleanup(self):
        """Cleanup delle risorse"""
        self.stop()



def integrate_weather_widget(launcher, base_dir):
   
    # Crea il widget meteo
    launcher.weather_widget = WeatherWidget(launcher.scaling, launcher)
    
    # Salva il base_dir per uso futuro
    launcher.weather_base_dir = base_dir
    
    



def add_weather_to_header(launcher, header_layout):
    """
    Aggiunge il widget meteo all'header del launcher.
    Chiamare in TVLauncher.init_ui() dopo aver creato clock_layout
    
    Args:
        launcher: Istanza di TVLauncher
        header_layout: QHBoxLayout dell'header
    """
   
    pass


def save_weather_config(launcher, city, country_code, units):
    """
    DEPRECATA: Questa funzione è obsoleta!
    
    La configurazione weather viene ora salvata direttamente in launcher_apps.json
    tramite launcher.save_config() chiamato da weather_settings.py
    
   
    
    Args:
        launcher: Istanza di TVLauncher
        city: Nome della città (ignorato)
        country_code: Codice paese (ignorato)
        units: Unità di misura (ignorato)
    """
    
    pass


def force_launcher_refresh(launcher):
    """
    Forza il refresh completo del launcher e dell'header
    Chiamare dopo aver aggiornato il weather widget
    """
    if not launcher:
        print("⚠️ Launcher is None, cannot refresh")
        return
    
   
    
    # Aggiorna il widget meteo
    if hasattr(launcher, 'weather_widget'):
        launcher.weather_widget.update()
        launcher.weather_widget.repaint()
    
    # Trova e aggiorna il centralWidget 
    try:
        central = launcher.centralWidget()
        if central:
            central.update()
            central.repaint()
            
            # Aggiorna il layout del central widget preservando visibilità weather
            layout = central.layout()
            if layout:
                layout.update()
                # Salva visibilità prima di activate() che può resettarla
                _wv = None
                if hasattr(launcher, 'weather_widget') and launcher.weather_widget:
                    _wv = launcher.weather_widget._user_visible
                layout.activate()
                # Ripristina visibilità dopo activate()
                if _wv is not None:
                    launcher.weather_widget._user_visible = _wv
                    launcher.weather_widget.setVisible(_wv)
    except Exception as e:
        print(f"   ⚠️ Error updating central widget: {e}")
    
    # Aggiorna la finestra principale
    try:
        launcher.update()
        launcher.repaint()
    except Exception as e:
        print(f"   ⚠️ Error updating launcher: {e}")
    
    
    try:
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
    except Exception as e:
        print(f"   ⚠️ Error processing events: {e}")
    
    


def cleanup_weather_widget(launcher):
  
    if hasattr(launcher, 'weather_widget'):
        launcher.weather_widget.cleanup()
