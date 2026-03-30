import os
import random
from pathlib import Path
from PyQt6.QtWidgets import QLabel, QFileDialog, QApplication, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, Qt
from PyQt6.QtGui import QPixmap, QBrush


class BackgroundManager:
    """Gestisce background, animazioni e auto-change wallpaper per Linux"""
    
    def __init__(self, parent, config_data, assets_dir):
        
        self.parent = parent
        self.assets_dir = Path(assets_dir)
        
        # Configurazione
        self.background_image = config_data.get('background', '')
        self.auto_change_wallpaper = config_data.get('auto_change_wallpaper', False)
        self.wallpaper_interval = 300000  # 5 minuti default (in millisecondi)
        
        # Cartella wallpapers
        self.wallpaper_folder = self.assets_dir / 'wallpapers'
        self.wallpaper_folder.mkdir(parents=True, exist_ok=True)
        
        # Animazioni
        self.fade_widget = None
        self.fade_animation = None
        self.pending_background = None
        
        # Timer per auto-change
        self.wallpaper_timer = None
        self.overlay = None
        
    def initialize(self, overlay=None):
        """
        Inizializza il background
        
        Args:
            overlay: Widget overlay da tenere in considerazione per lo stacking
        """
        self.overlay = overlay
        self.update_background(fade=False)
        
        # Avvia auto-change se abilitato
        if self.auto_change_wallpaper:
            self.start_wallpaper_rotation()
    
    def update_background(self, fade=False):
        """
        Aggiorna lo sfondo della finestra
        
        Args:
            fade: Se True, applica transizione fade
        """
        if self.background_image and Path(self.background_image).exists():
            if fade:
                self._fade_to_background(self.background_image)
            else:
                self._set_scaled_background(self.background_image)
        else:
            # Default: usa uno sfondo dalla cartella assets/wallpapers
            default_wallpaper = self.wallpaper_folder / 'default.jpg'
            if default_wallpaper.exists():
                if fade:
                    self._fade_to_background(str(default_wallpaper))
                else:
                    self._set_scaled_background(str(default_wallpaper))
            else:
                # Fallback: sfondo grigio scuro
                self._set_fallback_background()
    
    def _set_fallback_background(self):
        """Applica sfondo di fallback quando non ci sono immagini"""
        self.parent.setStyleSheet("""
            QMainWindow {
                background-color: #2a2a2a;
            }
        """)
        if self.overlay:
            self.overlay.setStyleSheet("background-color: transparent;")
    
    def _fade_to_background(self, image_path):
        """
        Transizione fade verso un nuovo sfondo
        
        Args:
            image_path: Percorso dell'immagine da caricare
        """
        # Se c'è già una transizione in corso, completala immediatamente
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()
            if self.fade_widget:
                self.fade_widget.deleteLater()
                self.fade_widget = None
        
        # Crea widget per il nuovo sfondo
        screen = QApplication.primaryScreen().geometry()
        self.fade_widget = QLabel(self.parent)
        self.fade_widget.setGeometry(0, 0, screen.width(), screen.height())
        self.fade_widget.setScaledContents(True)
        
        # Carica e scala l'immagine
        pixmap = QPixmap(image_path)
        scaled_pixmap = self._scale_pixmap_to_screen(pixmap, screen)
        self.fade_widget.setPixmap(scaled_pixmap)
        
        # Posiziona sotto l'overlay ma sopra lo sfondo
        self.fade_widget.lower()
        if self.overlay:
            self.fade_widget.stackUnder(self.overlay)
        
        # Crea effetto opacità
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0)
        self.fade_widget.setGraphicsEffect(opacity_effect)
        
        self.fade_widget.show()
        
        # Salva il percorso per applicarlo dopo il fade
        self.pending_background = image_path
        
        # Anima l'opacità da 0 a 1
        self.fade_animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_animation.setDuration(800)  # 800ms - dissolvenza fluida
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Quando finisce l'animazione, applica lo sfondo reale
        self.fade_animation.finished.connect(self._on_fade_finished)
        self.fade_animation.start()
    
    def _on_fade_finished(self):
        """Chiamato quando la transizione fade è completata"""
        # Applica lo sfondo reale
        if self.pending_background:
            self._set_scaled_background(self.pending_background)
            self.pending_background = None
        
        # Rimuovi il widget di transizione
        if self.fade_widget:
            self.fade_widget.deleteLater()
            self.fade_widget = None
        
        self.fade_animation = None
    
    def _set_scaled_background(self, image_path):
        """
        Imposta uno sfondo scalato per riempire la finestra
        
        Args:
            image_path: Percorso dell'immagine
        """
        screen = QApplication.primaryScreen().geometry()
        pixmap = QPixmap(image_path)
        
        # Scala il pixmap per riempire lo schermo
        scaled_pixmap = self._scale_pixmap_to_screen(pixmap, screen)
        
        # Applica lo sfondo usando QPalette
        palette = self.parent.palette()
        brush = QBrush(scaled_pixmap)
        palette.setBrush(self.parent.backgroundRole(), brush)
        self.parent.setPalette(palette)
        
        # Applica overlay scuro per migliorare leggibilità
        if self.overlay:
            self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
    
    def _scale_pixmap_to_screen(self, pixmap, screen):
        """
        Scala un pixmap per riempire lo schermo (cover mode)
        
        Args:
            pixmap: QPixmap da scalare
            screen: QRect con dimensioni dello schermo
            
        Returns:
            QPixmap scalato e centrato
        """
        # Scala il pixmap per riempire lo schermo (equivalente di background-size: cover)
        scaled_pixmap = pixmap.scaled(
            screen.width(), 
            screen.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Centra il pixmap se è più grande dello schermo
        if scaled_pixmap.width() > screen.width() or scaled_pixmap.height() > screen.height():
            x = (scaled_pixmap.width() - screen.width()) // 2
            y = (scaled_pixmap.height() - screen.height()) // 2
            scaled_pixmap = scaled_pixmap.copy(x, y, screen.width(), screen.height())
        
        return scaled_pixmap
    
    # ==================== GESTIONE WALLPAPER ====================
    
    def set_background_from_dialog(self):
        """
        Apre dialog per scegliere sfondo manualmente
        
        Returns:
            bool: True se sfondo cambiato, False altrimenti
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Select Background Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
        )
        
        if file_path:
            self.background_image = file_path
            
            # Disattiva il cambio automatico quando si sceglie uno sfondo manuale
            if self.auto_change_wallpaper:
                self.auto_change_wallpaper = False
                self.stop_wallpaper_rotation()
            
            self.update_background(fade=True)
            return True
        
        return False
    
    def start_wallpaper_rotation(self):
        """Avvia il timer per il cambio automatico dello sfondo"""
        if not self.auto_change_wallpaper:
            return
            
        # Cambia subito con fade
        self.change_random_wallpaper()
        
        # Avvia timer
        self.wallpaper_timer = QTimer()
        self.wallpaper_timer.timeout.connect(self.change_random_wallpaper)
        self.wallpaper_timer.start(self.wallpaper_interval)
    
    def stop_wallpaper_rotation(self):
        """Ferma il timer per il cambio automatico dello sfondo"""
        if self.wallpaper_timer:
            self.wallpaper_timer.stop()
            self.wallpaper_timer = None
    
    def change_random_wallpaper(self):
        """Cambia lo sfondo con uno casuale dalla cartella"""
        if not self.wallpaper_folder.exists():
            print(f"⚠️ Wallpaper folder not found: {self.wallpaper_folder}")
            return
        
        # Trova tutti i file immagine
        wallpapers = (
            list(self.wallpaper_folder.glob("*.jpg")) + 
            list(self.wallpaper_folder.glob("*.png")) + 
            list(self.wallpaper_folder.glob("*.jpeg"))
        )
        
        if not wallpapers:
            print(f"⚠️ No wallpapers found in {self.wallpaper_folder}")
            return
        
        # Scegli uno sfondo casuale (evitando quello corrente se possibile)
        if len(wallpapers) > 1 and self.background_image:
            current = Path(self.background_image)
            wallpapers = [w for w in wallpapers if w != current]
        
        random_wallpaper = random.choice(wallpapers)
        
        # Imposta lo sfondo con fade
        self.background_image = str(random_wallpaper)
        self.update_background(fade=True)
    
    def toggle_wallpaper_rotation(self, enabled):
        """
        Attiva/disattiva il cambio automatico sfondo
        
        Args:
            enabled: True per attivare, False per disattivare
        """
        self.auto_change_wallpaper = enabled
        
        if enabled:
            self.start_wallpaper_rotation()
        else:
            self.stop_wallpaper_rotation()
    
    def set_wallpaper_interval(self, interval_seconds):
        """
        Imposta l'intervallo di cambio wallpaper
        
        Args:
            interval_seconds: Intervallo in secondi
        """
        self.wallpaper_interval = interval_seconds * 1000  # Converti in millisecondi
        
        # Riavvia timer se attivo
        if self.wallpaper_timer and self.wallpaper_timer.isActive():
            self.stop_wallpaper_rotation()
            self.start_wallpaper_rotation()
    
    # ==================== CONFIGURAZIONE ====================
    
    def get_config(self):
        """
        Ritorna la configurazione corrente
        
        Returns:
            dict: Configurazione background
        """
        return {
            'background': self.background_image,
            'auto_change_wallpaper': self.auto_change_wallpaper,
            'wallpaper_interval': self.wallpaper_interval
        }
    
    def load_config(self, config_data):
        """
        Carica configurazione
        
        Args:
            config_data: Dict con configurazione
        """
        self.background_image = config_data.get('background', '')
        self.auto_change_wallpaper = config_data.get('auto_change_wallpaper', False)
        self.wallpaper_interval = config_data.get('wallpaper_interval', 300000)
    
    # ==================== CLEANUP ====================
    
    def cleanup(self):
        """Pulisce risorse quando si chiude l'applicazione"""
        self.stop_wallpaper_rotation()
        
        # Ferma animazioni in corso
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()
        
        # Rimuovi widget di fade
        if self.fade_widget:
            self.fade_widget.deleteLater()
            self.fade_widget = None
