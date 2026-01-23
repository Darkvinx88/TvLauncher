"""
Effetti visivi per le tile del launcher - Solo Dual Pulse
"""

from PyQt6.QtCore import QTimer, QRectF
from PyQt6.QtGui import QColor, QPainterPath, QRegion
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
import math


class TileGlowEffect:
    """Effetto dual pulse: bordo bianco + ombra colorata pulsanti"""
    
    def __init__(self, tile, scaling):
        self.tile = tile
        self.scaling = scaling
        self.timer = None
        self.is_active = False
        self.time = 0
        self.duration = 1500  # ms per ciclo completo
        
        # ✨ NUOVO: Shadow separato per il glow (applicato alla TILE intera, non all'image_label)
        self.glow_shadow = None
        
    def start(self):
        """Avvia l'effetto"""
        if self.is_active:
            return
            
        self.is_active = True
        self.time = 0
        
        # ✨ Porta la tile in primo piano
        if self.tile:
            self.tile.raise_()
        
        # ✨ CRITICAL: Crea un shadow SEPARATO per il glow sulla TILE intera
        self.glow_shadow = QGraphicsDropShadowEffect()
        self.glow_shadow.setBlurRadius(self.scaling.scale(20))  # ✨ Ridotto a 20px per evitare clipping
        self.glow_shadow.setXOffset(0)
        self.glow_shadow.setYOffset(0)  # ✨ ZERO per glow uniforme tutto intorno!
        self.glow_shadow.setColor(QColor(100, 150, 255, 0))  # Inizia trasparente
        
        # Applica il glow shadow alla TILE intera (non all'image_label!)
        self.tile.setGraphicsEffect(self.glow_shadow)
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_effect)
        self.timer.start(16)  # ~60 FPS
        
    def _update_effect(self):
        """Aggiorna l'effetto dual pulse"""
        try:
            # CHECK: Se la tile non è più focused, STOP
            if not self.tile or not hasattr(self.tile, 'is_focused') or not self.tile.is_focused:
                self.stop()
                return
            
            if not self.is_active:
                return
            
            if not hasattr(self.tile, 'image_label'):
                self.stop()
                return
            
            self.time += 16  # milliseconds
            
            # Funzione sinusoidale per il pulsare (0 to 1 to 0)
            progress = (self.time % self.duration) / self.duration
            pulse = (math.sin(progress * 2 * math.pi - math.pi / 2) + 1) / 2  # 0.0 to 1.0
            
            # ========================================
            # 🎨 DUAL PULSE: Bordo + Ombra sincronizzati
            # ========================================
            border_opacity = 0.5 + (pulse * 0.5)  # 50% → 100%
            shadow_blur = self.scaling.scale(20 + int(pulse * 15))  # 20-35px (più contenuto)
            
            border_width = self.scaling.scale(3)
            border_radius = self.tile.border_radius
            border_color = f"rgba(255, 255, 255, {border_opacity})"
            
            # Applica bordo pulsante all'image_label
            self.tile.image_label.setStyleSheet(f"""
                QLabel {{
                    background-color: #1a1a1a;
                    border: {border_width}px solid {border_color};
                    border-radius: {border_radius}px;
                    color: #ffffff;
                    font-size: {self.scaling.scale_font(18)}px;
                    font-weight: 600;
                }}
            """)
            
            # ✨ Ombra colorata pulsante sulla TILE intera - UNIFORME (offset 0,0)
            if self.glow_shadow:
                self.glow_shadow.setBlurRadius(shadow_blur)
                self.glow_shadow.setXOffset(0)  # ✨ ZERO
                self.glow_shadow.setYOffset(0)  # ✨ ZERO per glow uniforme!
                
                # Colore ombra: blu con alpha pulsante (più intenso per compensare blur minore)
                shadow_color = QColor(100, 150, 255, int(pulse * 240))  # ✨ 240 invece di 220
                self.glow_shadow.setColor(shadow_color)
            
            # ✨ L'ombra nera originale NON serve durante il glow, la rimuoviamo
            # (verrà ripristinata nello stop())
        
        except (RuntimeError, AttributeError):
            self.stop()
    
    def stop(self):
        """Ferma l'effetto e ripristina lo stato normale"""
        if not self.is_active:
            return
            
        self.is_active = False
        
        # Stop timer
        if self.timer:
            try:
                self.timer.stop()
                self.timer.deleteLater()
            except:
                pass
            finally:
                self.timer = None
        
        # ✨ Rimuovi il glow shadow dalla tile intera
        if self.glow_shadow:
            try:
                self.glow_shadow.deleteLater()
            except:
                pass
            self.glow_shadow = None
        
        # ✨ Rimuovi il graphics effect dalla tile (altrimenti resta trasparente)
        if self.tile:
            self.tile.setGraphicsEffect(None)
        
        # Ripristina lo stile normale
        try:
            if self.tile and hasattr(self.tile, 'image_label'):
                border_radius = self.tile.border_radius
                
                if self.tile.is_focused:
                    # Ripristina bordo normale focused
                    self.tile.image_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: #1a1a1a;
                            border: {self.scaling.scale(3)}px solid #ffffff;
                            border-radius: {border_radius}px;
                            color: #ffffff;
                            font-size: {self.scaling.scale_font(18)}px;
                            font-weight: 600;
                        }}
                    """)
                else:
                    # Ripristina stile unfocused
                    self.tile.image_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: #1a1a1a;
                            border-radius: {border_radius}px;
                            color: #cccccc;
                            font-size: {self.scaling.scale_font(18)}px;
                            font-weight: 600;
                        }}
                    """)
                
                # Ripristina il shadow normale dell'image_label (grigio)
                if hasattr(self.tile, 'shadow'):
                    if self.tile.is_focused:
                        self.tile.shadow.setBlurRadius(self.scaling.scale(25))
                        self.tile.shadow.setYOffset(self.scaling.scale(8))
                        self.tile.shadow.setColor(QColor(0, 0, 0, 180))
                    else:
                        self.tile.shadow.setBlurRadius(self.scaling.scale(15))
                        self.tile.shadow.setYOffset(self.scaling.scale(4))
                        self.tile.shadow.setColor(QColor(0, 0, 0, 180))
                    
                    self.tile.image_label.setGraphicsEffect(self.tile.shadow)
        except (RuntimeError, AttributeError):
            pass