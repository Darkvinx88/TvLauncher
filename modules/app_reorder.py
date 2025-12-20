"""
App Reordering Module for TV Launcher
Handles drag-and-drop style reordering with keyboard/joypad controls

Save this file as 'app_reorder.py' in the same directory as tvlauncher.py
"""

from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer
import time

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class ReorderMode:
    """Manages the reordering state and UI feedback"""
    
    def __init__(self, launcher):
        self.launcher = launcher
        self.is_active = False
        self.selected_index = None
        self.target_index = None
        
        # Timer for long press detection (keyboard only)
        self.long_press_timer = QTimer()
        self.long_press_timer.timeout.connect(self._activate_reorder)
        self.long_press_duration = 800  # ms to hold before activating
        
        # UI overlay
        self.overlay = None
        self.instruction_label = None

        # Debounce for buttons
        self.last_button_times = {}
        
        # Flag to prevent reactivation after exiting
        self.recently_exited = False
        self.exit_cooldown_timer = QTimer()
        self.exit_cooldown_timer.timeout.connect(self._clear_exit_cooldown)
        self.exit_cooldown_timer.setSingleShot(True)
        
    def _clear_exit_cooldown(self):
        """Clears the exit cooldown flag"""
        self.recently_exited = False
    
    def _is_dialog_active(self):
        """Check if any dialog or menu is currently active"""
        from PyQt6.QtWidgets import QApplication
        # Check if any modal dialog is open
        active_modal = QApplication.activeModalWidget()
        if active_modal:
            return True
        # Check if any popup is open
        active_popup = QApplication.activePopupWidget()
        if active_popup:
            return True
        return False
        
    def start_long_press(self):
        """Called when launch button is pressed"""
        # Don't activate if in menu, dialog active, or recently exited
        if (not self.is_active and 
            self.launcher.apps and 
            not self.recently_exited and
            not self.launcher.is_in_menu and
            not self._is_dialog_active()):
            self.long_press_timer.start(self.long_press_duration)
    
    def cancel_long_press(self):
        """Called when launch button is released"""
        if self.long_press_timer.isActive():
            self.long_press_timer.stop()
    
    def force_cancel_all_timers(self):
        """Force cancel all timers - called when launching app"""
        if self.long_press_timer.isActive():
            self.long_press_timer.stop()
        if self.exit_cooldown_timer.isActive():
            self.exit_cooldown_timer.stop()
    
    def _activate_reorder(self):
        """Activates reorder mode after long press"""
        self.long_press_timer.stop()
        
        # Don't activate if dialog is open or in menu
        if (self.launcher.apps and 
            not self.is_active and 
            not self.launcher.is_in_menu and
            not self._is_dialog_active()):
            self.is_active = True
            self.selected_index = self.launcher.current_index
            self.target_index = self.launcher.current_index
            self._show_reorder_ui()
            self._update_tile_highlights()
            print(f"🔄 Reorder mode activated - Selected: {self.launcher.apps[self.selected_index]['name']}")
    
    def _show_reorder_ui(self):
        """Shows visual feedback for reorder mode"""
        if self.overlay is None:
            # Create semi-transparent overlay
            self.overlay = QWidget(self.launcher)
            self.overlay.setGeometry(0, 0, self.launcher.width(), self.launcher.height())
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
            self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            # Create instruction label
            self.instruction_label = QLabel(self.overlay)
            self.instruction_label.setText(
                "🔄 REORDER MODE\n\n"
                "← → to move position\n"
                "Enter/A to confirm | Esc/B to cancel\n"
                "R or RB to toggle mode"
            )
            self.instruction_label.setStyleSheet(f"""
                QLabel {{
                    background-color: rgba(30, 30, 30, 0.95);
                    color: white;
                    font-size: {self.launcher.scaling.scale_font(18)}px;
                    font-weight: bold;
                    padding: {self.launcher.scaling.scale(30)}px;
                    border-radius: {self.launcher.scaling.scale(20)}px;
                    border: {self.launcher.scaling.scale(3)}px solid white;
                }}
            """)
            self.instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Position at top center
            self.instruction_label.adjustSize()
            x = (self.launcher.width() - self.instruction_label.width()) // 2
            y = self.launcher.scaling.scale(100)
            self.instruction_label.move(x, y)
        
        self.overlay.raise_()
        self.overlay.show()
        self.instruction_label.show()
        
        # Add position numbers to tiles
        self._add_position_numbers()
    
    def _hide_reorder_ui(self):
        """Hides reorder mode UI"""
        if self.overlay:
            self.overlay.hide()
        if self.instruction_label:
            self.instruction_label.hide()
        
        # Remove position numbers
        self._remove_position_numbers()
    
    def _add_position_numbers(self):
        """Adds position number labels to each tile"""
        if not self.launcher.tiles:
            return
        
        for tile in self.launcher.tiles:
            if not hasattr(tile, 'position_label'):
                # Create position label
                tile.position_label = QLabel(tile)
                tile.position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                tile.position_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: rgba(0, 0, 0, 0.8);
                        color: white;
                        font-size: {self.launcher.scaling.scale_font(32)}px;
                        font-weight: bold;
                        border-radius: {self.launcher.scaling.scale(25)}px;
                        border: {self.launcher.scaling.scale(2)}px solid white;
                    }}
                """)
                
                # Position in top-left corner of tile
                size = self.launcher.scaling.scale(50)
                tile.position_label.setFixedSize(size, size)
                tile.position_label.move(
                    self.launcher.scaling.scale(10),
                    self.launcher.scaling.scale(10)
                )
            
            # Update the number (1-based indexing for user)
            tile.position_label.setText(str(tile.app_index + 1))
            tile.position_label.show()
            tile.position_label.raise_()
    
    def _remove_position_numbers(self):
        """Removes position number labels from tiles"""
        if not self.launcher.tiles:
            return
        
        for tile in self.launcher.tiles:
            if hasattr(tile, 'position_label'):
                tile.position_label.hide()
    
    def _update_tile_highlights(self):
        """Updates visual highlights on tiles during reorder"""
        if not self.is_active or not self.launcher.tiles:
            return
        
        num_apps = len(self.launcher.apps)
        
        for i, tile in enumerate(self.launcher.tiles):
            app_idx = tile.app_index
            
            # Selected tile - bright gold border
            if app_idx == self.selected_index:
                tile.image_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: #1a1a1a;
                        border: {self.launcher.scaling.scale(5)}px solid #FFD700;
                        border-radius: {tile.border_radius}px;
                        color: #ffffff;
                        font-size: {self.launcher.scaling.scale_font(18)}px;
                        font-weight: 600;
                    }}
                """)
            # Target position - blue border
            elif app_idx == self.target_index:
                tile.image_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: #1a1a1a;
                        border: {self.launcher.scaling.scale(5)}px solid #00BFFF;
                        border-radius: {tile.border_radius}px;
                        color: #ffffff;
                        font-size: {self.launcher.scaling.scale_font(18)}px;
                        font-weight: 600;
                    }}
                """)
            # Normal tiles
            else:
                tile.image_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: #1a1a1a;
                        border: {self.launcher.scaling.scale(2)}px solid #444;
                        border-radius: {tile.border_radius}px;
                        color: #cccccc;
                        font-size: {self.launcher.scaling.scale_font(18)}px;
                        font-weight: 600;
                    }}
                """)
        
        # Update position numbers
        self._add_position_numbers()    
    def move_left(self):
        """Moves target position left"""
        if not self.is_active:
            return False
        
        num_apps = len(self.launcher.apps)
        
        if num_apps <= 5:
            # Linear movement
            if self.target_index > 0:
                self.target_index -= 1
                # Don't animate, just update highlights
                self._update_tile_highlights()
                return True
        else:
            # Circular movement - update target BEFORE animation
            new_target = (self.target_index - 1) % num_apps
            self.target_index = new_target
            self.launcher.current_index = self.target_index
            self.launcher.animate_carousel("left")
            # Highlights will update after animation
            QTimer.singleShot(260, self._update_tile_highlights)
            return True
        
        return False
    
    def move_right(self):
        """Moves target position right"""
        if not self.is_active:
            return False
        
        num_apps = len(self.launcher.apps)
        
        if num_apps <= 5:
            # Linear movement
            if self.target_index < num_apps - 1:
                self.target_index += 1
                # Don't animate, just update highlights
                self._update_tile_highlights()
                return True
        else:
            # Circular movement - update target BEFORE animation
            new_target = (self.target_index + 1) % num_apps
            self.target_index = new_target
            self.launcher.current_index = self.target_index
            self.launcher.animate_carousel("right")
            # Highlights will update after animation
            QTimer.singleShot(260, self._update_tile_highlights)
            return True
        
        return False
    
    def confirm_reorder(self):
        """Confirms and applies the reorder"""
        if not self.is_active:
            return False
        
        # Set flag IMMEDIATELY to block any other handlers
        self.recently_exited = True
        
        if self.selected_index != self.target_index:
            # Perform the reorder
            app_to_move = self.launcher.apps.pop(self.selected_index)
            self.launcher.apps.insert(self.target_index, app_to_move)
            
            # Update current index to follow the moved app
            self.launcher.current_index = self.target_index
            
            # Save and rebuild
            self.launcher.save_config()
            
            print(f"✅ Moved '{app_to_move['name']}' from position {self.selected_index} to {self.target_index}")
        
        self._exit_reorder()
        # Rebuild AFTER exiting to avoid triggering reorder mode again
        self.launcher.build_infinite_carousel()
        
        # Longer cooldown after confirm to prevent accidental launch
        self.exit_cooldown_timer.start(1000)  # 1 second cooldown
        return True
    
    def cancel_reorder(self):
        """Cancels reorder mode without changes"""
        if not self.is_active:
            return False
        
        # Return to original position
        original_index = self.selected_index
        
        print("❌ Reorder cancelled")
        self._exit_reorder()
        
        # Rebuild AFTER exiting
        self.launcher.current_index = original_index
        self.launcher.build_infinite_carousel()
        return True
    
    def _exit_reorder(self):
        """Exits reorder mode and cleans up"""
        self.is_active = False
        self.selected_index = None
        self.target_index = None
        self._hide_reorder_ui()
        
        # Set cooldown to prevent immediate reactivation
        self.recently_exited = True
        self.exit_cooldown_timer.start(500)  # 500ms cooldown
        
        # Force stop any timers
        self.cancel_long_press()
    
    def handle_joypad_button(self, button_index):
        """Handles joypad button for reorder mode - RB button (5) toggles"""
        current_time = time.time()
        if button_index in self.last_button_times and current_time - self.last_button_times[button_index] < 0.3:
            return False
        self.last_button_times[button_index] = current_time

        # RB button toggles reorder mode
        if button_index in (5, 10):  # RB button
            # Don't activate if dialog is open or in menu
            if self._is_dialog_active() or self.launcher.is_in_menu:
                #print("🚫 Reorder blocked - dialog or menu active")
                return False
                
            if not self.is_active:
                if self.launcher.apps and not self.recently_exited:
                    self._activate_reorder()
                    return True
            else:
                self.cancel_reorder()
                return True
        
        return False


