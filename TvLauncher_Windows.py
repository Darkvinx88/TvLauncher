import sys
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from services.tv_launcher import TVLauncher

def main():
    app = QApplication(sys.argv)
    # Prova a impostare un'icona (assicurati che il percorso sia corretto)
    icon_path = "assets/icons/logo48.png"
    if Path(icon_path).exists():
        app.setWindowIcon(QIcon(icon_path))
    else:
        print(f"Warning: App icon not found in {icon_path}")
        
    launcher = TVLauncher()
    launcher.show()
    launcher.setFocus()
    launcher.activateWindow()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
