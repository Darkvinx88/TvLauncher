"""
Mouse / Touch Manager Module
Aggiunge supporto mouse e touchscreen al launcher, senza modificare gli altri moduli.

Funzionalità:
- Click su una tile non focalizzata -> la seleziona (carousel si sposta su di essa)
- Click su una tile già focalizzata -> lancia l'app (equivalente a Enter)
- Doppio click su una tile -> lancia sempre l'app, indipendentemente dal focus
- Drag orizzontale / swipe sul carosello (mouse o touch) -> naviga tra le app
- Rotellina del mouse sul carosello -> naviga tra le app
- Cursore "a manina" su tile e pulsanti per un feedback visivo migliore
- Tap sui pulsanti del menu (restart/sleep/shutdown/close) già funzionanti di default
  (QPushButton li supporta nativamente), qui vengono solo uniformati col cursore pointer

Uso in tvlauncher.py:
    from modules.mouse_touch_manager import integrate_mouse_touch
    ...
    self.mouse_touch = integrate_mouse_touch(self)   # da chiamare dopo aver creato carousel_container e menu_buttons
"""

from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QCursor


# Soglia in pixel oltre la quale un drag viene considerato uno swipe (e non un semplice click)
SWIPE_THRESHOLD = 40


class MouseTouchManager:
    """Aggiunge interazione mouse/touch alla carousel e alla UI del launcher."""

    def __init__(self, launcher):
        self.launcher = launcher
        self._drag_start_pos = None
        self._drag_start_index = None
        self._dragged = False

        self._patch_build_infinite_carousel()
        self._enable_carousel_drag_and_wheel()
        self._enable_menu_buttons_cursor()

        # Se il carosello è già stato costruito prima dell'integrazione, applica subito le tile
        if getattr(launcher, "tiles", None):
            self._attach_tile_handlers()

    # ------------------------------------------------------------------
    # Tile: click per selezionare / lanciare
    # ------------------------------------------------------------------

    def _patch_build_infinite_carousel(self):
        """Fa in modo che ogni volta che il carosello viene ricostruito,
        le nuove tile ricevano automaticamente il supporto al mouse."""
        launcher = self.launcher
        original_build = launcher.build_infinite_carousel

        def patched_build(*args, **kwargs):
            result = original_build(*args, **kwargs)
            self._attach_tile_handlers()
            return result

        launcher.build_infinite_carousel = patched_build

    def _attach_tile_handlers(self):
        launcher = self.launcher
        for tile in launcher.tiles:
            tile.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # Rimuove eventuali handler precedenti prima di riassegnare
            tile.mousePressEvent = self._make_tile_mouse_press(tile)
            tile.mouseDoubleClickEvent = self._make_tile_double_click(tile)

    def _make_tile_mouse_press(self, tile):
        def handler(event):
            if event.button() != Qt.MouseButton.LeftButton:
                return
            launcher = self.launcher
            if not launcher.inputs_enabled or launcher.is_animating:
                return
            if launcher.progress_dialog and launcher.progress_dialog.isVisible():
                return

            app_index = getattr(tile, "app_index", None)
            if app_index is None:
                return

            # Se si è in menu (pulsanti in basso focalizzati), il click su una tile
            # riporta il focus sul carosello, sulla app selezionata
            if launcher.is_in_menu:
                launcher.is_in_menu = False
                launcher._reset_menu_styles()

            if app_index == launcher.current_index:
                # Tile già selezionata: click = lancio app (come premere Enter)
                launcher.sound_manager.select()
                launcher.launch_current_app()
            else:
                # Tile non selezionata: click = selezione (come navigare con le frecce)
                launcher.sound_manager.navigate()
                launcher.current_index = app_index
                launcher.build_infinite_carousel()

        return handler

    def _make_tile_double_click(self, tile):
        def handler(event):
            if event.button() != Qt.MouseButton.LeftButton:
                return
            launcher = self.launcher
            if not launcher.inputs_enabled or launcher.is_animating:
                return
            app_index = getattr(tile, "app_index", None)
            if app_index is None:
                return
            # Doppio click: seleziona (se serve) e lancia subito, utile su touchscreen
            if app_index != launcher.current_index:
                launcher.current_index = app_index
                launcher.build_infinite_carousel()
            launcher.sound_manager.select()
            launcher.launch_current_app()

        return handler

    # ------------------------------------------------------------------
    # Carosello: drag/swipe e rotellina del mouse
    # ------------------------------------------------------------------

    def _enable_carousel_drag_and_wheel(self):
        launcher = self.launcher
        container = launcher.carousel_container
        container.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        container.mousePressEvent = self._container_mouse_press
        container.mouseMoveEvent = self._container_mouse_move
        container.mouseReleaseEvent = self._container_mouse_release
        container.wheelEvent = self._container_wheel

    def _container_mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag_start_pos = event.position() if hasattr(event, "position") else event.pos()
        self._drag_start_index = self.launcher.current_index
        self._dragged = False
        self.launcher.carousel_container.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def _container_mouse_move(self, event):
        if self._drag_start_pos is None:
            return
        current_pos = event.position() if hasattr(event, "position") else event.pos()
        delta_x = current_pos.x() - self._drag_start_pos.x()
        if abs(delta_x) > SWIPE_THRESHOLD:
            self._dragged = True

    def _container_mouse_release(self, event):
        launcher = self.launcher
        launcher.carousel_container.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        if self._drag_start_pos is None:
            return

        current_pos = event.position() if hasattr(event, "position") else event.pos()
        delta_x = current_pos.x() - self._drag_start_pos.x()

        self._drag_start_pos = None

        if not launcher.inputs_enabled or launcher.is_animating:
            return
        if not launcher.apps:
            return

        if abs(delta_x) > SWIPE_THRESHOLD:
            if delta_x < 0:
                self._navigate("right")
            else:
                self._navigate("left")

    def _container_wheel(self, event):
        launcher = self.launcher
        if not launcher.inputs_enabled or launcher.is_animating or not launcher.apps:
            return
        delta = event.angleDelta().y()
        if delta == 0:
            delta = event.angleDelta().x()
        if delta < 0:
            self._navigate("right")
        elif delta > 0:
            self._navigate("left")

    def _navigate(self, direction):
        """Replica la logica di navigazione usata da keyPressEvent (frecce sinistra/destra)."""
        launcher = self.launcher
        num_apps = len(launcher.apps)
        if num_apps == 0:
            return

        if direction == "right":
            if num_apps <= 5:
                if launcher.current_index < num_apps - 1:
                    launcher.current_index += 1
                    launcher.animate_carousel("right")
            else:
                launcher.current_index = (launcher.current_index + 1) % num_apps
                launcher.animate_carousel("right")
        else:
            if num_apps <= 5:
                if launcher.current_index > 0:
                    launcher.current_index -= 1
                    launcher.animate_carousel("left")
            else:
                launcher.current_index = (launcher.current_index - 1) % num_apps
                launcher.animate_carousel("left")

    # ------------------------------------------------------------------
    # Pulsanti menu (restart/sleep/shutdown/close): solo cursore pointer,
    # il click è già gestito nativamente da QPushButton
    # ------------------------------------------------------------------

    def _enable_menu_buttons_cursor(self):
        launcher = self.launcher
        if not hasattr(launcher, "menu_buttons"):
            return
        for _action, btn in launcher.menu_buttons:
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


def integrate_mouse_touch(launcher):
    """Punto di ingresso da chiamare in tvlauncher.py dopo la costruzione della UI
    (carousel_container e menu_buttons devono già esistere)."""
    return MouseTouchManager(launcher)
