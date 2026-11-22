"""
UWP / Microsoft Store support
- scan_uwp_apps(): enumera le app dello Store (Get-StartApps + AppxManifest)
- UWPProcessTracker: segue il processo reale dell'app dopo il lancio via explorer
"""
import os
import re
import json
import shutil
import threading
import time
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import psutil

UWP_PREFIX = "shell:AppsFolder\\"
_NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW

ICON_CACHE_DIR = Path(os.environ.get('APPDATA', '.')) / 'TVLauncher' / 'uwp_icons'


def is_uwp_path(path):
    return isinstance(path, str) and path.lower().startswith(UWP_PREFIX.lower())


def aumid_from_path(path):
    return path[len(UWP_PREFIX):]


def launch_uwp(path):
    """Avvia l'app tramite explorer (senza shell=True)."""
    subprocess.Popen(['explorer.exe', UWP_PREFIX + aumid_from_path(path)])


def _powershell_json(script):
    full = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", full],
            capture_output=True, text=True, encoding='utf-8',
            creationflags=_NO_WINDOW, timeout=60
        ).stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"PowerShell error: {e}")
        return []


def _sanitize(name):
    safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
    return safe.strip().replace(' ', '_') or "app"


def _resolve_logo(install_dir, rel_logo):
    """Trova il file reale del logo (le cartelle di WindowsApps non sono
    listabili, quindi si provano i suffissi di scala noti)."""
    rel_logo = rel_logo.replace('/', '\\')
    base, ext = os.path.splitext(os.path.join(install_dir, rel_logo))
    candidates = [base + ext]
    for scale in (400, 200, 150, 125, 100):
        candidates.append(f"{base}.scale-{scale}{ext}")
    for size in (256, 96, 48):
        candidates.append(f"{base}.targetsize-{size}{ext}")
        candidates.append(f"{base}.targetsize-{size}_altform-unplated{ext}")
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _manifest_logo(install_dir, app_id):
    """Ritorna il path del logo migliore per l'Application con Id=app_id."""
    try:
        root = ET.parse(os.path.join(install_dir, "AppxManifest.xml")).getroot()
    except Exception:
        return None
    apps = [e for e in root.iter() if e.tag.endswith('}Application') or e.tag == 'Application']
    apps.sort(key=lambda e: e.get('Id') != app_id)  # quella giusta per prima
    for app in apps:
        for el in app.iter():
            if el.tag.endswith('VisualElements'):
                for attr in ('Square150x150Logo', 'Square44x44Logo'):
                    rel = el.get(attr)
                    if rel:
                        found = _resolve_logo(install_dir, rel)
                        if found:
                            return found
        break
    return None


def scan_uwp_apps():
    """Lista di dict {name, path, icon} delle app dello Store."""
    start_apps = _powershell_json("Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress")
    packages = _powershell_json(
        "Get-AppxPackage | Select-Object PackageFamilyName,InstallLocation | ConvertTo-Json -Compress")
    install_dirs = {p['PackageFamilyName']: p['InstallLocation']
                    for p in packages if p.get('PackageFamilyName') and p.get('InstallLocation')}

    ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for entry in start_apps:
        name = (entry.get('Name') or '').strip()
        aumid = (entry.get('AppID') or '').strip()
        # le app UWP hanno AUMID "PackageFamilyName!AppId"
        if not name or '!' not in aumid or '\\' in aumid:
            continue
        pfn, app_id = aumid.split('!', 1)
        icon = ''
        install_dir = install_dirs.get(pfn)
        if install_dir:
            logo = _manifest_logo(install_dir, app_id)
            if logo:
                # copia in AppData: il path del pacchetto cambia ad ogni aggiornamento
                dest = ICON_CACHE_DIR / f"{_sanitize(name)}{os.path.splitext(logo)[1]}"
                try:
                    shutil.copyfile(logo, dest)
                    icon = str(dest)
                except Exception as e:
                    print(f"Icon copy failed for {name}: {e}")
        results.append({'name': name, 'path': UWP_PREFIX + aumid, 'icon': icon})
    return results


class UWPProcessTracker:
    """explorer.exe termina subito: l'app va riconosciuta dai suoi processi,
    cioe' quelli il cui exe sta nella cartella di installazione del pacchetto."""

    GRACE_SECONDS = 20  # tempo massimo di attesa per la comparsa del processo

    def __init__(self, path):
        pfn = aumid_from_path(path).split('!')[0]
        self._name = pfn.split('_')[0].lower()
        self._pfn = pfn
        self._install_dir = None
        self._seen = False
        self._t0 = time.monotonic()
        threading.Thread(target=self._resolve_install_dir, daemon=True).start()

    def _resolve_install_dir(self):
        res = _powershell_json(
            f"Get-AppxPackage -PackageFamilyName '{self._pfn}' | "
            "Select-Object InstallLocation | ConvertTo-Json -Compress")
        if res and res[0].get('InstallLocation'):
            self._install_dir = res[0]['InstallLocation'].lower().rstrip('\\') + '\\'

    def _is_running(self):
        markers = [f"\\windowsapps\\{self._name}_"]
        if self._install_dir:
            markers.append(self._install_dir)
        for p in psutil.process_iter(['exe']):
            exe = (p.info.get('exe') or '').lower()
            if exe and any(m in exe for m in markers):
                return True
        return False

    def is_finished(self):
        """True quando l'app e' stata vista in esecuzione e poi chiusa,
        oppure non e' mai comparsa entro GRACE_SECONDS."""
        if self._is_running():
            self._seen = True
            return False
        if self._seen:
            return True
        return time.monotonic() - self._t0 > self.GRACE_SECONDS
