"""
Effetti visivi per le tile del launcher - Solo Dual Pulse
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QWidget

import math


class TileGlowEffect:
    """Effetto dual pulse: bordo bianco + ombra colorata pulsanti.

    Il glow shadow viene applicato a un QWidget overlay con background
    colorato posizionato SOTTO la tile (stessa geometria dell'image_label),
    così il blur si propaga all'esterno senza influenzare il layout della
    tile stessa. Fix per la deformazione a DPI >= 125%.
    """

    def __init__(self, tile, scaling):
        self.tile = tile
        self.scaling = scaling
        self.timer = None
        self.is_active = False
        self.time = 0
        self.duration = 1500  # ms per ciclo completo
        self.glow_shadow = None
        self._overlay = None

    def _create_overlay(self):
        """Crea un widget colorato fratello della tile, posizionato SOTTO di essa.
        Ha lo stesso border-radius dell'image_label così il bagliore segue
        la forma arrotondata.
        """
        parent = self.tile.parent()
        if parent is None:
            return None

        border_radius = self.tile.border_radius

        overlay = QWidget(parent)
        overlay.setAttribute(
            __import__('PyQt6.QtCore', fromlist=['Qt']).Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True
        )
        # Background scuro con border-radius — dà una superficie solida al DropShadow
        overlay.setStyleSheet(f"""
            QWidget {{
                background-color: #1a1a1a;
                border-radius: {border_radius}px;
            }}
        """)

        # Geometria uguale all'image_label in coordinate del parent del carousel
        img = self.tile.image_label
        img_pos = img.mapTo(parent, img.rect().topLeft())
        overlay.setGeometry(img_pos.x(), img_pos.y(), img.width(), img.height())

        # Metti l'overlay SOTTO la tile nello z-order
        overlay.lower()
        self.tile.raise_()
        overlay.show()
        return overlay

    def _update_overlay_geometry(self):
        """Aggiorna posizione/dimensione overlay se la tile si è spostata."""
        if not self._overlay or not self.tile:
            return
        parent = self.tile.parent()
        if parent is None:
            return
        img = self.tile.image_label
        img_pos = img.mapTo(parent, img.rect().topLeft())
        self._overlay.setGeometry(img_pos.x(), img_pos.y(), img.width(), img.height())

    def start(self):
        """Avvia l'effetto."""
        if self.is_active:
            return

        self.is_active = True
        self.time = 0

        if self.tile:
            self.tile.raise_()

        self._overlay = self._create_overlay()

        if self._overlay is not None:
            self.glow_shadow = QGraphicsDropShadowEffect()
            self.glow_shadow.setBlurRadius(self.scaling.scale(20))
            self.glow_shadow.setXOffset(0)
            self.glow_shadow.setYOffset(0)
            self.glow_shadow.setColor(QColor(100, 150, 255, 0))  # inizia trasparente
            self._overlay.setGraphicsEffect(self.glow_shadow)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_effect)
        self.timer.start(16)  # ~60 FPS

    def _update_effect(self):
        """Aggiorna l'effetto dual pulse."""
        try:
            if not self.tile or not hasattr(self.tile, 'is_focused') or not self.tile.is_focused:
                self.stop()
                return

            if not self.is_active:
                return

            if not hasattr(self.tile, 'image_label'):
                self.stop()
                return

            # Tieni l'overlay allineato alla tile
            self._update_overlay_geometry()

            self.time += 16

            progress = (self.time % self.duration) / self.duration
            pulse = (math.sin(progress * 2 * math.pi - math.pi / 2) + 1) / 2  # 0.0 → 1.0

            border_opacity = 0.5 + (pulse * 0.5)   # 50% → 100%
            shadow_blur = self.scaling.scale(20 + int(pulse * 15))  # 20–35 px

            border_width = self.scaling.scale(3)
            border_radius = self.tile.border_radius
            border_color = f"rgba(255, 255, 255, {border_opacity})"

            # Bordo pulsante sull'image_label
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

            # Glow sull'overlay — nessuna deformazione della tile
            if self.glow_shadow:
                self.glow_shadow.setBlurRadius(shadow_blur)
                self.glow_shadow.setXOffset(0)
                self.glow_shadow.setYOffset(0)
                self.glow_shadow.setColor(QColor(100, 150, 255, int(pulse * 240)))

        except (RuntimeError, AttributeError):
            self.stop()

    def stop(self):
        """Ferma l'effetto e ripristina lo stato normale."""
        if not self.is_active:
            return

        self.is_active = False

        if self.timer:
            try:
                self.timer.stop()
                self.timer.deleteLater()
            except Exception:
                pass
            finally:
                self.timer = None

        if self._overlay:
            try:
                self._overlay.hide()
                self._overlay.deleteLater()
            except Exception:
                pass
            finally:
                self._overlay = None
                self.glow_shadow = None

        # Ripristina stile image_label e shadow della tile
        try:
            if self.tile and hasattr(self.tile, 'image_label'):
                border_radius = self.tile.border_radius

                if self.tile.is_focused:
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
                    self.tile.image_label.setStyleSheet(f"""
                        QLabel {{
                            background-color: #1a1a1a;
                            border-radius: {border_radius}px;
                            color: #cccccc;
                            font-size: {self.scaling.scale_font(18)}px;
                            font-weight: 600;
                        }}
                    """)

                if hasattr(self.tile, 'shadow') and self.tile.shadow:
                    if self.tile.is_focused:
                        self.tile.shadow.setBlurRadius(self.scaling.scale(25))
                        self.tile.shadow.setYOffset(self.scaling.scale(8))
                    else:
                        self.tile.shadow.setBlurRadius(self.scaling.scale(15))
                        self.tile.shadow.setYOffset(self.scaling.scale(4))
                    self.tile.shadow.setColor(QColor(0, 0, 0, 180))
                    self.tile.setGraphicsEffect(self.tile.shadow)

        except (RuntimeError, AttributeError):
            pass
