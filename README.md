# TV Launcher

A sleek, console-style application launcher for Windows and Linux with gamepad support, automatic image fetching, and powerful organization features.

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Platform">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">
</p>


<img width="1920" height="1080" alt="Screenshot (338)" src="https://github.com/user-attachments/assets/4bb5d45b-ef80-4481-beb4-28fc2ac89485" />



## Features

### Beautiful Interface
- **Full-screen TV-Mode** - Console-style carousel with smooth animations
- **System Menu** - Press `S` or `Start` button to access the system Menu
- **Responsive Scaling** - Automatically adapts to any screen resolution (from 720p to 4K+)
- **Gamepad Support** - Navigate with Xbox/PlayStation controllers or keyboard/Bluetooth TV Remotes
- **Automatic Image Downloads** - Fetches 16:9 cover art from SteamGridDB
- **Smart Program Scanner** - Automatically detects installed applications with proper icon extraction
- **Quick Search Widget** - Instant app filtering with `F/LB`
- **Drag & Drop Reordering** - Reorganize apps with `R/RB`
- **System Controls** - Built-in Restart/Shutdown/Sleep options
- **Customizable Controls** - Remap any keyboard key or remote button to your liking

## Screenshots

<img width="1920" height="1080" alt="Screenshot (339)" src="https://github.com/user-attachments/assets/b9c74376-fc18-4be8-8c99-639de0777a43" />


*System Menu*


<img width="1920" height="1080" alt="Screenshot (340)" src="https://github.com/user-attachments/assets/b77ce772-d9d2-48a4-bfe9-f3e8632b71dc" />



*Key Mapper and battery Widget*


<img width="1920" height="1080" alt="Screenshot (314)" src="https://github.com/user-attachments/assets/616d08f4-c1c3-45a7-8e8e-6981a002348c" />

*Category Manager*



https://github.com/user-attachments/assets/09108e93-de59-4919-a60f-eb129cec89bc






*In motion*

### Input Support
- **Gamepad Compatible** - Xbox, PlayStation, or any standard controller
- **Keyboard Navigation** - Full keyboard support
- **TV Remote Support** - Works with Bluetooth TV remotes
- **Fully Customizable** - Remap any key or button in Settings → Key Remapper
- **Auto-detection** - Automatically detects connected gamepads with visual notifications

### Smart Organization
- **Category System** 
  - Organize apps into categories (Games, Media, Programs, Other)
  - Press Up/D-Pad Up to open category selector
  - Navigate categories with Left/Right or D-Pad
  - Quick category assignment with C (keyboard) or X/Square (controller)


- **Category Manager** - Customize categories in Settings
   - Add, edit, or delete categories
   - Choose custom icons and colors
   - Select the default category shown on launch
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

### Automatic Image Management
- **SteamGridDB Integration** - Auto-downloads 16:9 cover art
- **Manual Download Button** - Download covers for existing apps at any time
- **Smart Auto-download Logic** - Automatically fetches images when adding apps
- **Local Image Support** - Use your own custom images


### System Controls
- **Settings Menu** Comprehensive configuration panel with:
   - Visual toggles for all settings
   - Backup/Restore configuration
   - Soft Reset (keeps apps) vs Full Reset options
   - Direct GitHub update checker
   - Category Manager for organizing apps
- **Quick Actions** - Restart, Sleep, Shutdown, or Close launcher


 ### New in Version 1.1
- **Fixed**
   - Flatpak binary path (/usr/bin/flatpak) was incorrectly treated as a valid icon,
     preventing cover download from SteamGridDB on some Linux distributions (e.g. Kubuntu).
   
  
   ## Requirements

- **Operating System:** Windows 10/11 or Linux (Ubuntu 20.04+, Fedora, Arch, etc.)
- **Python:** 3.8 or higher

### Dependencies
- `PyQt6` - UI framework
- `psutil` - Process management
- `pygame` - Gamepad support
- `requests`- Automatic image downloads
- `pycaw`   (Windows only) - Windows core audio control
- `pywin32` (Windows only) - Shortcut scanning and icon extraction

## Installation

### 1. Clone the Repository (branch 1 for Windows,branch 2 for Linux)
```bash
git clone https://github.com/Darkvinx88/TvLauncher.git
cd TvLauncher
```
 
### 2. Create Virtual Environment and Install Dependencies

**Windows:**
```bash
#Create Virtual environment:
python -m venv venv

#Activate Virtual environment:
venv\Scripts\activate

#Install dependencies:
pip install -r requirements.txt

#Run the launcher
python TvLauncher_Windows.py

#Alternatively you can just run the installer.bat and let it do everything for you
#(creates a virtual environment,activates it,installs dependencies)
#Once everything is installed simply run the launcher with the given TVLauncher.bat file
#it will automatically activate the virtual environment and run the launcher with 1 click


```

**Linux:**
```bash

# Create virtual environment:
python3 -m venv venv

# Activate virtual environment:
source venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# Run the launcher 
python3 TvLauncher_Linux.py

#Alternatively you can just run the Installer.sh and let it do everything for you
#(creates a virtual environment,activates it,installs dependencies)
#Once everything is installed simply run the launcher with the given Launcher.sh file
#it will automatically activate the virtual environment and run the launcher with 1 click

#sh files are already executable but if they are not just do
chmod +x installer.sh
./installer.sh

chmod +x launcher.sh
./launcher.sh

#you can also edit the given .desktop so you are able to run the launcher no matter where it is placed.

```

## Windows Portable Mode
The Windows version is fully portable - simply press the .exe to start the launcher. You can move the entire folder anywhere.

## Linux Portable Mode
This version includes everything needed:
- Python runtime
- Environment and launcher.sh have launching permissions already baked in
- All Python packages (PyQt6, pygame, requests, etc.)
- Qt6 with XCB/Wayland support (if in trouble sudo apt install libxcb)

