#!/usr/bin/env bash
# ==============================================================================
# Installer for Truck Mod Manager (ETS2 & ATS)
# Can be run as:
#   ./install.sh --user     (Installs to ~/.local, no root/sudo needed)
#   sudo ./install.sh       (Installs system-wide to /usr)
# ==============================================================================
set -e

COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_BLUE="\033[1;34m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_BLUE}====================================================${COLOR_RESET}"
echo -e "${COLOR_BLUE}       Truck Mod Manager (ETS2 & ATS) - Setup       ${COLOR_RESET}"
echo -e "${COLOR_BLUE}====================================================${COLOR_RESET}\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine install prefix
INSTALL_USER=false
if [ "$1" = "--user" ] || [ "$EUID" -ne 0 ]; then
    INSTALL_USER=true
    PREFIX="$HOME/.local"
    BIN_DIR="$PREFIX/bin"
    SHARE_DIR="$PREFIX/share/truck-mod-manager"
    APP_DIR="$PREFIX/share/applications"
    ICON_DIR_SVG="$PREFIX/share/icons/hicolor/scalable/apps"
    echo -e "Installationsmodus: ${COLOR_YELLOW}Benutzerverzeichnis (${PREFIX})${COLOR_RESET}"
else
    PREFIX="/usr"
    BIN_DIR="$PREFIX/bin"
    SHARE_DIR="$PREFIX/share/truck-mod-manager"
    APP_DIR="$PREFIX/share/applications"
    ICON_DIR_SVG="$PREFIX/share/icons/hicolor/scalable/apps"
    echo -e "Installationsmodus: ${COLOR_GREEN}Systemweit (${PREFIX})${COLOR_RESET}"
fi

# 1. Dependency checks
echo -e "\n${COLOR_BLUE}[1/4] Prüfe System-Abhängigkeiten...${COLOR_RESET}"

if ! command -v python3 &>/dev/null; then
    echo -e "${COLOR_RED}✗ Python 3 ist nicht installiert!${COLOR_RESET}"
    exit 1
else
    echo -e "${COLOR_GREEN}✓ Python 3 gefunden:${COLOR_RESET} $(python3 --version)"
fi

if ! python3 -c "import PyQt6" &>/dev/null; then
    echo -e "${COLOR_YELLOW}⚠ PyQt6 (python-pyqt6) ist noch nicht installiert.${COLOR_RESET}"
    echo -e "  Installation unter Arch/CachyOS: ${COLOR_GREEN}sudo pacman -S python-pyqt6${COLOR_RESET}"
    echo -e "  Installation unter Ubuntu/Debian: ${COLOR_GREEN}sudo apt install python3-pyqt6${COLOR_RESET}"
else
    echo -e "${COLOR_GREEN}✓ PyQt6 ist installiert.${COLOR_RESET}"
fi

# 2. Create directories
echo -e "\n${COLOR_BLUE}[2/4] Erstelle Verzeichnisstruktur...${COLOR_RESET}"
mkdir -p "$BIN_DIR"
mkdir -p "$SHARE_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR_SVG"

# 3. Copy application files
echo -e "\n${COLOR_BLUE}[3/4] Installiere Programmdateien...${COLOR_RESET}"
cp -r "$SCRIPT_DIR/truck_mod_manager" "$SHARE_DIR/"
cp "$SCRIPT_DIR/main.py" "$SHARE_DIR/"

# Create executable launcher script
cat << 'EOF' > "$BIN_DIR/truck-mod-manager"
#!/usr/bin/env bash
SHARE_PATH="TARGET_SHARE_DIR"
exec python3 "$SHARE_PATH/main.py" "$@"
EOF

# Substitute actual SHARE_DIR in launcher script
sed -i "s|TARGET_SHARE_DIR|$SHARE_DIR|g" "$BIN_DIR/truck-mod-manager"
chmod +x "$BIN_DIR/truck-mod-manager"

# Install Icon and Desktop file
if [ -f "$SCRIPT_DIR/truck_mod_manager/resources/icon.svg" ]; then
    cp "$SCRIPT_DIR/truck_mod_manager/resources/icon.svg" "$ICON_DIR_SVG/truck-mod-manager.svg"
fi

cp "$SCRIPT_DIR/truck-mod-manager.desktop" "$APP_DIR/truck-mod-manager.desktop"

# 4. Update system caches
echo -e "\n${COLOR_BLUE}[4/4] Aktualisiere Desktop- und Icon-Caches...${COLOR_RESET}"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi

echo -e "\n${COLOR_GREEN}✓ Installation erfolgreich abgeschlossen!${COLOR_RESET}"
echo -e "Start über Anwendungsmenü oder Terminal: ${COLOR_YELLOW}truck-mod-manager${COLOR_RESET}\n"
