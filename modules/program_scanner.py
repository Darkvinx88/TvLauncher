"""
Program Scanner Module
Handles scanning installed programs and displaying them in a dialog
Uses Qt Icon Theme Engine for optimal performance on Linux
"""
import sys
import os
import json
import platform
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QFileInfo
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider

# Detect OS
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    import winreg

def _get_icon_path(icon_name):
    """Trova il path dell'icona sia in sviluppo che in AppImage"""
    # Prova prima il path relativo normale (sviluppo)
    normal_path = Path("assets/icons") / icon_name
    if normal_path.exists():
        return str(normal_path)
    
    # Se siamo in AppImage, cerca nel sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        appimage_path = Path(sys._MEIPASS) / "assets" / "icons" / icon_name
        if appimage_path.exists():
            return str(appimage_path)
    
    return None

class ProgramScanner(QThread):
    """Background thread to scan installed programs WITH icons"""
    program_found = pyqtSignal(dict)
    scan_complete = pyqtSignal()
    progress_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
    
    def _extract_icon_from_exe(self, exe_path):
        """Extract icon from exe file using QFileIconProvider (Windows only)"""
        try:
            provider = QFileIconProvider()
            file_info = QFileInfo(exe_path)
            icon = provider.icon(file_info)
            
            if not icon.isNull():
                pixmap = icon.pixmap(32, 32)
                return pixmap
        except Exception as e:
            print(f"Error extracting icon from {exe_path}: {e}")
        
        return None
    
    def _find_best_exe(self, directory, app_name):
        """Find best exe in directory using smart heuristics (Windows only)"""
        if not os.path.isdir(directory):
            return None
        
        try:
            exe_files = []
            for f in os.listdir(directory):
                if f.lower().endswith('.exe'):
                    exe_files.append(f)
            
            if not exe_files:
                return None
            
            bad_keywords = [
                'unins', 'uninst', 'uninstall', 'setup', 'install', 'update', 
                'updater', 'launcher', 'crash', 'report', 'helper', 'service',
                'background', 'agent', 'stub', 'bootstrap', 'redist'
            ]
            
            good_exes = []
            for exe in exe_files:
                exe_lower = exe.lower()
                if not any(bad in exe_lower for bad in bad_keywords):
                    good_exes.append(exe)
            
            if not good_exes:
                for exe in exe_files:
                    if 'unins' not in exe.lower():
                        return os.path.join(directory, exe)
                return None
            
            app_name_clean = app_name.lower().replace(' ', '').replace('-', '').replace('_', '')
            
            for exe in good_exes:
                exe_clean = exe.lower().replace('.exe', '').replace(' ', '').replace('-', '').replace('_', '')
                if exe_clean == app_name_clean or app_name_clean in exe_clean:
                    return os.path.join(directory, exe)
            
            app_words = app_name.lower().split()
            for exe in good_exes:
                exe_lower = exe.lower()
                if any(word in exe_lower and len(word) > 3 for word in app_words):
                    return os.path.join(directory, exe)
            
            good_exes.sort(key=len)
            return os.path.join(directory, good_exes[0])
            
        except Exception as e:
            print(f"Error finding best exe in {directory}: {e}")
            return None

    def run(self):
        if IS_WINDOWS:
            self._scan_windows()
        else:
            self._scan_linux()
        
        self.scan_complete.emit()
    
    def _scan_windows(self):
        """Scan Windows programs from registry WITH icons"""
        seen_names = set()

        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for hkey, path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, path)
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            name = winreg.QueryValueEx(subkey, "DisplayName")[0].strip()
                        except:
                            winreg.CloseKey(subkey)
                            continue

                        exe_path = None
                        icon_path = None

                        try:
                            val = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            icon_path = val.strip('"').split(',')[0]
                        except:
                            pass

                        try:
                            val = winreg.QueryValueEx(subkey, "InstallLocation")[0].strip()
                            if val:
                                exe_path = self._find_best_exe(val, name)
                        except:
                            pass

                        if not exe_path:
                            try:
                                val = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                if "unins" in val.lower():
                                    parts = val.split('"')
                                    for p in parts:
                                        if p.lower().endswith('.exe'):
                                            dir_path = os.path.dirname(p)
                                            exe_path = self._find_best_exe(dir_path, name)
                                            if exe_path:
                                                break
                            except:
                                pass

                        if name and exe_path and os.path.exists(exe_path):
                            if name.lower() not in seen_names:
                                seen_names.add(name.lower())
                                
                                self.progress_update.emit(f"Found: {name}")
                                final_icon = icon_path if icon_path and os.path.exists(icon_path) else exe_path
                                
                                icon_pixmap = None
                                if final_icon and os.path.exists(final_icon):
                                    if final_icon.lower().endswith('.exe'):
                                        icon_pixmap = self._extract_icon_from_exe(final_icon)
                                    else:
                                        from PyQt6.QtGui import QPixmap
                                        icon_pixmap = QPixmap(final_icon)
                                        if icon_pixmap.isNull():
                                            icon_pixmap = None
                                
                                program_data = {
                                    'name': name,
                                    'path': exe_path,
                                    'icon': final_icon,
                                    'icon_pixmap': icon_pixmap
                                }
                                self.program_found.emit(program_data)

                        winreg.CloseKey(subkey)
                    except:
                        continue
                winreg.CloseKey(key)
            except:
                continue

        # Start Menu shortcuts
        start_menu_paths = [
            os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
            os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
            os.path.join(os.environ.get("PUBLIC", "C:\\Users\\Public"), "Desktop"),
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)")
        ]
        for start_path in start_menu_paths:
            if os.path.exists(start_path):
                self.scan_shortcuts(start_path, seen_names)
    
    def _scan_linux(self):
        """Scan Linux programs from .desktop files - OPTIMIZED WITH ICON THEME"""
        seen_names = set()
        
        desktop_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/snapd/desktop/applications",
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications")
        ]
        
        for desktop_dir in desktop_dirs:
            if not os.path.exists(desktop_dir):
                continue
                
            try:
                for filename in os.listdir(desktop_dir):
                    if not filename.endswith('.desktop'):
                        continue
                    
                    desktop_file = os.path.join(desktop_dir, filename)
                    
                    try:
                        app_data = self._parse_desktop_file(desktop_file)
                        if app_data and app_data['name'].lower() not in seen_names:
                            seen_names.add(app_data['name'].lower())
                            self.progress_update.emit(f"Found: {app_data['name']}")
                            self.program_found.emit(app_data)
                    except Exception as e:
                        print(f"Error parsing {desktop_file}: {e}")
                        continue
            except Exception as e:
                print(f"Error scanning {desktop_dir}: {e}")
                continue
    
    def _parse_desktop_file(self, filepath):
        """Parse Linux .desktop file - STORES ICON NAME FOR THEME LOOKUP"""
        name = None
        exec_path = None
        icon_name = None  # Store icon name, not path
        no_display = False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    if line.startswith('Name=') and not name:
                        name = line.split('=', 1)[1]
                    elif line.startswith('Exec='):
                        exec_cmd = line.split('=', 1)[1]
                        exec_cmd = exec_cmd.replace('%U', '').replace('%F', '').replace('%u', '').replace('%f', '')
                        exec_path = exec_cmd.strip()
                    elif line.startswith('Icon='):
                        # Store the icon name/path as-is
                        icon_name = line.split('=', 1)[1].strip()
                    elif line.startswith('NoDisplay=true'):
                        no_display = True
                    elif line.startswith('Terminal=true'):
                        no_display = True
            
            if no_display or not name or not exec_path:
                return None
            
            # Resolve command
            if ' ' in exec_path:
                exec_path_cmd = exec_path.split(' ')[0]
            else:
                exec_path_cmd = exec_path
            
            # Find command in PATH if not absolute
            if not os.path.isabs(exec_path_cmd):
                import shutil
                full_path = shutil.which(exec_path_cmd)
                if full_path:
                    exec_path = exec_path.replace(exec_path_cmd, full_path, 1)
                else:
                    return None
            
            # Check file existence only if no arguments
            if ' ' not in exec_path and not os.path.exists(exec_path):
                return None

            # Return icon_name for Qt Icon Theme lookup
            return {
                'name': name,
                'path': exec_path,
                'icon': icon_name,  # Can be name or path
                'icon_name': icon_name  # Store for theme lookup
            }
        
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return None
    
    def scan_shortcuts(self, directory, seen_names):
        """Scan Windows shortcuts (Windows only)"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.lnk'):
                        try:
                            shortcut_path = os.path.join(root, file)
                            shortcut = shell.CreateShortCut(shortcut_path)
                            target = shortcut.Targetpath
                            if target and target.lower().endswith('.exe') and os.path.exists(target):
                                name = Path(file).stem
                                if name.lower() not in seen_names:
                                    seen_names.add(name.lower())
                                    
                                    self.progress_update.emit(f"Found: {name}")
                                    
                                    icon_pixmap = self._extract_icon_from_exe(target)
                                    
                                    program_data = {
                                        'name': name,
                                        'path': target,
                                        'icon': target,
                                        'icon_pixmap': icon_pixmap
                                    }
                                    self.program_found.emit(program_data)
                        except:
                            continue
        except ImportError:
            pass


class ProgramScanDialog(QDialog):
    def __init__(self, image_manager=None, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        cache_suffix = "windows" if IS_WINDOWS else "linux"
        self.cache_file = Path(f"scanner_cache_{cache_suffix}.json")
        self.setWindowTitle("Scan Installed Programs")
        self.setModal(True)
        self.setFixedSize(700, 650)
        self.setStyleSheet("""
            QDialog { background-color: #1a1a1a; }
            QLabel { color: white; font-size: 16px; }
            QLineEdit { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 8px; border-radius: 8px; font-size: 14px; }
            QListWidget { 
                background-color: #2a2a2a; 
                color: white; 
                border: 2px solid #444; 
                border-radius: 8px; 
                font-size: 14px; 
                padding: 5px; 
            }
            QListWidget::item { 
                padding: 8px; 
                border-radius: 4px;
                background-color: transparent;
            }
            QListWidget::item:selected { 
                background-color: #3a3a3a; 
            }
            QListWidget::item:hover { 
                background-color: rgba(51, 51, 51, 0.5);
            }
            QPushButton { background-color: #2a2a2a; color: white; border: 2px solid #444; padding: 12px 30px; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #3a3a3a;} 
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        header_layout = QHBoxLayout()
        self.title_label = QLabel("Scanning Installed Programs in Progress...")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton()
        refresh_icon_path = _get_icon_path("refresh.png")
        if refresh_icon_path:
            self.refresh_btn.setIcon(QIcon(refresh_icon_path))
            self.refresh_btn.setIconSize(QSize(20, 20))
        else:
            self.refresh_btn.setText("↻")
        
        self.refresh_btn.setFixedSize(40, 40)
        self.refresh_btn.setToolTip("Update programs list")
        self.refresh_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.refresh_btn.clicked.connect(self.force_rescan)
        self.refresh_btn.setEnabled(False)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #888; font-size: 12px;")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)

        search_box = QHBoxLayout()
        search_box.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by Name...")
        self.search_input.textChanged.connect(self.filter_list)
        search_box.addWidget(self.search_input)
        layout.addLayout(search_box)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.list_widget.setIconSize(QSize(32, 32))
        layout.addWidget(self.list_widget)

        self.info_label = QLabel("Select which programs to add (Ctrl/Shift for multiple)")
        self.info_label.setStyleSheet("color: #aaa; font-size: 13px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add selected")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.list_widget.itemSelectionChanged.connect(self.update_add_button)

        self.scanner = None
        self.cache_loader = None
        if self.load_from_cache_fast():
            self.title_label.setText(f"Loaded {self.list_widget.count()} programs from cache")
            self.progress_label.setText("✅ Cache loaded (press ↻ to update)")
            self.refresh_btn.setEnabled(True)
        else:
            self.start_scan()

    def load_from_cache_fast(self):
        """Fast load from cache with ICON THEME ENGINE"""
        if not self.cache_file.exists():
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_programs = json.load(f)
            
            if not cached_programs:
                return False
            
            # Sort programs by name BEFORE loading
            cached_programs.sort(key=lambda x: x['name'].lower())
            
            # PHASE 1: Load first 10 immediately (with icons)
            for idx, data in enumerate(cached_programs[:10]):
                item = QListWidgetItem(f"{data['name']}")
                
                # Load icon using Qt Icon Theme (FAST!)
                icon = self._load_icon_from_theme(data)
                if not icon.isNull():
                    item.setIcon(icon)
                
                item.setData(Qt.ItemDataRole.UserRole, data)
                self.list_widget.addItem(item)
            
            # PHASE 2: Load the rest in background if more than 10
            if len(cached_programs) > 10:
                self.title_label.setText(f"Loaded 10/{len(cached_programs)} programs")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, lambda: self.load_remaining_icons(cached_programs[10:]))
            else:
                self.title_label.setText(f"Loaded {len(cached_programs)} programs from cache")
                self.progress_label.setText("✅ Cache loaded (press ↻ to update)")
                self.refresh_btn.setEnabled(True)
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error loading cache: {e}")
            return False
    
    def _load_icon_from_theme(self, app_data):
        """Load icon using Qt Icon Theme Engine - OPTIMIZED FOR LINUX"""
        icon_value = app_data.get('icon') or app_data.get('icon_name')
        
        if not icon_value:
            return QIcon()
        
        if IS_WINDOWS:
            # Windows: use file path
            if os.path.exists(icon_value):
                if icon_value.lower().endswith('.exe'):
                    provider = QFileIconProvider()
                    file_info = QFileInfo(icon_value)
                    return provider.icon(file_info)
                else:
                    return QIcon(icon_value)
            return QIcon()
        else:
            # Linux: use Qt Icon Theme Engine (MUCH FASTER!)
            # First try as theme icon name
            if not os.path.isabs(icon_value):
                # It's an icon name, use theme lookup
                icon = QIcon.fromTheme(icon_value)
                if not icon.isNull():
                    return icon
            
            # If absolute path, load directly
            if os.path.isabs(icon_value) and os.path.exists(icon_value):
                return QIcon(icon_value)
            
            # Fallback: try with common extensions
            for ext in ['', '.png', '.svg', '.xpm']:
                test_icon = QIcon.fromTheme(icon_value + ext)
                if not test_icon.isNull():
                    return test_icon
            
            return QIcon()
    
    def load_remaining_icons(self, remaining_programs):
        """Load remaining programs progressively"""
        from PyQt6.QtCore import QTimer
        
        self.remaining_queue = remaining_programs
        self.remaining_index = 0
        self.total_programs = self.list_widget.count() + len(remaining_programs)
        
        # Timer to load in batches
        self.remaining_timer = QTimer()
        self.remaining_timer.timeout.connect(self.load_remaining_batch)
        self.remaining_timer.start(10)  # Every 10ms
    
    def load_remaining_batch(self):
        """Load a batch of remaining programs"""
        batch_size = 20  # Increased from 15 - Icon Theme is faster!
        
        for _ in range(batch_size):
            if self.remaining_index >= len(self.remaining_queue):
                # Done!
                self.remaining_timer.stop()
                self.title_label.setText(f"Loaded {self.total_programs} programs from cache")
                self.progress_label.setText("✅ Cache loaded (press ↻ to update)")
                self.refresh_btn.setEnabled(True)
                return
            
            data = self.remaining_queue[self.remaining_index]
            
            item = QListWidgetItem(f"{data['name']}")
            
            # Load icon using Qt Icon Theme
            icon = self._load_icon_from_theme(data)
            if not icon.isNull():
                item.setIcon(icon)
            
            item.setData(Qt.ItemDataRole.UserRole, data)
            self.list_widget.addItem(item)
            
            self.remaining_index += 1
        
        # Update counter
        current_count = self.list_widget.count()
        self.title_label.setText(f"Loading... {current_count}/{self.total_programs}")
    
    def save_to_cache(self, programs):
        try:
            programs_to_save = []
            for prog in programs:
                prog_copy = prog.copy()
                prog_copy.pop('icon_pixmap', None)
                programs_to_save.append(prog_copy)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(programs_to_save, f, indent=2, ensure_ascii=False)
            print(f"💾 Cache saved with {len(programs_to_save)} programs")
        except Exception as e:
            print(f"⚠️ Error saving cache: {e}")
    
    def force_rescan(self):
        self.list_widget.clear()
        self.refresh_btn.setEnabled(False)
        self.title_label.setText("Scanning Installed Programs in Progress...")
        self.progress_label.setText("")
        self.start_scan()
    
    def start_scan(self):
        self.scanner = ProgramScanner()
        self.scanner.program_found.connect(self.add_item)
        self.scanner.scan_complete.connect(self.scan_done)
        self.scanner.progress_update.connect(self.update_progress)
        self.scanner.start()

    def add_item(self, data):
        item = QListWidgetItem(f"{data['name']}")
        
        # Load icon using Qt Icon Theme
        icon = self._load_icon_from_theme(data)
        if not icon.isNull():
            item.setIcon(icon)
        
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.list_widget.addItem(item)
        self.title_label.setText(f"Found {self.list_widget.count()} programs")

    def scan_done(self):
        programs = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            programs.append(item.data(Qt.ItemDataRole.UserRole))

        self.list_widget.sortItems(Qt.SortOrder.AscendingOrder)
        self.save_to_cache(programs)
        
        self.title_label.setText(f"Scan completed — Found {self.list_widget.count()} programs")
        self.progress_label.setText("💾 Cache saved")
        self.refresh_btn.setEnabled(True)
    
    def update_progress(self, message):
        self.progress_label.setText(message)

    def filter_list(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def update_add_button(self):
        selected = len(self.list_widget.selectedItems())
        self.add_btn.setEnabled(selected > 0)
        self.info_label.setText(f"{selected} selected" if selected > 0 else "Select the programs to add")

    def get_selected(self):
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.list_widget.selectedItems()]
