"""
Modulo per la gestione completa del joystick
Gestisce inizializzazione, polling, mappatura pulsanti e notifiche
"""

from PyQt6.QtCore import QTimer, Qt, QCoreApplication
from PyQt6.QtGui import QKeyEvent
import pygame

try:
    import pygame
    JOYSTICK_AVAILABLE = True
except ImportError:
    JOYSTICK_AVAILABLE = False
    print("Warning: pygame not installed. Joystick support disabled.")


class JoystickManager:
    """Gestisce tutte le funzionalità del joystick"""
    
    def __init__(self, parent, scaling):
        self.parent = parent
        self.scaling = scaling
        self.joystick = None
        self.joystick_timer = None
        self.joystick_detection_timer = None
        self.joystick_notification = None
        
        # Configurazione deadzone e cooldown
        self.axis_deadzone = 0.2
        self.button_cooldown = {}
        self.axis_cooldown = 0
        self._category_selector_enabled = False
        self._category_open_last_y = (False, 0, False)
        self._category_selector_last_x = (False, False, 0, False, False)
        self._category_selector_last_y = (False, 0, False)
        self._category_selector_last_b = False
        # Stati degli assi per rilevare cambiamenti
        self.last_axis_state = {'x': 0, 'y': 0}
        self.last_hat = (0, 0)
        
        # Stati per i vari menu (evita ripetizioni)
        self._menu_last_state = (False, False, 0, False, False)
        self._reorder_last_x = (False, False, 0, False, False)
        self._exit_dialog_last_x = (False, False, 0, False, False)
        self._search_last_state = (False, False, 0, False, False)
        self._category_dialog_last_state = (False, False, 0, False, False)
        self._bottom_menu_last_x = (False, False, 0, False, False)
        self._bottom_menu_last_y = (False, 0, False)
        self._carousel_last_x = (False, False, 0, False, False)
        self._carousel_last_y = (False, False, 0, False, False)
        
        if JOYSTICK_AVAILABLE:
            pygame.init()
            self.init_joystick()
            self.start_detection_timer()

    def register_category_support(self, launcher):
        """✅ NUOVO: Registra il category selector per il supporto joystick"""
        self._category_selector_enabled = True
        print("✅ Category selector joystick support enabled")

    def init_joystick(self):
        """Inizializza il joystick se disponibile"""
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                
                # Mostra notifica connessione
                from modules.joystick_notification import show_joystick_connected
                self.joystick_notification = show_joystick_connected(
                    self.parent, 
                    self.joystick.get_name(), 
                    self.scaling
                )
                
                print(f"🎮 Joystick connected: {self.joystick.get_name()}")
                
                # Imposta joystick nel volume manager
                
                
                # Avvia polling
                self.joystick_timer = QTimer()
                self.joystick_timer.timeout.connect(self.poll_joystick)
                self.joystick_timer.start(12)  # ~83 Hz
                
        except Exception as e:
            print(f"❌ Error initializing joystick: {e}")
    
    def start_detection_timer(self):
        """Avvia il timer per rilevare connessioni/disconnessioni"""
        self.joystick_detection_timer = QTimer()
        self.joystick_detection_timer.timeout.connect(self.detect_joystick)
        self.joystick_detection_timer.start(5000)  # Controlla ogni 5 secondi
    
    def detect_joystick(self):
        """Rileva connessioni/disconnessioni del joystick"""
        try:
            pygame.joystick.init()
            count = pygame.joystick.get_count()
            
            if count > 0 and self.joystick is None:
                # Joystick connesso dopo l'avvio
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                
                from modules.joystick_notification import show_joystick_connected
                self.joystick_notification = show_joystick_connected(
                    self.parent, 
                    self.joystick.get_name(), 
                    self.scaling
                )
                
                print(f"🎮 Joystick connected (late detection): {self.joystick.get_name()}")
                
                if self.joystick_timer is None:
                    self.joystick_timer = QTimer()
                    self.joystick_timer.timeout.connect(self.poll_joystick)
                    self.joystick_timer.start(12)
                    
            elif count == 0 and self.joystick is not None:
                # ✅ FIX: Verifica che sia DAVVERO disconnesso
                # Prova a leggere un asse - se funziona, NON è disconnesso
                try:
                    _ = self.joystick.get_numaxes()
                    # Se arriviamo qui, il joystick è ancora connesso
                    # NON disconnettere
                    print("ℹ️ False disconnect alarm - joystick still active")
                    return
                except:
                    # Se la lettura fallisce, allora è davvero disconnesso
                    pass
                
                # Joystick davvero disconnesso
                print("🔌 Joystick disconnected")
                
                from modules.joystick_notification import show_joystick_disconnected
                self.joystick_notification = show_joystick_disconnected(
                    self.parent, 
                    self.scaling
                )
                
                if self.joystick_timer:
                    self.joystick_timer.stop()
                    self.joystick_timer = None
                
                try:
                    self.joystick.quit()
                except:
                    pass
                
                self.joystick = None
                    
        except Exception as e:
            print(f"⚠️ Error during joystick detection: {e}")
            # ✅ FIX: NON disconnettere su errori generici
            # Solo disconnetti se il joystick è davvero inaccessibile
            if self.joystick is not None:
                try:
                    _ = self.joystick.get_numaxes()
                    # Se funziona, mantieni il joystick
                    print("ℹ️ Joystick still accessible despite error")
                    return
                except:
                    # Se non funziona, allora disconnetti
                    if self.joystick_timer:
                        self.joystick_timer.stop()
                        self.joystick_timer = None
                    try:
                        self.joystick.quit()
                    except:
                        pass
                    self.joystick = None
                
                
    
    def poll_joystick(self):
        """Polling principale del joystick - distribuisce agli handler appropriati"""
        if not self.joystick:
            return
        
        try:
            # Consuma eventi pygame
            for event in pygame.event.get():
                pass
            
            # ✅ CRITICAL FIX: Verifica joystick PRIMA di usarlo
            try:
                _ = self.joystick.get_numaxes()
            except (pygame.error, AttributeError):
                raise pygame.error("Joystick disconnected")
            
            # ✅ Controlla volume control PRIMA di tutto
            try:
                if self._handle_volume_control():
                    return
            except Exception as e:
                print(f"⚠️ Volume control error: {e}")
            
            # Distribuisci ai vari handler in ordine di priorità
            try:
                if self._handle_settings_menu():
                    return
            except Exception as e:
                print(f"⚠️ Settings menu error: {e}")
            
            if not self.parent.inputs_enabled:
                return
            
            try:
                if self._handle_reorder_mode():
                    return
            except Exception as e:
                print(f"⚠️ Reorder mode error: {e}")
            
            # ✅ FIX CRITICAL: Proteggi il category selector
            try:
                if self._category_selector_enabled and \
                    hasattr(self.parent, 'is_in_category_selector') and \
                    self.parent.is_in_category_selector:
                        self._handle_category_selector()
                        return
            except Exception as e:
                print(f"⚠️ Category selector error: {e}")
                # Disabilita il selector se continua a dare errori
                self.parent.is_in_category_selector = False

            try:
                if self._handle_exit_dialog():
                    return
            except Exception as e:
                print(f"⚠️ Exit dialog error: {e}")
            
            try:
                if self._handle_quick_search():
                    return
            except Exception as e:
                print(f"⚠️ Quick search error: {e}")
            
            try:
                if self._handle_category_dialog():
                    return
            except Exception as e:
                print(f"⚠️ Category dialog error: {e}")
            
            try:
                if self._handle_bottom_menu():
                    return
            except Exception as e:
                print(f"⚠️ Bottom menu error: {e}")
            
            # Handler principale del carousel
            try:
                self._handle_carousel_navigation()
                self._handle_main_buttons()
            except Exception as e:
                print(f"⚠️ Carousel/buttons error: {e}")
            
        except (pygame.error, AttributeError, ValueError) as e:
            # ✅ Solo disconnetti se è un VERO errore di disconnessione
            error_msg = str(e).lower()
            if "joystick" in error_msg or "device" in error_msg or "disconnected" in error_msg:
                print(f"⚠️ Joystick connection lost: {e}")
                self._handle_disconnection()
            else:
                print(f"⚠️ Temporary error (ignored): {e}")
        except Exception as e:
            print(f"⚠️ Unexpected error in poll_joystick: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_settings_menu(self):
        """Gestisce navigazione nel settings menu"""
        if not (hasattr(self.parent, 'settings_menu') and 
                getattr(self.parent.settings_menu, 'is_open', False)):
            self._menu_last_state = (False, False, 0, False, False)
            return False
        
        y_axis = self.joystick.get_axis(1)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
        
        current_state = (y_axis > self.axis_deadzone, y_axis < -self.axis_deadzone, 
                        hat[1], dpad_down, dpad_up)
        
        # Rileva movimenti
        if y_axis > self.axis_deadzone and not self._menu_last_state[0]:
            self.parent.settings_menu.navigate_down()
        elif y_axis < -self.axis_deadzone and not self._menu_last_state[1]:
            self.parent.settings_menu.navigate_up()
        elif hat[1] == -1 and self._menu_last_state[2] != -1:
            self.parent.settings_menu.navigate_down()
        elif hat[1] == 1 and self._menu_last_state[2] != 1:
            self.parent.settings_menu.navigate_up()
        elif dpad_down and not self._menu_last_state[3]:
            self.parent.settings_menu.navigate_down()
        elif dpad_up and not self._menu_last_state[4]:
            self.parent.settings_menu.navigate_up()
        
        self._menu_last_state = current_state
        
        # Gestisci pulsanti
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:  # A/Cross - Attiva
                    self.parent.settings_menu.activate_current()
                elif i in (1, 2, 6, 7, 9):  # Vari pulsanti per chiudere
                    self.parent.settings_menu.close_menu()
        
        return True
    
    def _handle_reorder_mode(self):
        """Gestisce navigazione in reorder mode"""
        if not (hasattr(self.parent, 'reorder_active') and self.parent.reorder_active):
            self._reorder_last_x = (False, False, 0, False, False)
            return False
        
        x_axis = self.joystick.get_axis(0)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_left = self.joystick.get_button(13) if self.joystick.get_numbuttons() > 13 else False
        dpad_right = self.joystick.get_button(14) if self.joystick.get_numbuttons() > 14 else False
        
        current_state_x = (x_axis > self.axis_deadzone, x_axis < -self.axis_deadzone,
                          hat[0], dpad_right, dpad_left)
        
        if x_axis > self.axis_deadzone and not self._reorder_last_x[0]:
            self._simulate_key(Qt.Key.Key_Right)
        elif x_axis < -self.axis_deadzone and not self._reorder_last_x[1]:
            self._simulate_key(Qt.Key.Key_Left)
        elif hat[0] == 1 and self._reorder_last_x[2] != 1:
            self._simulate_key(Qt.Key.Key_Right)
        elif hat[0] == -1 and self._reorder_last_x[2] != -1:
            self._simulate_key(Qt.Key.Key_Left)
        elif dpad_right and not self._reorder_last_x[3]:
            self._simulate_key(Qt.Key.Key_Right)
        elif dpad_left and not self._reorder_last_x[4]:
            self._simulate_key(Qt.Key.Key_Left)
        
        self._reorder_last_x = current_state_x
        
        # Pulsanti
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:
                    self._simulate_key(Qt.Key.Key_Return)
                elif i in (1, 2):
                    self._simulate_key(Qt.Key.Key_Escape)
        
        return True

        
    
    def _handle_exit_dialog(self):
        """Gestisce exit confirmation dialog"""
        if not (hasattr(self.parent, '_exit_dialog_active') and self.parent._exit_dialog_active):
            self._exit_dialog_last_x = (False, False, 0, False, False)
            return False
        
        x_axis = self.joystick.get_axis(0)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_left = self.joystick.get_button(13) if self.joystick.get_numbuttons() > 13 else False
        dpad_right = self.joystick.get_button(14) if self.joystick.get_numbuttons() > 14 else False
        
        current_state_x = (x_axis > self.axis_deadzone, x_axis < -self.axis_deadzone,
                          hat[0], dpad_right, dpad_left)
        
        if (x_axis > self.axis_deadzone and not self._exit_dialog_last_x[0]) or \
           (hat[0] == 1 and self._exit_dialog_last_x[2] != 1) or \
           (dpad_right and not self._exit_dialog_last_x[3]):
            self._simulate_key(Qt.Key.Key_Right)
        elif (x_axis < -self.axis_deadzone and not self._exit_dialog_last_x[1]) or \
             (hat[0] == -1 and self._exit_dialog_last_x[2] != -1) or \
             (dpad_left and not self._exit_dialog_last_x[4]):
            self._simulate_key(Qt.Key.Key_Left)
        
        self._exit_dialog_last_x = current_state_x
        
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:
                    self._simulate_key(Qt.Key.Key_Return)
                elif i in (1, 2):
                    self._simulate_key(Qt.Key.Key_Escape)
        
        return True
    
    def _handle_quick_search(self):
        """Gestisce quick search navigation"""
        if not (hasattr(self.parent, 'quick_search') and self.parent.quick_search.isVisible()):
            self._search_last_state = (False, False, 0, False, False)
            return False
        
        y_axis = self.joystick.get_axis(1)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
        
        current_state = (y_axis > self.axis_deadzone, y_axis < -self.axis_deadzone,
                        hat[1], dpad_down, dpad_up)
        
        if (y_axis > self.axis_deadzone and not self._search_last_state[0]) or \
           (hat[1] == -1 and self._search_last_state[2] != -1) or \
           (dpad_down and not self._search_last_state[3]):
            self.parent.quick_search.handle_joypad_input(Qt.Key.Key_Down)
        elif (y_axis < -self.axis_deadzone and not self._search_last_state[1]) or \
             (hat[1] == 1 and self._search_last_state[2] != 1) or \
             (dpad_up and not self._search_last_state[4]):
            self.parent.quick_search.handle_joypad_input(Qt.Key.Key_Up)
        
        self._search_last_state = current_state
        
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:
                    self.parent.quick_search.handle_joypad_input(Qt.Key.Key_Return)
                elif i == 1:
                    self.parent.quick_search.handle_joypad_input(Qt.Key.Key_Escape)
                elif i == 2:
                    self.parent.quick_search.handle_joypad_input(Qt.Key.Key_E)
        
        return True
    
    def _handle_category_dialog(self):
        """Gestisce category dialog navigation"""
        if not (hasattr(self.parent, '_category_dialog_open') and self.parent._category_dialog_open):
            self._category_dialog_last_state = (False, False, 0, False, False)
            return False
        
        y_axis = self.joystick.get_axis(1)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
        
        current_state = (y_axis > self.axis_deadzone, y_axis < -self.axis_deadzone,
                        hat[1], dpad_down, dpad_up)
        
        if (y_axis > self.axis_deadzone and not self._category_dialog_last_state[0]) or \
           (hat[1] == -1 and self._category_dialog_last_state[2] != -1) or \
           (dpad_down and not self._category_dialog_last_state[3]):
            self._simulate_key(Qt.Key.Key_Down)
        elif (y_axis < -self.axis_deadzone and not self._category_dialog_last_state[1]) or \
             (hat[1] == 1 and self._category_dialog_last_state[2] != 1) or \
             (dpad_up and not self._category_dialog_last_state[4]):
            self._simulate_key(Qt.Key.Key_Up)
        
        self._category_dialog_last_state = current_state
        
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:
                    self._simulate_key(Qt.Key.Key_Return)
                elif i in (1, 2):
                    self._simulate_key(Qt.Key.Key_Escape)
        
        return True
    
    def _handle_bottom_menu(self):
        """Gestisce menu basso (restart/shutdown/etc)"""
        if not self.parent.is_in_menu:
            self._bottom_menu_last_x = (False, False, 0, False, False)
            self._bottom_menu_last_y = (False, 0, False)
            return False
        
        # Navigazione orizzontale
        x_axis = self.joystick.get_axis(0)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_left = self.joystick.get_button(13) if self.joystick.get_numbuttons() > 13 else False
        dpad_right = self.joystick.get_button(14) if self.joystick.get_numbuttons() > 14 else False
        
        current_state_x = (x_axis > self.axis_deadzone, x_axis < -self.axis_deadzone,
                        hat[0], dpad_right, dpad_left)
        
        if (x_axis > self.axis_deadzone and not self._bottom_menu_last_x[0]) or \
        (hat[0] == 1 and self._bottom_menu_last_x[2] != 1) or \
        (dpad_right and not self._bottom_menu_last_x[3]):
            self._simulate_key(Qt.Key.Key_Right)
        elif (x_axis < -self.axis_deadzone and not self._bottom_menu_last_x[1]) or \
            (hat[0] == -1 and self._bottom_menu_last_x[2] != -1) or \
            (dpad_left and not self._bottom_menu_last_x[4]):
            self._simulate_key(Qt.Key.Key_Left)
        
        self._bottom_menu_last_x = current_state_x
        
        # Navigazione verticale (UP per uscire)
        y_axis = self.joystick.get_axis(1)
        hat_y = self.joystick.get_hat(0)[1] if self.joystick.get_numhats() > 0 else 0
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        
        current_state_y = (y_axis < -self.axis_deadzone, hat_y, dpad_up)
        
        if (y_axis < -self.axis_deadzone and not self._bottom_menu_last_y[0]) or \
        (hat_y == 1 and self._bottom_menu_last_y[1] != 1) or \
        (dpad_up and not self._bottom_menu_last_y[2]):
            self._simulate_key(Qt.Key.Key_Up)
            
            # ✅ FIX: Forza lo stato UP per evitare riapertura category selector
            self._category_open_last_y = (
                True if (y_axis < -self.axis_deadzone or dpad_up) else False,
                hat_y if hat_y != 0 else 0,
                True if dpad_up else False
            )
        
        self._bottom_menu_last_y = current_state_y
        
        # Pulsanti
        for i in range(self.joystick.get_numbuttons()):
            if self.joystick.get_button(i) and self._check_button_cooldown(i):
                if i == 0:
                    self._simulate_key(Qt.Key.Key_Return)
                elif i in (1, 2):
                    self._simulate_key(Qt.Key.Key_Up)
                    
                    # ✅ FIX: Forza stato anche per pulsante B
                    y_axis = self.joystick.get_axis(1)
                    hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
                    dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
                    
                    self._category_open_last_y = (
                        True if y_axis < -self.axis_deadzone else False,
                        hat[1] if hat[1] != 0 else 0,
                        True if dpad_up else False
                    )
        
        return True
    
    def _handle_carousel_navigation(self):
        """Gestisce navigazione nel carousel principale"""
        
        # ✅ NUOVO: Controlla se UP deve aprire category selector
        if self._category_selector_enabled and \
        not self.parent.is_in_menu and \
        not getattr(self.parent, 'reorder_active', False):
            
            y_axis = self.joystick.get_axis(1)
            hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
            dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
            
            current_state_y_up = (y_axis < -self.axis_deadzone, hat[1], dpad_up)
            
            moved_up = (y_axis < -self.axis_deadzone and not self._category_open_last_y[0]) or \
                    (hat[1] == 1 and self._category_open_last_y[1] != 1) or \
                    (dpad_up and not self._category_open_last_y[2])
            
            # ✅ FIX: Aggiungi cooldown per D-PAD UP (button 11)
            if moved_up and self._check_button_cooldown(11, cooldown_ms=250):
                try:
                    # ✅ CRITICAL: Verifica che category_selector esista
                    if not hasattr(self.parent, 'category_selector'):
                        print("⚠️ Category selector not initialized")
                        self._category_open_last_y = current_state_y_up
                        return
                    
                    # ✅ CRITICAL: Verifica che sound_manager esista
                    if hasattr(self.parent, 'sound_manager'):
                        self.parent.sound_manager.navigate()
                    
                    self.parent.is_in_category_selector = True
                    self.parent.category_selector.show_animated()
                    self._category_open_last_y = current_state_y_up
                    
                    print("✅ Category selector opened")
                    return
                    
                except Exception as e:
                    # ✅ FIX: Cattura errori senza crashare
                    print(f"⚠️ Error opening category selector: {e}")
                    self._category_open_last_y = current_state_y_up
                    # NON propagare l'errore
                    return
            
            self._category_open_last_y = current_state_y_up
        
        # Navigazione orizzontale (LEFT/RIGHT)
        x_axis = self.joystick.get_axis(0)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_left = self.joystick.get_button(13) if self.joystick.get_numbuttons() > 13 else False
        dpad_right = self.joystick.get_button(14) if self.joystick.get_numbuttons() > 14 else False
        
        current_state_x = (x_axis > self.axis_deadzone, x_axis < -self.axis_deadzone,
                        hat[0], dpad_right, dpad_left)
        
        moved_right = (x_axis > self.axis_deadzone and not self._carousel_last_x[0]) or \
                    (hat[0] == 1 and self._carousel_last_x[2] != 1) or \
                    (dpad_right and not self._carousel_last_x[3])
        
        moved_left = (x_axis < -self.axis_deadzone and not self._carousel_last_x[1]) or \
                    (hat[0] == -1 and self._carousel_last_x[2] != -1) or \
                    (dpad_left and not self._carousel_last_x[4])
        
        if moved_right and self.parent.apps and not self.parent.is_animating and not self.parent.is_in_menu:
            self._simulate_key(Qt.Key.Key_Right)
        elif moved_left and self.parent.apps and not self.parent.is_animating and not self.parent.is_in_menu:
            self._simulate_key(Qt.Key.Key_Left)
        
        self._carousel_last_x = current_state_x
        
        # Navigazione verticale (DOWN per menu basso)
        y_axis = self.joystick.get_axis(1)
        hat_y = hat[1]
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
        
        current_state_y = (y_axis > self.axis_deadzone, y_axis < -self.axis_deadzone,
                        hat_y, dpad_down, dpad_up)
        
        moved_down = (y_axis > self.axis_deadzone and not self._carousel_last_y[0]) or \
                    (hat_y == -1 and self._carousel_last_y[2] != -1) or \
                    (dpad_down and not self._carousel_last_y[3])
        
        moved_up = (y_axis < -self.axis_deadzone and not self._carousel_last_y[1]) or \
                (hat_y == 1 and self._carousel_last_y[2] != 1) or \
                (dpad_up and not self._carousel_last_y[4])
        
        if moved_down and not self.parent.is_in_menu:
            self._simulate_key(Qt.Key.Key_Down)
        elif moved_up and self.parent.is_in_menu:
            self._simulate_key(Qt.Key.Key_Up)
        
        self._carousel_last_y = current_state_y

    def _handle_category_selector(self):
        """✅ NUOVO: Gestisce input joystick nel category selector"""
        try:
            # ✅ CRITICAL: Verifica che category_selector esista ancora
            if not hasattr(self.parent, 'category_selector'):
                print("⚠️ Category selector disappeared")
                self.parent.is_in_category_selector = False
                return
            
            # Navigazione ORIZZONTALE (LEFT/RIGHT cambia categoria)
            x_axis = self.joystick.get_axis(0)
            y_axis = self.joystick.get_axis(1)
            hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
            
            dpad_left = self.joystick.get_button(13) if self.joystick.get_numbuttons() > 13 else False
            dpad_right = self.joystick.get_button(14) if self.joystick.get_numbuttons() > 14 else False
            dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
            
            # Gestisce LEFT/RIGHT per cambiare categoria
            current_state_x = (x_axis > self.axis_deadzone, x_axis < -self.axis_deadzone,
                            hat[0], dpad_right, dpad_left)
            
            moved_right = (x_axis > self.axis_deadzone and not self._category_selector_last_x[0]) or \
                        (hat[0] == 1 and self._category_selector_last_x[2] != 1) or \
                        (dpad_right and not self._category_selector_last_x[3])
            
            moved_left = (x_axis < -self.axis_deadzone and not self._category_selector_last_x[1]) or \
                        (hat[0] == -1 and self._category_selector_last_x[2] != -1) or \
                        (dpad_left and not self._category_selector_last_x[4])
            
            if moved_right:
                if hasattr(self.parent, 'sound_manager'):
                    self.parent.sound_manager.navigate()
                self.parent.category_selector.navigate_right()
            elif moved_left:
                if hasattr(self.parent, 'sound_manager'):
                    self.parent.sound_manager.navigate()
                self.parent.category_selector.navigate_left()
            
            self._category_selector_last_x = current_state_x
            
            # Navigazione VERTICALE (DOWN chiude)
            current_state_y = (y_axis > self.axis_deadzone, hat[1], dpad_down)
            
            moved_down = (y_axis > self.axis_deadzone and not self._category_selector_last_y[0]) or \
                        (hat[1] == -1 and self._category_selector_last_y[1] != -1) or \
                        (dpad_down and not self._category_selector_last_y[2])
            
            if moved_down:
                if hasattr(self.parent, 'sound_manager'):
                    self.parent.sound_manager.navigate()
                self._close_category_selector()
                return
            
            self._category_selector_last_y = current_state_y
            
            # Pulsante B (chiude)
            current_b_state = self.joystick.get_button(1) if self.joystick.get_numbuttons() > 1 else False
            
            if current_b_state and not self._category_selector_last_b:
                if hasattr(self.parent, 'sound_manager'):
                    self.parent.sound_manager.back()
                self._close_category_selector()
                current_time = pygame.time.get_ticks()
                self.button_cooldown[1] = current_time + 500
                self._category_selector_last_b = True
                return
            
            self._category_selector_last_b = current_b_state
            
            # Consuma altri pulsanti
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    current_time = pygame.time.get_ticks()
                    self.button_cooldown[i] = current_time + 400
                    
        except Exception as e:
            # ✅ FIX: Cattura errori senza crashare
            print(f"⚠️ Error in category selector handler: {e}")
            # Chiudi il selector se c'è un errore
            try:
                self._close_category_selector()
            except:
                self.parent.is_in_category_selector = False

    def _close_category_selector(self):
        """✅ NUOVO: Chiude il category selector"""
        from PyQt6.QtCore import QTimer
        
        self.parent.is_in_category_selector = False
        self.parent.category_selector.hide_animated()
        
        # Reset stati
        self._category_selector_last_x = (False, False, 0, False, False)
        self._category_selector_last_y = (False, 0, False)
        self._category_selector_last_b = False
        
        # Blocca tutti i pulsanti per 500ms
        current_time = pygame.time.get_ticks()
        for i in range(self.joystick.get_numbuttons()):
            self.button_cooldown[i] = current_time + 500
        
        # ✅ FIX CRITICO: Forza lo stato DOWN/UP come TRUE per evitare retriggering
        y_axis = self.joystick.get_axis(1)
        hat = self.joystick.get_hat(0) if self.joystick.get_numhats() > 0 else (0, 0)
        dpad_up = self.joystick.get_button(11) if self.joystick.get_numbuttons() > 11 else False
        dpad_down = self.joystick.get_button(12) if self.joystick.get_numbuttons() > 12 else False
        
        # Forza TUTTI gli stati del carousel come se fossero già premuti
        self._carousel_last_y = (
            True if (y_axis > self.axis_deadzone or dpad_down) else False,  # DOWN
            True if (y_axis < -self.axis_deadzone or dpad_up) else False,   # UP
            hat[1] if hat[1] != 0 else 0,
            True if dpad_down else False,  # D-PAD DOWN
            True if dpad_up else False     # D-PAD UP
        )
        
        # ✅ FIX: Forza anche lo stato per riaprire il category selector
        self._category_open_last_y = (
            True if (y_axis < -self.axis_deadzone or dpad_up) else False,  # UP analogico
            hat[1] if hat[1] != 0 else 0,                                   # Hat Y
            True if dpad_up else False                                      # D-PAD UP
        )           
            
    def _handle_main_buttons(self):
        """Gestisce i pulsanti principali del joystick"""
        for i in range(self.joystick.get_numbuttons()):
            if not self.joystick.get_button(i) or not self._check_button_cooldown(i):
                continue
            
            # Mappatura pulsanti
            if i == 0:  # A/Cross - Conferma
                self._simulate_key(Qt.Key.Key_Return)
            elif i == 1:  # B/Circle - Indietro
                self._simulate_key(Qt.Key.Key_Escape)
            elif i == 2:  # X/Square - Quick Category
                if not (hasattr(self.parent, 'reorder_active') and self.parent.reorder_active):
                    self._simulate_key(Qt.Key.Key_C)
            elif i == 3:  # Y/Triangle - Delete
                self._simulate_key(Qt.Key.Key_Delete)
            elif i == 4:  # LB/L1 - Quick Search
                self._simulate_key(Qt.Key.Key_F)
            elif i == 5:  # RB/R1 - Reorder Mode
                self._simulate_key(Qt.Key.Key_R)
            elif i in (6, 7):  # L2/Start - Settings
                self._open_settings()
            elif i == 9:  # Options (PS4) - Quick Search
                self._simulate_key(Qt.Key.Key_F)
            elif i == 10:  # L3 (PS4) - Reorder Mode
                self._simulate_key(Qt.Key.Key_R)
    

    def _handle_volume_control(self):
        """Gestisce controllo volume con LT/L2 + D-Pad UP/DOWN"""
        # Verifica che il volume manager esista
        if not hasattr(self.parent, 'volume_manager') or not self.parent.volume_manager:
            return False
        
        # Verifica che il launcher sia in focus
        if not self.parent.volume_manager.is_launcher_focused():
            return False
        
        # Leggi il trigger sinistro (LT)
        try:
            lt_axis = self.joystick.get_axis(2)  # Axis 2 per Linux
        except:
            return False
        
        # Trigger NON premuto (a riposo = -1.0)
        if lt_axis < 0.0:
            return False
        
        # ✅ Trigger PREMUTO: gestisci volume
        try:
            if self.joystick.get_numhats() > 0:
                hat = self.joystick.get_hat(0)
                
                # D-Pad UP = volume su
                if hat[1] == 1 and self._check_button_cooldown(9001, cooldown_ms=250):
                    self.parent.volume_manager.increase_volume()
                
                # D-Pad DOWN = volume giù
                elif hat[1] == -1 and self._check_button_cooldown(9002, cooldown_ms=250):
                    self.parent.volume_manager.decrease_volume()
        except Exception as e:
            # ⚠️ NON propagare l'errore - potrebbe far crashare poll_joystick
            print(f"⚠️ Volume control error (non-critical): {e}")
            pass
        
        # Ritorna True per bloccare altri handler
        return True

    def _check_button_cooldown(self, button_index, cooldown_ms=300):
        """Verifica e aggiorna il cooldown dei pulsanti"""
        current_time = pygame.time.get_ticks()
        
        if button_index in self.button_cooldown:
            if current_time - self.button_cooldown[button_index] < cooldown_ms:
                return False
        
        self.button_cooldown[button_index] = current_time
        return True
    
    def _simulate_key(self, key):
        """Simula la pressione di un tasto"""
        event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
        active_win = QCoreApplication.instance().activeWindow()
        if active_win:
            QCoreApplication.postEvent(active_win, event)
    
    def _open_settings(self):
        """Apre il menu settings"""
        try:
            if hasattr(self.parent, 'settings_menu') and self.parent.settings_menu is not None:
                if not getattr(self.parent.settings_menu, 'is_open', False):
                    self.parent.settings_menu.open_menu(self.parent)
        except Exception as e:
            print(f"⚠️ Error opening settings: {e}")
    
    def _handle_disconnection(self):
        """Gestisce la disconnessione improvvisa del joystick"""
        if self.joystick_timer:
            self.joystick_timer.stop()
            self.joystick_timer = None
        
        self.joystick = None
        
       
        
        
        from modules.joystick_notification import show_joystick_disconnected
        self.joystick_notification = show_joystick_disconnected(
            self.parent, 
            self.scaling
        )
    
    def cleanup(self):
        """Pulizia risorse prima della chiusura"""
        if self.joystick_timer:
            self.joystick_timer.stop()
        if self.joystick_detection_timer:
            self.joystick_detection_timer.stop()
        if JOYSTICK_AVAILABLE:
            pygame.quit()