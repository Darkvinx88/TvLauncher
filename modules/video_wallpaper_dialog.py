"""
video_wallpaper_dialog.py

Dialog di configurazione per i Video Wallpaper (streaming stile Projectivy
Overflight). Da agganciare al SettingsMenu esistente con la funzione
add_video_wallpaper_button_to_settings(self) - vedi fondo file.
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QCheckBox, QLineEdit, QScrollArea, QWidget,
    QGridLayout, QMessageBox
)
from PyQt6.QtCore import Qt


QUALITY_LABELS = [
    ("1080p", "1080p"),
    ("1080p_hdr", "1080p HDR"),
    ("4k", "4K"),
    ("4k_hdr", "4K HDR"),
    ("auto", "Automatico (adattivo)"),
]


class VideoWallpaperSettingsDialog(QDialog):
    """Dialog per configurare i video wallpaper in streaming."""

    def __init__(self, parent, video_manager, scaling=None):
        super().__init__(parent)
        self.video_manager = video_manager
        self.scaling = scaling
        self.setWindowTitle("Video Wallpaper")
        self.setModal(True)
        self.resize(600, 680)

        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 14px;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QCheckBox { color: white; }
        """)

        self._category_checkboxes = {}
        self._build_ui()
        self._load_from_manager()

    # ---------------------------------------------------------------

    def _section_title(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #ffffff; margin-top: 8px;")
        return lbl

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Enable
        self.enable_checkbox = QCheckBox("Activate Streaming Video Wallpaper")
        layout.addWidget(self.enable_checkbox)

        info = QLabel(
            "Videos are streamed (no permanent download)."
            
            "Requires an active internet connection."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(info)

        # Qualità
        layout.addWidget(self._section_title("Video Quality"))
        self.quality_combo = QComboBox()
        for key, label in QUALITY_LABELS:
            self.quality_combo.addItem(label, key)
        layout.addWidget(self.quality_combo)

        # Intervallo
        layout.addWidget(self._section_title("Change video every (minutes)"))
        interval_row = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 180)
        self.interval_spin.setSuffix(" min")
        interval_row.addWidget(self.interval_spin)
        interval_row.addStretch()
        layout.addLayout(interval_row)

        # Audio
        self.mute_checkbox = QCheckBox("Muted (Recommended for wallpapers)")
        layout.addWidget(self.mute_checkbox)

        # Categorie
        layout.addWidget(self._section_title("Category (nothing selected = all)"))
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(160)
        cat_scroll.setStyleSheet("QScrollArea { border: 1px solid #444; border-radius: 6px; }")

        cat_container = QWidget()
        cat_grid = QGridLayout(cat_container)
        categories = self.video_manager.get_available_categories()
        for i, cat in enumerate(categories):
            cb = QCheckBox(cat)
            self._category_checkboxes[cat] = cb
            cat_grid.addWidget(cb, i // 2, i % 2)
        cat_scroll.setWidget(cat_container)
        layout.addWidget(cat_scroll)

        # URL catalogo personalizzato
        layout.addWidget(self._section_title("URL JSON catalogue"))
        self.catalog_url_edit = QLineEdit()
        layout.addWidget(self.catalog_url_edit)

        reset_url_btn = QPushButton("Restore default URL (Projectivy Overflight)")
        reset_url_btn.clicked.connect(self._reset_catalog_url)
        layout.addWidget(reset_url_btn)

        # Stato / test
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #ffb74d; font-size: 11px;")
        layout.addWidget(self.status_label)

        test_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh catalogue")
        refresh_btn.clicked.connect(self._refresh_catalog)
        test_row.addWidget(refresh_btn)

        test_btn = QPushButton("Test / Try video")
        test_btn.clicked.connect(self._test_video)
        test_row.addWidget(test_btn)
        layout.addLayout(test_row)

        layout.addStretch()

        # Bottoni finali
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton { background-color: #2a2a2a; border: 1px solid #444; }
            QPushButton:hover { background-color: #3a3a3a; }
        """)
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ---------------------------------------------------------------

    def _load_from_manager(self):
        vm = self.video_manager
        self.enable_checkbox.setChecked(vm.enabled)

        idx = self.quality_combo.findData(vm.quality)
        if idx >= 0:
            self.quality_combo.setCurrentIndex(idx)

        self.interval_spin.setValue(max(1, vm.interval_seconds // 60))
        self.mute_checkbox.setChecked(vm.muted)
        self.catalog_url_edit.setText(vm.catalog_url)

        for cat, cb in self._category_checkboxes.items():
            cb.setChecked(cat in vm.categories)

        if not vm.available and vm.enabled:
            self.status_label.setText(
                f"⚠ mpv not available: {vm.last_error or 'librery not found'}"
            )

    def _reset_catalog_url(self):
        from modules.video_wallpaper_manager import DEFAULT_CATALOG_URL
        self.catalog_url_edit.setText(DEFAULT_CATALOG_URL)

    def _selected_categories(self):
        return [cat for cat, cb in self._category_checkboxes.items() if cb.isChecked()]

    def _refresh_catalog(self):
        self.video_manager.set_catalog_url(self.catalog_url_edit.text().strip())
        self.video_manager._dead_urls.clear()
        self.video_manager._consecutive_failures = 0
        ok = self.video_manager.fetch_catalog(force=True)
        if ok:
            self.status_label.setStyleSheet("color: #81c784; font-size: 11px;")
            self.status_label.setText(
                f"Catalogue downloaded: {len(self.video_manager.catalog)} video. Verifying link in progress..."
            )
            from PyQt6.QtWidgets import QApplication as _QApp
            _QApp.processEvents()

            def _progress(checked, total):
                self.status_label.setText(f"Verifica link: {checked}/{total}...")
                _QApp.processEvents()

            alive, dead = self.video_manager.validate_catalog(progress_callback=_progress)
            self.status_label.setStyleSheet("color: #81c784; font-size: 11px;")
            self.status_label.setText(
                f"✓ Catalogue refreshed: {alive} working videos, {dead} links not available."
            )
        else:
            self.status_label.setStyleSheet("color: #e57373; font-size: 11px;")
            self.status_label.setText(f"✗ {self.video_manager.last_error}")

    def _test_video(self):
        vm = self.video_manager

        # Applica temporaneamente i parametri correnti del dialog per il test
        vm.set_catalog_url(self.catalog_url_edit.text().strip())
        vm.set_quality(self.quality_combo.currentData())
        vm.set_categories(self._selected_categories())
        vm.set_muted(self.mute_checkbox.isChecked())

        if not vm.available:
            if not vm._init_mpv():
                QMessageBox.warning(
                    self, "Video Wallpaper not available.",
                    f"failed to initialize mpv:\n{vm.last_error}\n\n"
                    "Verify python-mpv is installed and libmpv is present."
                )
                return
            vm.resize_to_parent()
            vm.stack_under(getattr(vm, 'overlay', None))

        if not vm.catalog:
            vm.fetch_catalog()

        # Allinea il test allo stesso comportamento della rotazione reale:
        # sospendi lo sfondo statico prima di riprodurre, altrimenti durante
        # il test resta "attivo" sotto e il comportamento visivo differisce
        # da quello che si vede dopo aver premuto Salva.
        if vm.background_manager:
            vm.background_manager.suspend_for_video()

        ok = vm.play_random()
        if ok and vm.current_entry:
            title = vm.current_entry.get('title') or vm.current_entry.get('location') or 'video'
            self.status_label.setStyleSheet("color: #81c784; font-size: 11px;")
            self.status_label.setText(f"▶ Playing now: {title}")
        else:
            self.status_label.setStyleSheet("color: #e57373; font-size: 11px;")
            self.status_label.setText(f"✗ {vm.last_error or 'No video available.'}")

    def _save_and_close(self):
        vm = self.video_manager
        vm.set_catalog_url(self.catalog_url_edit.text().strip())
        vm.set_quality(self.quality_combo.currentData())
        vm.set_interval(self.interval_spin.value() * 60)
        vm.set_categories(self._selected_categories())
        vm.set_muted(self.mute_checkbox.isChecked())

        want_enabled = self.enable_checkbox.isChecked()
        if want_enabled != vm.enabled:
            success = vm.toggle_enabled(want_enabled)
            if not success and want_enabled:
                QMessageBox.warning(
                    self, "Video Wallpaper not available",
                    f"Failed to activate video wallpaper:\n{vm.last_error}"
                )
        elif want_enabled and vm.available:
            # già attivo: riavvia rotazione con i nuovi parametri
            vm.start_rotation()

        # Persisti su disco. Senza questo, tutte le modifiche fatte nel dialog
        # (qualità, intervallo, categorie, enable/disable, ecc.) restano solo
        # in memoria in vm e vengono perse al riavvio del launcher — esattamente
        # come fanno tutti gli altri salvataggi in settings_menu.py, che
        # aggiornano launcher.config_data['video_wallpaper'] e poi chiamano
        # launcher.save_config().
        launcher = getattr(vm, 'parent', None)
        if launcher is not None and hasattr(launcher, 'config_data'):
            launcher.config_data['video_wallpaper'] = vm.get_config()
        if launcher is not None and hasattr(launcher, 'save_config'):
            launcher.save_config()

        self.accept()


# ==================== INTEGRAZIONE NEL SETTINGS MENU ====================

def add_video_wallpaper_button_to_settings(settings_menu, launcher, layout, menu_items, icon_dir):
    
    def _open_dialog():
        current_launcher = settings_menu.launcher
        if current_launcher is None or not hasattr(current_launcher, 'video_wallpaper_manager'):
            QMessageBox.warning(
                settings_menu, "Non disponibile",
                "Il modulo video_wallpaper_manager non è integrato nel launcher."
            )
            return
        dlg = VideoWallpaperSettingsDialog(
            current_launcher,
            current_launcher.video_wallpaper_manager,
            getattr(settings_menu, 'scaling', None)
        )
        dlg.exec()

    btn = settings_menu._create_menu_button(
        "Video Wallpaper",
        "Streaming video wallpapers (Projectivy-style)",
        _open_dialog,
        str(Path(icon_dir) / "video.png")
    )
    layout.addWidget(btn)
    menu_items.append(btn)
    return btn