Just extract and run:
```bash
# Extract
TVLauncher Linux v1.1 Portable.tar.gz

# Run
./launcher.sh

or edit the .desktop file
```

## Controls

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
| `C` | Quick Category Assignment |
| `Delete` | Remove current app |
| `Tab` | Switch search mode (when searching) |
| `Esc` | Exit launcher / Cancel / Close search |

### Default Gamepad Controls
| Button | Action |
|--------|--------|
| `D-Pad / Left Stick` | Navigate |
| `D-Pad Up` | Open category selector |
| `A/Cross` | Launch app / Confirm |
| `B/Circle` | Back / Cancel |
| `X/Square` | Quick Category editor |
| `Y/Triangle` | Delete app |
| `LB/L1` | Open Quick Search |
| `RB/R1` | Toggle Reorder Mode |
| `start` | Open Settings Menu |
| `LT\L2+Dpad ↑/↓` | Volume up/down |




**Customizing Controls**
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

## Quick Start Guide

### First Time Setup
1. Open settings Menu with `s`  or `start`
   
2. **Set Up SteamGridDB (Recommended)**
   - Click "API Key"
   - Get a free API key from [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)
   - Paste it in the dialog
   - The launcher will now auto-download 16:9 cover art
     
3. **Scan Installed Programs**
   - Click "Scan Programs" 
   - Wait for the scan to complete (may take a minute on first run)
   - Results are cached for instant loading next time
   - Select programs to add
   - Click "Add Selected"
   - Images download automatically in background
  
4. **Add App Manually**
   - Click "Add app"
   - Browse for the executable
   - Optionally add a custom image
   - Click "Add"

5. **Download Covers for Existing Apps**
   - Click "Download Covers" 
   - Covers download automatically from SteamGridDB

6. **Customize Background**
   - Click "Set Background"
   - Select an image file (16:9 recommended)
   - Background updates immediately
  
7. **Auto change Wallpapers (Optional)**
   - Place your image files in the wallpaper folder
   - Go to settings and activate the Auto change wallpapers
   - Now every 5 minutes your wallpapers will change in a random rotation
     
8. **Setup Weather Widget (Optional)**
   - Press `S` to open Settings
   - Navigate to Weather Settings
   - Type your city and optional nation code (IT,GB,US etc)
   - Click Save and Apply
   - Weather Widget will be on top righ corner (it may take 1 second to fetch weather data)
     
9. **Customize Controls (Optional)**
   - Press `S` to open Settings
   - Navigate to "🎮 Key Remapper"
   - Remap any key to your preference
   - Changes apply instantly
          
   
### Using Categories

1. Press `↑ (keyboard)` or `D-Pad Up` (gamepad) to open category selector
2. Use `←/→` or `D-Pad Left/Right` to switch between categories
3. Press `↓` or `D-Pad Down` to close and view filtered apps
4. Press `C` or `X/Square` on any app to quickly assign a category

### Managing Categories:

1. Open Settings (`S` or `Start`)
2. Select "Manage Categories"
3. Add, edit, or delete categories
4. Customize icons and colors
5. Select your preferred category
6. click on the green checkmark and save
7. at launch the selected category will be the first to be shown
 
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

## Autostart Setup

The Launcher can start at boot on both Windows and Linux

### Windows Autostart

**Method 1: Startup Folder (Recommended)**
1. Press `Win + R` to open Run dialog
2. Type `shell:startup` and press Enter
3. Right-click your launcher `.bat` or `.exe` file → Create shortcut
4. Drag the shortcut into the Startup folder
5. Launcher will start automatically after login

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
5. Launcher will start automatically on every boot

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
Exec=/path/to/venv/bin/python /path/to/TvLauncher_Linux.py
Path=/path/to/
Terminal=false
X-GNOME-Autostart-enabled=true
```
*Replace `/path/to/` with actual directory*

4. **Make executable:**
```bash
chmod +x ~/.config/autostart/TVLauncher.desktop
```

Launcher will now start automatically on login.

## ⚙️ Configuration

Configuration is stored in `launcher_apps.json`

Key mappings are stored separately in `key_mappings.json`

💡 **Tip:** Use the Backup feature in Settings to save your entire configuration (apps + mappings + settings).

### Image Organization
Images are stored in `assets/APP_NAME/banner.{png|jpg|jpeg|webp}` with automatic fallback.


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

### Key Remapper Issues
- If remapped keys don't work, try restarting the launcher
- Check `key_mappings.json` file exists
- Use "Reset to Defaults" in Key Remapper if needed
- Key mappings are automatically included in configuration backups

### Program Scanner Issues
- First scan may take 1-2 minutes
- Results are cached in `scanner_cache_*.json`
- Click refresh button (↻) to force rescan
- **Windows:** Ensure `pywin32` is installed for icon extraction

### Scaling Issues
- Launcher auto-scales to your resolution
- Base resolution: 1920x1080
- All UI elements scale proportionally

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

## Acknowledgments

- [SteamGridDB](https://www.steamgriddb.com/) - For providing game artwork API
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - For the UI framework
- [pygame](https://www.pygame.org/) - For gamepad support
- Community contributors and testers

## Known Issues

- **Windows:** Some executables may need administrator privileges
- **All:** Background images should be high resolution (1920x1080+) for best results


## 📧 Contact

For issues, questions, or suggestions, please open an issue on GitHub.

---

⭐ **Star this repo if you find it useful!**

Made with ❤️ by Darkvinx88 
<p align="center">
  <a href='https://ko-fi.com/W7W41RFDX2' target='_blank'>
    <img height='36' style='border:0px;height:36px;' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' />
  </a>
</p>

