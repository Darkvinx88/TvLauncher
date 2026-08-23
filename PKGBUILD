# Maintainer: Darkvinx88 <email here>
pkgname=tvlauncher
pkgver=1.4.1
pkgrel=1
epoch=
pkgdesc="A lightweight launcher for Windows and Linux that transforms your computer into a smart TV, delivering a full leanback experience on desktop."
arch=('x86_64' 'aarch64')
url="https://github.com/Darkvinx88/TvLauncher"
license=('MIT')
groups=()
depends=('python>=3.8' 'python-pyqt6' 'python-psutil' 'python-pygame' 'python-requests' 'python-mpv' 'python-pillow' 'mpv')
makedepends=()
checkdepends=()
optdepends=('python-pyqt6-multimedia: sound effects support')
provides=()
conflicts=()
replaces=()
backup=()
options=()
install=
changelog=
source=("https://github.com/Darkvinx88/TvLauncher/releases/download/${pkgver}/TV_Launcher_Linux_v${pkgver}.tar.gz")
sha256sums=('5bda4b2e3e425781d7a4a6c7ad192e722abea38aea55f1acd591e305f00d8b7e')

package() {
    cd "${srcdir}"

    # Install to /usr/lib/tvlauncher
    install -dm755 "${pkgdir}/usr/lib/tvlauncher"
    cp -r ./* "${pkgdir}/usr/lib/tvlauncher/"
    chmod -R +rx "${pkgdir}/usr/lib/tvlauncher/"

    # Create launcher script
    install -dm755 "${pkgdir}/usr/bin"
    cat > "${pkgdir}/usr/bin/tvlauncher" << EOF
#!/bin/bash
cd /usr/lib/tvlauncher/TV_Launcher_Linux_v${pkgver}
python3 TvLauncher_Linux.py
EOF
    chmod +x "${pkgdir}/usr/bin/tvlauncher"

    # Create desktop entry (if icon exists)
    install -dm755 "${pkgdir}/usr/share/applications"
    cat > "${pkgdir}/usr/share/applications/tvlauncher.desktop" << EOF
[Desktop Entry]
Name=TvLauncher
Comment=A lightweight launcher that transforms your computer into a smart TV
Exec=/usr/bin/tvlauncher
Icon=/usr/lib/tvlauncher/icon.png
Terminal=false
Type=Application
Categories=AudioVideo;Player;
EOF
}
