# 🎮 TV Launcher

A sleek, console-style application launcher for Windows and Linux with gamepad support, automatic image fetching, and powerful organization features.

![TV Launcher](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 🎨 Beautiful Interface
- **Full-screen TV-Mode** - Console-style carousel with smooth animations
- **Responsive Scaling** - Automatically adapts to any screen resolution (from 720p to 4K+)
- **Gamepad Support** - Navigate with Xbox/PlayStation controllers or keyboard/Bluetooth TV Remotes
- **Automatic Image Downloads** - Fetches 16:9 cover art from SteamGridDB
- **Smart Program Scanner** - Automatically detects installed applications with proper icon extraction
- **Quick Search Widget** - Instant app filtering with F/LB
- **Drag & Drop Reordering** - Reorganize apps with R/RB
- **System Controls** - Built-in Restart/Shutdown/Sleep options

## 📸 Screenshots

<img width="1920" height="1080" alt="Screenshot (275)" src="https://github.com/user-attachments/assets/27e8cb96-49e2-4f69-8543-e99e303cf4ab" />

*Carousel view with cover art*

<img width="1920" height="1080" alt="Screenshot (276)" src="https://github.com/user-attachments/assets/eee826a9-94c1-493d-bdfb-77539611abc7" />

*Quick Search feature*

<img width="1920" height="1080" alt="Screenshot (278)" src="https://github.com/user-attachments/assets/7bbe9023-4762-4f12-b59a-3f4981dad55a" />

*Reorder mode with visual indicators*

<img width="1920" height="1080" alt="Screenshot (277)" src="https://github.com/user-attachments/assets/8a5f00e4-2983-433a-9d53-436bbb440d4c" />

*Automatic program detection*

https://github.com/user-attachments/assets/a827225f-9d14-4dcd-a48d-282d3d7d295a

*In motion*

### 🎮 Input Support
- **Gamepad Compatible** - Xbox, PlayStation, or any standard controller
- **Keyboard Navigation** - Full keyboard support
- **TV Remote Support** - Works with Bluetooth TV remotes
- **Auto-detection** - Automatically detects connected gamepads with visual notifications

### 🔍 Smart Organization
- **Quick Search** - Press `F` or `LB` to instantly search your apps
  - Live filtering as you type
  - Alphabetically sorted results
  - Two modes: Typing & Navigation
  - Keyboard and gamepad support
- **Drag & Drop Reordering** - Press `R` or `RB` to rearrange apps
  - Press `Enter`/`A` to activate reorder mode
  - Visual position indicators
  - Supports both linear and circular navigation
- **Smart Program Scanner** - Automatically detects installed applications
  - Cached results for instant loading
  - Proper icon extraction from executables
  - Alphabetically sorted display
- **Edit & Delete** - Manage your app library easily

### 🖼️ Automatic Image Management
- **SteamGridDB Integration** - Auto-downloads 16:9 cover art
- **Manual Download Button** - Download covers for existing apps at any time
- **Smart Auto-download Logic** - Automatically fetches images when adding apps
- **Local Image Support** - Use your own custom images
- **Smart Fallback** - Uses exe icons if images unavailable
- **Optimized Loading** - Cached pixmaps for smooth performance

### ⚡ System Controls
- **Quick Actions** - Restart, Sleep, Shutdown, or Close launcher
- **Process Monitoring** - Auto-detects when launched apps close
- **Input Management** - Automatically disables controls when app is running

## 🆕 Recent Updates

### Latest Version
- ✅ **Controller Connection Banners** - Visual notifications when gamepads connect/disconnect (Windows)
- ✅ **Manual Cover Download** - New button to download covers for existing apps
- ✅ **Improved Auto-download Logic** - Smarter image fetching when adding programs
- ✅ **Program Scanner Enhancements** - Cached results and proper icon extraction
- ✅ **Performance Improvements** - Initial refactoring for faster loading
- ✅ **Portable Mode** - Fully portable Windows version (no python install needed)

## 🔧 Requirements

- **Operating System:** Windows 10/11 or Linux (Ubuntu 20.04+, Fedora, Arch, etc.)
- **Python:** 3.8 or higher

### Dependencies
- `PyQt6` - UI framework
- `psutil` - Process management
- `pygame` (optional) - Gamepad support
- `requests` (optional) - Automatic image downloads
- `pywin32` (Windows only) - Shortcut scanning and icon extraction

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Darkvinx88/TvLauncher.git
cd TvLauncher
```

### 2. Install Dependencies

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux:**
```bash
# Install system dependencies first
# Ubuntu/Debian:
sudo apt-get update
sudo apt-get install python3-pyqt6 python3-pip

# Fedora:
sudo dnf install python3-qt6 python3-pip

# Arch:
sudo pacman -S python-pyqt6 python-pip

# Then install Python packages
pip install -r requirements.txt
```

### 3. Run the Launcher

**Windows:**
```bash
python TvLauncher_Windows.py
# or use the included .bat file for easier startup
```

**Linux:**
```bash
python3 TvLauncher_Linux.py
# or make it executable
chmod +x TvLauncher_Linux.py
./TvLauncher_Linux.py
```

## 🎮 Controls

### Keyboard Controls
| Key | Action |
|-----|--------|
| `←` `→` | Navigate carousel |
| `↑` `↓` | Navigate menus / system controls |
| `Enter` | Launch app |
| **`F`** | **Open Quick Search** |
| **`R`** | **Toggle Reorder Mode** |
| `E` | Edit current app |
| `Delete` | Remove current app |
| `Tab` | Switch search mode (when searching) |
| `Esc` | Exit launcher / Cancel / Close search |

### Gamepad Controls
| Button | Action |
|--------|--------|
| D-Pad / Left Stick | Navigate |
| `A` | Launch app / Confirm |
| `B` | Back / Cancel |
| `X` | Edit app / Switch mode (in search) |
| `Y` | Delete app |
| **`LB`** | **Open Quick Search** |
| **`RB`** | **Toggle Reorder Mode** |

## 🚀 Quick Start Guide

### First Time Setup

1. **Add Your First App**
   - Click the `+` icon in the top-right
   - Browse for the executable
   - Insert the API Key before adding any program for auto-download to work
   - Optionally add a custom image
   - Click "Add"

2. **Set Up SteamGridDB (Recommended)**
   - Click the `🔑` icon
   - Get a free API key from [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)
   - Paste it in the dialog
   - The launcher will now auto-download 16:9 cover art

3. **Scan Installed Programs**
   - Click the `🔍` icon
   - Wait for the scan to complete (may take a minute on first run)
   - Results are cached for instant loading next time
   - Select programs to add
   - Click "Add Selected"
   - Images download automatically in background

4. **Download Covers for Existing Apps**
   - Click the `⬇️` download icon in the header
   - Select which apps need covers
   - Covers download automatically from SteamGridDB

5. **Customize Background**
   - Click the `🖼️` icon
   - Select an image file (16:9 recommended)
   - Background updates immediately

### Using Quick Search

1. Press `F` (keyboard) or `LB` (gamepad) anywhere
2. Start typing to filter apps (Typing Mode)
3. Use `↑`/`↓` or D-Pad to navigate results (auto-switches to Navigation Mode)
4. Press `Tab` or `X` to manually switch modes
5. Press `Enter` or `A` to launch selected app
6. Press `Esc` or `B` to close search

### Reordering Apps

**Quick Toggle Method:**
1. Press `R` (keyboard) or `RB` (gamepad)
2. Use `←`/`→` to move the app to desired position
3. Press `Enter`/`A` to confirm or `Esc`/`B` to cancel

**Features:**
- Gold border shows selected app
- Blue border shows target position
- Position numbers appear on each tile
- Works with both linear (≤5 apps) and circular (>5 apps) modes
- Instructions overlay appears when active

## 🚀 Autostart Setup

The Launcher can start at boot on both Windows and Linux

### Windows Autostart

**Method 1: Startup Folder (Recommended)**
1. Press `Win + R` to open Run dialog
2. Type `shell:startup` and press Enter
3. Right-click your launcher `.bat` or `.exe` file → Create shortcut
4. Drag the shortcut into the Startup folder
5. ✅ Launcher will start automatically after login

💡 **Tip:** Right-click shortcut → Properties → Set Run: `Minimized` to hide console window.

**Method 2: Windows Registry**
1. Create a file named `TVLauncher_Autostart.reg`
2. Paste the following content:
```reg
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run]
"TVLauncher"="\"C:\\path\\to\\launch.bat\""
```
3. Replace `C:\\path\\to\\launch.bat` with your actual path
4. Double-click the `.reg` file to add the registry entry
5. ✅ Launcher will start automatically on every boot

### Linux Autostart

Works with any desktop environment (XFCE, GNOME, KDE, Cinnamon, MATE, etc.)

1. **Create autostart directory:**
```bash
mkdir -p ~/.config/autostart
```

2. **Create autostart file:**
```bash
nano ~/.config/autostart/TVLauncher.desktop
```

3. **Add this content:**
```ini
[Desktop Entry]
Type=Application
Name=TVLauncher
Comment=Automatically start the TV Launcher on login
Exec=/usr/bin/python3 /path/to/TvLauncher_Linux.py
Path=/path/to/
Terminal=false
X-GNOME-Autostart-enabled=true
```
*Replace `/path/to/` with actual directory*

4. **Make executable:**
```bash
chmod +x ~/.config/autostart/TVLauncher.desktop
```

**Using Virtual Environment?** Change the `Exec` line to:
```ini
Exec=/path/to/venv/bin/python /path/to/TvLauncher_Linux.py
```

✅ Launcher will now start automatically on login.

## ⚙️ Configuration

Configuration is stored in `launcher_apps.json`:

```json
{
  "apps": [
    {
      "name": "Steam",
      "path": "C:\\Program Files\\Steam\\steam.exe",
      "icon": "assets/Steam/banner.png"
    }
  ],
  "background": "C:\\path\\to\\background.jpg",
  "steamgriddb_api_key": "your-api-key-here"
}
```

### Image Organization
Images are stored in `assets/APP_NAME/banner.{png|jpg|jpeg|webp}` with automatic fallback.

### Portable Mode
The Windows version is fully portable - all paths are relative to the launcher directory. Simply move the entire folder to run from anywhere (USB drive, network share, etc.).

## 🛠️ Troubleshooting

### Gamepad Not Detected
- Ensure `pygame` is installed: `pip install pygame`
- Connect gamepad before launching
- Launcher auto-detects gamepads every 5 seconds
- Controller connection notifications appear when detected (Windows)
- **Linux:** Ensure user has permission to access `/dev/input/`:
  ```bash
  sudo usermod -a -G input $USER
  # Log out and back in
  ```

### Images Not Downloading
- Verify `requests` is installed: `pip install requests`
- Check SteamGridDB API key is valid
- Ensure internet connection is active
- Try the manual download button (⬇️ icon) for existing apps
- Images download in background thread (check console for errors)

### App Won't Launch
- Verify executable path is correct
- Check file permissions
- **Windows:** Try running as administrator
- **Linux:** Ensure binary has execute permissions (`chmod +x`)

### Search Not Working
- Check that `modules/search_widget.py` exists
- Try pressing `F` or `LB` to open search
- If search is stuck, press `Esc` to close and retry

### Reorder Mode Not Activating
- Try pressing `R` or `RB` to toggle
- Cannot activate during menu, dialogs, or when no apps exist

### Program Scanner Issues
- First scan may take 1-2 minutes
- Results are cached in `scanner_cache_*.json`
- Click refresh button (↻) to force rescan
- **Windows:** Ensure `pywin32` is installed for icon extraction

### Scaling Issues
- Launcher auto-scales to your resolution
- Base resolution: 1920x1080
- All UI elements scale proportionally
- **Linux/Wayland:** Some scaling issues may occur, try X11 session

### Linux-Specific Issues

**Missing Qt Platform Plugin:**
```bash
# Ubuntu/Debian:
sudo apt-get install qt6-qpa-plugins

# Fedora:
sudo dnf install qt6-qtbase-gui
```

**Permission Denied:**
```bash
chmod +x TvLauncher_Linux.py
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [SteamGridDB](https://www.steamgriddb.com/) - For providing game artwork API
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - For the UI framework
- [pygame](https://www.pygame.org/) - For gamepad support
- Community contributors and testers

## 🐛 Known Issues

- **Windows:** Some executables may need administrator privileges
- **All:** Background images should be high resolution (1920x1080+) for best results
- **Linux/Wayland:** Some scaling issues may occur, X11 recommended
- **Reorder Mode:** Cannot be activated while dialogs or menus are open (by design)

## 📧 Contact

For issues, questions, or suggestions, please open an issue on GitHub.

---

⭐ **Star this repo if you find it useful!**

Made with ❤️ by Darkvinx88
