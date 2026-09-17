# Maintainer: Julian
pkgname=truck-mod-manager
pkgver=1.0.4
pkgrel=1
pkgdesc="Native Mod Manager for Euro Truck Simulator 2 & American Truck Simulator on Linux"
arch=('any')
url="https://github.com/julian/truck-mod-manager"
license=('GPL3')
depends=('python' 'python-pyqt6' 'python-requests')
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')

source=()
sha256sums=()

build() {
    cd "$srcdir/.."
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/.."
    python -m installer --destdir="$pkgdir" dist/*.whl

    # Desktop entry & Icon
    install -Dm644 truck-mod-manager.desktop "$pkgdir/usr/share/applications/truck-mod-manager.desktop"
    install -Dm644 truck_mod_manager/resources/icon.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/truck-mod-manager.svg"
}
