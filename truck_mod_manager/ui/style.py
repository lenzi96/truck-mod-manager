"""
Modern dark styling and CSS definitions for Truck Mod Manager.
"""
from typing import Dict
from truck_mod_manager.core.models import ModCategory


DARK_THEME_QSS = """
/* Global Application Style - Modern Obsidian Midnight Theme */
QWidget {
    background-color: #0b0f19;
    color: #f1f5f9;
    font-family: 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Sans', sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Base text labels - transparent background so cards, headers and toolbars are seamless */
QLabel {
    background-color: transparent;
    color: #f1f5f9;
}

/* Header & Card Containers */
QFrame#headerFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #162035, stop:1 #101726);
    border: 1px solid #243350;
    border-radius: 9px;
    padding: 6px 14px;
}

QFrame#toolbarCard {
    background-color: #131b2e;
    border: 1px solid #243350;
    border-radius: 8px;
    padding: 8px 12px;
}

QFrame#cardFrame {
    background-color: #131b2e;
    border: 1px solid #243350;
    border-radius: 9px;
    padding: 0px;
}

QFrame#cardFrame:hover {
    border: 1px solid #3b82f6;
    background-color: #18233c;
}

/* Navigation Tabs */
QTabWidget::pane {
    border: 1px solid #243350;
    background-color: #0b0f19;
    border-radius: 8px;
    top: -1px;
}

QTabBar::tab {
    background-color: #131b2e;
    color: #94a3b8;
    padding: 9px 16px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid #243350;
    border-bottom: none;
    font-weight: 500;
    font-size: 13px;
}

QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563eb, stop:1 #1d4ed8);
    color: #ffffff;
    font-weight: bold;
    border-color: #3b82f6;
    border-bottom: 2px solid #60a5fa;
}

QTabBar::tab:hover:!selected {
    background-color: #1c2740;
    color: #f8fafc;
    border-color: #334155;
}

/* Push Buttons */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a253c, stop:1 #131c2e);
    color: #f1f5f9;
    border: 1px solid #28395a;
    border-radius: 7px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #233250, stop:1 #1a263d);
    border-color: #3b82f6;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #0c121e;
    border-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #111827;
    color: #475569;
    border-color: #1e293b;
}

/* Accent Buttons */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3b82f6, stop:1 #1d4ed8);
    color: #ffffff;
    border: 1px solid #60a5fa;
    font-weight: bold;
}

QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60a5fa, stop:1 #2563eb);
    border-color: #93c5fd;
}

QPushButton#successBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #10b981, stop:1 #059669);
    color: #ffffff;
    border: 1px solid #34d399;
    font-weight: bold;
}

QPushButton#successBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34d399, stop:1 #047857);
    border-color: #6ee7b7;
}

QPushButton#dangerBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #b91c1c);
    color: #ffffff;
    border: 1px solid #f87171;
    font-weight: bold;
}

QPushButton#dangerBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #991b1b);
    border-color: #fca5a5;
}

QPushButton#warningBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f59e0b, stop:1 #b45309);
    color: #ffffff;
    border: 1px solid #fbbf24;
    font-weight: bold;
}

QPushButton#warningBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fbbf24, stop:1 #92400e);
    border-color: #fde68a;
}

QPushButton#iconBtn {
    padding: 0px;
    text-align: center;
}

/* Inputs & Editors */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #0e1524;
    color: #f8fafc;
    border: 1px solid #243350;
    border-radius: 7px;
    padding: 7px 12px;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1.5px solid #3b82f6;
    background-color: #111a2d;
}

/* ComboBox */
QComboBox {
    background-color: #131b2e;
    color: #f8fafc;
    border: 1px solid #243350;
    border-radius: 7px;
    padding: 6px 14px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #3b82f6;
}

QComboBox:focus {
    border: 1.5px solid #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #131b2e;
    color: #f8fafc;
    border: 1px solid #243350;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    border-radius: 6px;
    padding: 4px;
}

/* Lists and Tables */
QListWidget {
    background-color: transparent;
    border: none;
    padding: 2px 0px;
    outline: none;
}

QTableWidget, QTreeWidget {
    background-color: #0b0f19;
    alternate-background-color: #101828;
    gridline-color: #1a253c;
    border: 1px solid #202d44;
    border-radius: 8px;
    padding: 2px;
    outline: none;
    color: #f1f5f9;
}

QListWidget::item {
    padding: 0px;
    border: none;
    background: transparent;
}

QListWidget::item:hover {
    background-color: transparent;
}

QListWidget::item:selected {
    background-color: transparent;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #162032;
}

QHeaderView::section {
    background-color: #131b2e;
    color: #94a3b8;
    padding: 9px;
    border: none;
    border-right: 1px solid #202d44;
    border-bottom: 2px solid #243350;
    font-weight: bold;
    font-size: 12px;
}

/* Sleek Slim Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #293854;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background-color: transparent;
    height: 8px;
}

QScrollBar::handle:horizontal {
    background-color: #293854;
    min-width: 28px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #3b82f6;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* Splitters */
QSplitter::handle {
    background-color: #202d44;
}

/* Checkboxes & Radios */
QCheckBox, QRadioButton {
    background-color: transparent;
    spacing: 8px;
    color: #f1f5f9;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #131b2e;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #60a5fa;
}

/* Tooltips */
QToolTip {
    background-color: #131b2e;
    color: #f8fafc;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* Status Bar */
QStatusBar {
    background-color: #111827;
    color: #94a3b8;
    border-top: 1px solid #202d44;
    padding: 4px 8px;
}
"""


