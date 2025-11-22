# 🎮 TV Launcher

A sleek, console-style application launcher for Windows with gamepad support and automatic image fetching.

![TV Launcher](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/python-3.8+-green) ![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ Features

- **🎨 Beautiful TV-Mode Interface** - Full-screen carousel with smooth animations
- **🎮 Gamepad Support** - Navigate with Xbox/PlayStation controllers or keyboard
- **🖼️ Automatic Image Downloads** - Fetches 16:9 cover art from SteamGridDB
- **📱 Responsive Scaling** - Adapts to any screen resolution
- **🔍 Smart Program Scanner** - Automatically detects installed applications
- **⚡ Quick Launch** - Launch apps with Enter/A button
- **🎯 System Controls** - Built-in restart/shutdown options
- **🌄 Custom Backgrounds** - Personalize with your own images

## 📸 Screenshots

<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/e89a267a-052b-4df8-b546-3f12bff375a5" />

*Carousel view with cover art*

<img width="1920" height="1080" alt="Screenshot (253)" src="https://github.com/user-attachments/assets/1f9e19e3-02c9-476a-ab00-cafe8daadae9" />

*Automatic program detection*

## 🔧 Requirements

- **Windows** 10/11 or **Linux** (Ubuntu 20.04+, Fedora, Arch, etc.)
- **Python** 3.8 or higher
- **Dependencies**:
  - PyQt6
  - psutil
  - pygame (optional, for gamepad support)
  - requests (optional, for automatic image downloads)
  - pywin32 (Windows only, for shortcut scanning)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Darkvinx88/tv-launcher.git
cd tv-launcher
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
pip install -r requirements-linux.txt
```



### 3. Run the Launcher

**Windows:**
```bash
python tvlauncher.py
```

**Linux:**
```bash
python3 tvlauncher.py
# or make it executable
chmod +x tvlauncher.py
./tvlauncher.py
```

## 🎮 Usage

### Keyboard Controls
- **Arrow Keys** - Navigate carousel and menus
- **Enter** - Launch selected app
- **E** - Edit current app
- **Delete** - Remove current app
- **Escape** - Exit launcher or cancel menu
- **Up/Down** - Access system menu

### Gamepad Controls
- **D-Pad/Left Stick** - Navigate
- **A Button** - Launch app
- **B Button** - Back/Cancel
- **X Button** - Edit app
- **Y Button** - Delete app
- **Start Button** - Toggle system menu

### First Time Setup

1. **Add Your First App**
   - Click the `+` icon in the top-right
   - Browse for the executable
   - Optionally add a custom image
   - Click "Add"

2. **Scan Installed Programs**
   - Click the 🔍 icon
   - Wait for the scan to complete
   - Select programs to add
   - Click "Add Selected"

3. **Set Up SteamGridDB (Optional)**
   - Click the 🔑 icon
   - Get a free API key from [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)
   - Paste it in the dialog
   - The launcher will now auto-download 16:9 cover art

4. **Customize Background**
   - Click the 🖼️ icon
   - Select an image file
   - The background updates immediately

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
Images are stored in `assets/APP_NAME/banner.png` with automatic fallback to `.jpg`, `.jpeg`, or `.webp`.

## 📁 Project Structure

```
tv-launcher/
├── tvlauncher.py          # Main application
├── launcher_apps.json     # Configuration (auto-generated)
├── requirements.txt       # Python dependencies
├── assets/               # Image storage
│   ├── icons/           # UI icons
│   │   ├── key.png
│   │   ├── search.png
│   │   ├── plus.png
│   │   ├── image.png
│   │   └── logo48.png
│   └── [app_name]/      # Per-app folders
│       └── banner.png   # 16:9 cover art
└── README.md
```

## 🛠️ Troubleshooting

### Gamepad Not Detected
- Ensure pygame is installed: `pip install pygame`
- Connect gamepad before launching
- The launcher auto-detects gamepads every 5 seconds
- **Linux**: Ensure your user has permission to access `/dev/input/` devices
  ```bash
  sudo usermod -a -G input $USER
  # Log out and back in for changes to take effect
  ```

### Images Not Downloading
- Verify requests is installed: `pip install requests`
- Check your SteamGridDB API key is valid
- Ensure internet connection is active

### App Won't Launch
- Verify the executable path is correct
- Check file permissions
- **Windows**: Try running as administrator
- **Linux**: Ensure the binary has execute permissions (`chmod +x`)

### Scaling Issues
- The launcher auto-scales to your resolution
- Base resolution is 1920x1080
- All UI elements scale proportionally
- **Linux**: If using Wayland, some scaling issues may occur. Try X11 session.

### Linux-Specific Issues

**Missing Qt Platform Plugin:**
```bash
# Install Qt platform plugins
# Ubuntu/Debian:
sudo apt-get install qt6-qpa-plugins

# Fedora:
sudo dnf install qt6-qtbase-gui
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [SteamGridDB](https://www.steamgriddb.com/) - For providing game artwork API
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - For the UI framework
- [pygame](https://www.pygame.org/) - For gamepad support

## 🐛 Known Issues

- **Windows**: Some executables may need administrator privileges
- **All**: Background images should be high resolution for best results
- **Linux/Wayland**: Some scaling issues may occur, X11 recommended

**Star ⭐ this repo if you find it useful!**