def integrate_reorder_mode(launcher):
    """
    Integrates reorder mode into the launcher.
    Call this from TVLauncher.__init__() after self.init_ui()
    
    Usage:
        from app_reorder import integrate_reorder_mode
        # In TVLauncher.__init__:
        integrate_reorder_mode(self)
    """
    launcher.reorder_mode = ReorderMode(launcher)
    
    # Store original keyPressEvent
    original_key_press = launcher.keyPressEvent
    
    def enhanced_key_press(event):
        """Enhanced keyPressEvent with reorder support"""
        if event.isAutoRepeat():
            original_key_press(event)
            return
        
        key = event.key()
        
        # R key toggles reorder mode
        if key == Qt.Key.Key_R:
            # Don't activate if dialog is open or in menu
            if launcher.reorder_mode._is_dialog_active() or launcher.is_in_menu:
                #print("🚫 Reorder blocked - dialog or menu active")
                original_key_press(event)
                return
                
            if not launcher.reorder_mode.is_active:
                if launcher.apps and not launcher.reorder_mode.recently_exited:
                    launcher.reorder_mode._activate_reorder()
            else:
                launcher.reorder_mode.cancel_reorder()
            return
        
        # In reorder mode, intercept navigation
        if launcher.reorder_mode.is_active:
            if key == Qt.Key.Key_Left:
                if launcher.reorder_mode.move_left():
                    return
            elif key == Qt.Key.Key_Right:
                if launcher.reorder_mode.move_right():
                    return
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if launcher.reorder_mode.confirm_reorder():
                    return
            elif key == Qt.Key.Key_Escape:
                if launcher.reorder_mode.cancel_reorder():
                    return
        else:
            # Long press detection for Enter key (only if not in menu/dialog)
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not launcher.is_in_menu and not launcher.reorder_mode._is_dialog_active():
                    launcher.reorder_mode.start_long_press()
        
        # Pass to original handler
        original_key_press(event)
    
    # Store original keyReleaseEvent if it exists
    original_key_release = getattr(launcher, 'keyReleaseEvent', None)
    
    def enhanced_key_release(event):
        """Enhanced keyReleaseEvent for long press detection"""
        if event.isAutoRepeat():
            return
        
        key = event.key()
        
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not launcher.reorder_mode.is_active:
                launcher.reorder_mode.cancel_long_press()
        
        if original_key_release:
            original_key_release(event)
    
    # Store original launch_current_app to cancel timers
    original_launch = launcher.launch_current_app
    
    def enhanced_launch():
        """Enhanced launch that cancels all reorder timers"""
        # Force cancel any pending reorder activation
        launcher.reorder_mode.force_cancel_all_timers()
        launcher.reorder_mode.recently_exited = False
        # Call original launch
        original_launch()
    
    launcher.launch_current_app = enhanced_launch
    
    # Store original handle_button
    original_handle_button = launcher.handle_button
    
    def enhanced_handle_button(button_index):
        """Enhanced button handler with reorder support"""
        # CRITICAL: Block all button handling during cooldown
        if launcher.reorder_mode.recently_exited:
            #print(f"🚫 Button {button_index} blocked during cooldown")
            return
        
        # In reorder mode, handle A and B buttons specially
        if launcher.reorder_mode.is_active:
            if button_index == 0:  # A button - confirm reorder
                print("✅ A button pressed in reorder mode - confirming")
                launcher.reorder_mode.confirm_reorder()
                return  # Don't pass to original handler
            elif button_index == 1:  # B button - cancel reorder
                print("❌ B button pressed in reorder mode - canceling")
                launcher.reorder_mode.cancel_reorder()
                return  # Don't pass to original handler
        
        # RB button (button 5) toggles reorder mode
        if launcher.reorder_mode.handle_joypad_button(button_index):
            return
        
        # Pass to original handler if not handled by reorder mode
        original_handle_button(button_index)
    
    # Store original handle_navigation and enhance it for controller support in reorder mode
    if hasattr(launcher, 'handle_navigation'):
        original_handle_navigation = launcher.handle_navigation
        
        def enhanced_handle_navigation(direction):
            """Enhanced navigation handler with reorder support"""
            if launcher.reorder_mode.is_active:
                if direction == "left":
                    return launcher.reorder_mode.move_left()
                elif direction == "right":
                    return launcher.reorder_mode.move_right()
                return False
            else:
                original_handle_navigation(direction)
        
        launcher.handle_navigation = enhanced_handle_navigation
    
    # Replace methods
    launcher.keyPressEvent = enhanced_key_press
    launcher.keyReleaseEvent = enhanced_key_release
    launcher.handle_button = enhanced_handle_button
    
    # Update instructions label
    if hasattr(launcher, 'findChild'):
        instructions = launcher.findChildren(QLabel)
        for label in instructions:
            if "Navigate:" in label.text():
                label.setText(
                    "Navigate: ← → ↑ ↓ | Launch: Enter/A | Edit: E | Delete: Del/Y | "
                    "Reorder: R/RB | Search: F/LB | Exit: Esc/B"
                )
                label.setStyleSheet(f"""
                    color: rgba(255, 255, 255, 0.3);
                    font-size: {launcher.scaling.scale_font(11)}px;
                    background: transparent;
                """)
                break
