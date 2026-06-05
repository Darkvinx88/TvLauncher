# Maintainer: Darkvinx88 <email here>
pkgname=tvlauncher
pkgver=v1.3
pkgrel=1
epoch=
pkgdesc="A lightweight launcher for Windows and Linux that transforms your computer into a smart TV, delivering a full leanback experience on desktop."
arch=('x86_64' 'aarch64')
url="https://github.com/Darkvinx88/TvLauncher"
license=('MIT')
groups=()
depends=('python>=3.8' 'python-pyqt6' 'python-psutil' 'python-pygame' 'python-requests')
makedepends=()
checkdepends=()
optdepends=()
provides=()
conflicts=()
replaces=()
backup=()
options=()
install=
changelog=
source=("https://github.com/Darkvinx88/TvLauncher/releases/download/1.3/TV_Launcher_Linux_${pkgver}.tar.gz")
sha256sums=('SKIP')  # Replace with actual sha256 sum

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
cd /usr/lib/tvlauncher/TV_Launcher_Linux_${pkgver}
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
