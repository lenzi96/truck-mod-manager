#!/usr/bin/env bash
# ==============================================================================
# Uninstaller for Truck Mod Manager (ETS2 & ATS)
# ==============================================================================
set -e

COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_BLUE="\033[1;34m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_BLUE}Deinstalliere Truck Mod Manager...${COLOR_RESET}"

if [ -f "$HOME/.local/bin/truck-mod-manager" ]; then
    PREFIX="$HOME/.local"
else
    PREFIX="/usr"
fi

rm -f "$PREFIX/bin/truck-mod-manager"
rm -rf "$PREFIX/share/truck-mod-manager"
rm -f "$PREFIX/share/applications/truck-mod-manager.desktop"
rm -f "$PREFIX/share/icons/hicolor/scalable/apps/truck-mod-manager.svg"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
fi

echo -e "${COLOR_GREEN}✓ Truck Mod Manager wurde erfolgreich deinstalliert.${COLOR_RESET}"
echo -e "Hinweis: Deine Mod-Archive unter ~/.local/share/truck-mod-manager wurden beibehalten."
