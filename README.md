# 🎮 TV Launcher

A sleek, console-style application launcher for Windows and Linux with gamepad support, automatic image fetching, and powerful organization features.

<p align="center">
  <a href='https://ko-fi.com/W7W41RFDX2' target='_blank'>
    <img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>





## ✨ Features

### 🎨 Beautiful Interface
- **Full-screen TV-Mode** - Console-style carousel with smooth animations
- **System Menu** - Press `S` or `Start` button to access the system Menu
- **Responsive Scaling** - Automatically adapts to any screen resolution (from 720p to 4K+)
- **Gamepad Support** - Navigate with Xbox/PlayStation controllers or keyboard/Bluetooth TV Remotes
- **Automatic Image Downloads** - Fetches 16:9 cover art from SteamGridDB
- **Smart Program Scanner** - Automatically detects installed applications with proper icon extraction
- **Quick Search Widget** - Instant app filtering with F/LB
- **Drag & Drop Reordering** - Reorganize apps with R/RB
- **System Controls** - Built-in Restart/Shutdown/Sleep options
- **Customizable Controls** - Remap any keyboard key or remote button to your liking

## 📸 Screenshots

<img width="1920" height="1080" alt="Screenshot (305)" src="https://github.com/user-attachments/assets/912fc172-427e-41c0-a043-c728a255b7ce" />


*Carousel view with cover art*

<img width="1920" height="1080" alt="Screenshot (301)" src="https://github.com/user-attachments/assets/f7bbd689-0bbd-4963-b040-36d5eb6665c1" />


*System Menu*

<img width="1920" height="1080" alt="Screenshot (303)" src="https://github.com/user-attachments/assets/cba6c06e-c600-4c5f-b55f-c30a672c7319" />


*Quick Search feature*


<img width="1920" height="1080" alt="Screenshot (302)" src="https://github.com/user-attachments/assets/5d65517b-b4c4-40dc-a1c6-c09247486ec5" />


*Key Remapper*



https://github.com/user-attachments/assets/9b5a56f2-09a0-4c7f-829d-2a1907c9bc80




*In motion*

### 🎮 Input Support
- **Gamepad Compatible** - Xbox, PlayStation, or any standard controller
- **Keyboard Navigation** - Full keyboard support
- **TV Remote Support** - Works with Bluetooth TV remotes
- **Fully Customizable** - Remap any key or button in Settings → Key Remapper
- **Auto-detection** - Automatically detects connected gamepads with visual notifications

### 🔍 Smart Organization
- **Quick Search** - Press `F` or `LB` to instantly search your apps
  - Live filtering as you type
  - Alphabetically sorted results
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


### ⚡ System Controls
- **Settings Menu** Comprehensive configuration panel with:
   - Visual toggles for all settings
   - Backup/Restore configuration
   - Soft Reset (keeps apps) vs Full Reset options
   - Direct GitHub update checker
- **Quick Actions** - Restart, Sleep, Shutdown, or Close launcher


### 🆕 New in Version 0.6 

- **Fixed**
   - Fixed a critical bug in the cover downloader
   - Strenghtened the cover download functionality
  
  
  
- **Added**
   - Linux Portable version
   - The ability to increase and decrease volume with xbox/ps4 controllers by pressing `LT + Dpad` up/down
   - Tile glow effect for the focused app and on/off switch in the settings menu
   - Network settings to easely manage ethernet/wifi/bluetooth
   - General UX/UI optimizations
   - Matching icons for every part of the settings menu
   - Reworked keymapper interface to match the new icons
   
   
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
sudo dnf install python3-pyqt6 python3-pip

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

### Default Keyboard Controls
| Key | Action |
|-----|--------|
| `←` `→` | Navigate carousel |
| `↑` `↓` | Navigate menus / system controls |
| `Enter` | Launch app |
| `F` | Open Quick Search |
| `R` | Toggle Reorder Mode |
| `S` | Open Settings Menu |
| `E` | Edit current app |
| `Delete` | Remove current app |
| `Tab` | Switch search mode (when searching) |
| `Esc` | Exit launcher / Cancel / Close search |

### Default Gamepad Controls
| Button | Action |
|--------|--------|
| D-Pad / Left Stick | Navigate |
| `A` | Launch app / Confirm |
| `B` | Back / Cancel |
| `X` | Edit app / Switch mode (in search) |
| `Y` | Delete app |
| `LB` | Open Quick Search |
| `RB` | Toggle Reorder Mode |
| `LT+Dpad up/down` | Volume up/down |




**🎮 Customizing Controls**
All controls can be remapped! Here's how:
 - Open Settings - Press S or Start button
 - Navigate to Advanced section
 - Select "🎮 Key Remapper"
 - Choose an action to remap
 - Press "Change" button
 - Press any key or button on your remote/keyboard
 - Confirm or cancel
 - Save and Close when done
 - Works with any keyboard key or TV remote button

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
  
6. **🆕 Customize Controls (Optional)**
   - Press `S` to open Settings
   - Navigate to "🎮 Key Remapper"
   - Remap any key to your preference
   - Changes apply instantly
     
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

**🆕 Key mappings** are stored separately in `key_mappings.json`:

```json
{
  "current_profile": "keyboard",
  "mappings": {
    "keyboard": {
      "navigate_left": "key_16777234",
      "navigate_right": "key_16777236",
      "launch": "key_16777220",
      "quick_search": "key_70",
      "reorder_mode": "key_82"
    }
  }
}
```

💡 **Tip:** Use the Backup feature in Settings to save your entire configuration (apps + mappings + settings).

### Image Organization
Images are stored in `assets/APP_NAME/banner.{png|jpg|jpeg|webp}` with automatic fallback.

## Windows Portable Mode
The Windows version is fully portable - simply press the .exe to start the launcher. You can move the entire folder anywhere.

## Linux Portable Mode
This version includes everything needed:
- Python 3.10 runtime
- All Python packages (PyQt6, pygame, requests, etc.)
- Qt6 with XCB/Wayland support (if in trouble sudo apt install libxcb)
- All system libraries bundled
  
**No installation required!** Just extract and run:
```bash
# Extract
TVLauncher Linux v0.6 Portable.zip

# Run
./launcher.sh

or edit the .desktop file
```

### System Requirements
- **Any Linux distro** (Ubuntu, Fedora, Arch, Debian, etc.)
- **X11 or Wayland** (auto-detected)
- **No external dependencies**

### Size
- Compressed: ~150MB
- Extracted: ~350MB

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

### Key Remapper Issues
- If remapped keys don't work, try restarting the launcher
- Check `key_mappings.json` file exists
- Use "Reset to Defaults" in Key Remapper if needed
- Key mappings are automatically included in configuration backups

### Settings Menu Issues
- Press `S` or `Start` to open settings
- If menu won't close, press `Esc` or `B`
- Settings changes save automatically
- Use Soft Reset to restore settings while keeping apps

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

**Missing Qt Multimedia (Sound Effects Not Working):**
If the launcher won't start or sound effects don't work, you may need Qt Multimedia packages:
```bash
# Debian / Ubuntu / Mint:
sudo apt install python3-pyqt6.qtmultimedia

# Fedora:
sudo dnf install python3-qt6-qtmultimedia

# Arch:
sudo pacman -S python-pyqt6-multimedia
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
- **Key Remapper:** Changes require launcher restart on some systems

## 📧 Contact

For issues, questions, or suggestions, please open an issue on GitHub.

---

⭐ **Star this repo if you find it useful!**

Made with ❤️ by Darkvinx88
