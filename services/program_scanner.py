import os
import winreg
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class ProgramScanner(QThread):
    """Background thread per scansionare i programmi installati SENZA download immagini"""
    program_found = pyqtSignal(dict)
    scan_complete = pyqtSignal()
    progress_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
    
    def _find_best_exe(self, directory, app_name):
        """Trova l'exe migliore in una directory usando euristiche intelligenti"""
        if not os.path.isdir(directory):
            return None
        
        try:
            exe_files = []
            for f in os.listdir(directory):
                if f.lower().endswith('.exe'):
                    exe_files.append(f)
            
            if not exe_files:
                return None
            
            # Filtri per escludere exe indesiderati
            bad_keywords = [
                'unins', 'uninst', 'uninstall', 'setup', 'install', 'update', 
                'updater', 'launcher', 'crash', 'report', 'helper', 'service',
                'background', 'agent', 'stub', 'bootstrap', 'redist'
            ]
            
            # Prima passata: rimuovi exe chiaramente sbagliati
            good_exes = []
            for exe in exe_files:
                exe_lower = exe.lower()
                if not any(bad in exe_lower for bad in bad_keywords):
                    good_exes.append(exe)
            
            if not good_exes:
                # Se abbiamo filtrato tutto, usa il primo che non è uninstaller
                for exe in exe_files:
                    if 'unins' not in exe.lower():
                        return os.path.join(directory, exe)
                return None
            
            # Seconda passata: trova il migliore
            app_name_clean = app_name.lower().replace(' ', '').replace('-', '').replace('_', '')
            
            # 1. Cerca exe con nome simile all'app
            for exe in good_exes:
                exe_clean = exe.lower().replace('.exe', '').replace(' ', '').replace('-', '').replace('_', '')
                if exe_clean == app_name_clean or app_name_clean in exe_clean:
                    return os.path.join(directory, exe)
            
            # 2. Cerca exe con parole chiave del nome app
            app_words = app_name.lower().split()
            for exe in good_exes:
                exe_lower = exe.lower()
                if any(word in exe_lower and len(word) > 3 for word in app_words):
                    return os.path.join(directory, exe)
            
            # 3. Preferisci exe più corti (di solito sono i principali)
            good_exes.sort(key=len)
            return os.path.join(directory, good_exes[0])
            
        except Exception as e:
            print(f"Error finding best exe in {directory}: {e}")
            return None

    def run(self):
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

                        # Icona
                        try:
                            val = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                            icon_path = val.strip('"').split(',')[0]
                        except:
                            pass

                        # Percorso eseguibile da InstallLocation
                        try:
                            val = winreg.QueryValueEx(subkey, "InstallLocation")[0].strip()
                            if val:
                                exe_path = self._find_best_exe(val, name)
                        except:
                            pass

                        # Fallback su UninstallString
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
                                
                                self.progress_update.emit(f"Trovato: {name}")
                                final_icon = icon_path if icon_path and os.path.exists(icon_path) else exe_path
                                
                                program_data = {
                                    'name': name,
                                    'path': exe_path,
                                    'icon': final_icon
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

        self.scan_complete.emit()

    def scan_shortcuts(self, directory, seen_names):
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
                                    
                                    self.progress_update.emit(f"Trovato: {name}")
                                    
                                    program_data = {
                                        'name': name,
                                        'path': target,
                                        'icon': target
                                    }
                                    self.program_found.emit(program_data)
                        except:
                            continue
        except ImportError:
            pass
