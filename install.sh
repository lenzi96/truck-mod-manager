#!/usr/bin/env bash
# ==============================================================================
# Installer for Truck Mod Manager (ETS2 & ATS)
# Can be run as:
#   ./install.sh --user     (Installs to ~/.local, no root/sudo needed - default)
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
    echo -e "  Installation unter Arch/CachyOS: ${COLOR_GREEN}sudo pacman -S python${COLOR_RESET}"
    echo -e "  Installation unter Ubuntu/Debian: ${COLOR_GREEN}sudo apt install python3${COLOR_RESET}"
    echo -e "  Installation unter Fedora:        ${COLOR_GREEN}sudo dnf install python3${COLOR_RESET}"
    exit 1
else
    echo -e "${COLOR_GREEN}✓ Python 3 gefunden:${COLOR_RESET} $(python3 --version)"
fi

if ! python3 -c "import PyQt6" &>/dev/null; then
    echo -e "${COLOR_YELLOW}⚠ PyQt6 (python-pyqt6) ist noch nicht installiert.${COLOR_RESET}"
    echo -e "  Installation unter Arch/CachyOS: ${COLOR_GREEN}sudo pacman -S python-pyqt6${COLOR_RESET}"
    echo -e "  Installation unter Ubuntu/Debian: ${COLOR_GREEN}sudo apt install python3-pyqt6${COLOR_RESET}"
    echo -e "  Installation unter Fedora:        ${COLOR_GREEN}sudo dnf install python3-pyqt6${COLOR_RESET}"
else
    echo -e "${COLOR_GREEN}✓ PyQt6 ist installiert.${COLOR_RESET}"
fi

if ! command -v 7z &>/dev/null && ! command -v 7za &>/dev/null; then
    echo -e "${COLOR_YELLOW}ℹ Hinweis: 7z (p7zip) empfohlen für automatisches Entpacken von mehrteiligen ProMods-Archiven.${COLOR_RESET}"
    echo -e "  Installation: ${COLOR_GREEN}sudo pacman -S p7zip${COLOR_RESET} oder ${COLOR_GREEN}sudo apt install p7zip-full${COLOR_RESET}"
else
    echo -e "${COLOR_GREEN}✓ 7z-Archiv-Entpacker verfügbar.${COLOR_RESET}"
fi

# 2. Create directories
echo -e "\n${COLOR_BLUE}[2/4] Erstelle Verzeichnisstruktur...${COLOR_RESET}"
mkdir -p "$BIN_DIR"
mkdir -p "$SHARE_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR_SVG"

# 3. Copy application files
echo -e "\n${COLOR_BLUE}[3/4] Installiere Programmdateien...${COLOR_RESET}"
rm -rf "$SHARE_DIR/truck_mod_manager"
cp -r "$SCRIPT_DIR/truck_mod_manager" "$SHARE_DIR/"
cp "$SCRIPT_DIR/main.py" "$SHARE_DIR/"

# Create robust executable launcher script
cat << 'EOF' > "$BIN_DIR/truck-mod-manager"
#!/usr/bin/env bash
# Truck Mod Manager launcher

# Safe Wayland/X11 platform plugin fallback
if [ -z "$QT_QPA_PLATFORM" ] && [ -n "$WAYLAND_DISPLAY" ]; then
    export QT_QPA_PLATFORM="wayland;xcb"
fi

SHARE_PATH="TARGET_SHARE_DIR"
if [ ! -d "$SHARE_PATH" ]; then
    if [ -d "$HOME/.local/share/truck-mod-manager" ]; then
        SHARE_PATH="$HOME/.local/share/truck-mod-manager"
    elif [ -d "/usr/share/truck-mod-manager" ]; then
        SHARE_PATH="/usr/share/truck-mod-manager"
    fi
fi

# Dependency check on launch
if ! command -v python3 &>/dev/null; then
    MSG="Python 3 ist nicht installiert!"
    if command -v zenity &>/dev/null; then zenity --error --text="$MSG" --title="Truck Mod Manager"; fi
    echo "$MSG" >&2
    exit 1
fi

if ! python3 -c "import PyQt6" &>/dev/null; then
    MSG="PyQt6 ist nicht installiert!\n\nBitte installiere PyQt6:\n  Arch/CachyOS: sudo pacman -S python-pyqt6\n  Ubuntu/Debian: sudo apt install python3-pyqt6\n  Fedora: sudo dnf install python3-pyqt6"
    if command -v zenity &>/dev/null; then zenity --error --text="$MSG" --title="Truck Mod Manager";
    elif command -v kdialog &>/dev/null; then kdialog --error "$MSG" --title "Truck Mod Manager"; fi
    echo -e "$MSG" >&2
    exit 1
fi

exec python3 "$SHARE_PATH/main.py" "$@"
EOF

# Substitute actual SHARE_DIR in launcher script
sed -i "s|TARGET_SHARE_DIR|$SHARE_DIR|g" "$BIN_DIR/truck-mod-manager"
chmod +x "$BIN_DIR/truck-mod-manager"

# Install Icon
if [ -f "$SCRIPT_DIR/truck_mod_manager/resources/icon.svg" ]; then
    cp "$SCRIPT_DIR/truck_mod_manager/resources/icon.svg" "$ICON_DIR_SVG/truck-mod-manager.svg"
fi

# Install Desktop file with absolute Exec path so it launches regardless of GUI $PATH
sed -e "s|^Exec=.*|Exec=$BIN_DIR/truck-mod-manager|g" \
    -e "s|^Icon=.*|Icon=truck-mod-manager|g" \
    "$SCRIPT_DIR/truck-mod-manager.desktop" > "$APP_DIR/truck-mod-manager.desktop"
chmod +x "$APP_DIR/truck-mod-manager.desktop"

# Install Desktop Shortcut on ~/Desktop or ~/Schreibtisch if directory exists
for dt_dir in "$HOME/Desktop" "$HOME/Schreibtisch"; do
    if [ -d "$dt_dir" ]; then
        cp "$APP_DIR/truck-mod-manager.desktop" "$dt_dir/truck-mod-manager.desktop"
        chmod +x "$dt_dir/truck-mod-manager.desktop"
        if command -v gio &>/dev/null; then
            gio set "$dt_dir/truck-mod-manager.desktop" metadata::trusted true 2>/dev/null || true
        fi
        echo -e "${COLOR_GREEN}✓ Desktop-Verknüpfung erstellt in:${COLOR_RESET} $dt_dir"
        break
    fi
done

# 4. Update system caches
echo -e "\n${COLOR_BLUE}[4/4] Aktualisiere Desktop- und Icon-Caches...${COLOR_RESET}"
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache &>/dev/null; then
    gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi

echo -e "\n${COLOR_GREEN}✓ Installation erfolgreich abgeschlossen!${COLOR_RESET}"
echo -e "Start über Anwendungsmenü oder Terminal: ${COLOR_YELLOW}$BIN_DIR/truck-mod-manager${COLOR_RESET}\n"