# Category Badges (Background, Text Color, Border Color, Human label)
CATEGORY_STYLES: Dict[ModCategory, Dict[str, str]] = {
    ModCategory.MAP: {"bg": "#1e3a8a", "fg": "#bfdbfe", "border": "#3b82f6", "label": "Karte (Map)"},
    ModCategory.MODELS: {"bg": "#064e3b", "fg": "#a7f3d0", "border": "#10b981", "label": "Modelle"},
    ModCategory.PREFABS: {"bg": "#065f46", "fg": "#6ee7b7", "border": "#059669", "label": "Prefabs"},
    ModCategory.DEF: {"bg": "#831843", "fg": "#fbcfe8", "border": "#db2777", "label": "Definition (Def)"},
    ModCategory.TRUCK: {"bg": "#1e40af", "fg": "#dbeafe", "border": "#60a5fa", "label": "LKW (Truck)"},
    ModCategory.TRAILER: {"bg": "#155e75", "fg": "#cffafe", "border": "#06b6d4", "label": "Trailer"},
    ModCategory.TUNING: {"bg": "#7c2d12", "fg": "#ffedd5", "border": "#ea580c", "label": "Tuning"},
    ModCategory.INTERIOR: {"bg": "#701a75", "fg": "#fae8ff", "border": "#c026d3", "label": "Interieur"},
    ModCategory.SOUND: {"bg": "#78350f", "fg": "#fef08a", "border": "#d97706", "label": "Sound (FMOD)"},
    ModCategory.PHYSICS: {"bg": "#374151", "fg": "#f3f4f6", "border": "#6b7280", "label": "Physik"},
    ModCategory.AI_TRAFFIC: {"bg": "#365314", "fg": "#ecfccb", "border": "#65a30d", "label": "KI-Verkehr"},
    ModCategory.PAINT_JOB: {"bg": "#581c87", "fg": "#f3e8ff", "border": "#9333ea", "label": "Skin / Lackierung"},
    ModCategory.CARGO: {"bg": "#451a03", "fg": "#ffedd5", "border": "#b45309", "label": "Fracht (Cargo)"},
    ModCategory.GRAPHICS: {"bg": "#0c4a6e", "fg": "#e0f2fe", "border": "#0284c7", "label": "Grafik"},
    ModCategory.WEATHER: {"bg": "#134e4a", "fg": "#ccfbf1", "border": "#0d9488", "label": "Wetter / Klima"},
    ModCategory.UI: {"bg": "#312e81", "fg": "#e0e7ff", "border": "#4f46e5", "label": "UI / HUD"},
    ModCategory.OTHER: {"bg": "#1f2937", "fg": "#e5e7eb", "border": "#374151", "label": "Sonstige"},
}


def get_category_badge_style(category: ModCategory) -> str:
    """Returns CSS style string for a category badge."""
    info = CATEGORY_STYLES.get(category, CATEGORY_STYLES[ModCategory.OTHER])
    border_color = info.get("border", info["bg"])
    return (
        f"background-color: {info['bg']}; "
        f"color: {info['fg']}; "
        f"border: 1px solid {border_color}; "
        f"padding: 3px 9px; "
        f"border-radius: 6px; "
        f"font-size: 11px; "
        f"font-weight: bold;"
    )
