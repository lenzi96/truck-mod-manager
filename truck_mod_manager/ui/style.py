"""
Modern dark styling and CSS definitions for Truck Mod Manager.
"""
from typing import Dict
from truck_mod_manager.core.models import ModCategory


DARK_THEME_QSS = """
/* Global Application Style */
QWidget {
    background-color: #0f172a;
    color: #f1f5f9;
    font-family: 'Segoe UI', 'Ubuntu', 'Inter', 'Noto Sans', sans-serif;
    font-size: 13px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Header & Cards */
QFrame#headerFrame {
    background-color: #1e293b;
    border-bottom: 2px solid #334155;
    padding: 6px;
}

QFrame#cardFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0px;
}

QFrame#cardFrame:hover {
    border: 1px solid #475569;
    background-color: #243248;
}

/* Navigation Tabs */
QTabWidget::pane {
    border: 1px solid #334155;
    background-color: #0f172a;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 10px 18px;
    margin-right: 3px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid #334155;
    border-bottom: none;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
    border-color: #3b82f6;
}

QTabBar::tab:hover:!selected {
    background-color: #334155;
    color: #f8fafc;
}

/* Push Buttons */
QPushButton {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}

QPushButton:pressed {
    background-color: #0f172a;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border-color: #1e293b;
}

/* Accent Buttons */
QPushButton#primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    border: 1px solid #3b82f6;
    font-weight: bold;
}

QPushButton#primaryBtn:hover {
    background-color: #1d4ed8;
}

QPushButton#successBtn {
    background-color: #059669;
    color: #ffffff;
    border: 1px solid #10b981;
    font-weight: bold;
}

QPushButton#successBtn:hover {
    background-color: #047857;
}

QPushButton#dangerBtn {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
}

QPushButton#dangerBtn:hover {
    background-color: #b91c1c;
}

QPushButton#warningBtn {
    background-color: #d97706;
    color: #ffffff;
    border: 1px solid #f59e0b;
}

QPushButton#warningBtn:hover {
    background-color: #b45309;
}

/* Inputs */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}

/* ComboBox */
QComboBox {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #475569;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}

/* Lists and Tables */
QListWidget, QTableWidget, QTreeWidget {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
    outline: none;
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
    padding: 6px;
    border-bottom: 1px solid #1e293b;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-right: 1px solid #334155;
    border-bottom: 1px solid #334155;
    font-weight: bold;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #0f172a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #0f172a;
    height: 10px;
}

QScrollBar::handle:horizontal {
    background-color: #334155;
    min-width: 25px;
    border-radius: 5px;
}

/* Splitters */
QSplitter::handle {
    background-color: #1e293b;
}

/* Checkboxes */
QCheckBox {
    spacing: 8px;
    color: #f1f5f9;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #475569;
    border-radius: 4px;
    background-color: #1e293b;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 5px;
}

/* Status Bar */
QStatusBar {
    background-color: #1e293b;
    color: #94a3b8;
    border-top: 1px solid #334155;
}
"""


# Category Badges (Background, Text Color, Human label)
CATEGORY_STYLES: Dict[ModCategory, Dict[str, str]] = {
    ModCategory.MAP: {"bg": "#1e3a8a", "fg": "#93c5fd", "label": "Karte (Map)"},
    ModCategory.MODELS: {"bg": "#064e3b", "fg": "#a7f3d0", "label": "Modelle"},
    ModCategory.PREFABS: {"bg": "#065f46", "fg": "#6ee7b7", "label": "Prefabs"},
    ModCategory.DEF: {"bg": "#831843", "fg": "#fbcfe8", "label": "Definition (Def)"},
    ModCategory.TRUCK: {"bg": "#1e40af", "fg": "#bfdbfe", "label": "LKW (Truck)"},
    ModCategory.TRAILER: {"bg": "#155e75", "fg": "#a5f3fc", "label": "Trailer"},
    ModCategory.TUNING: {"bg": "#7c2d12", "fg": "#fed7aa", "label": "Tuning"},
    ModCategory.INTERIOR: {"bg": "#701a75", "fg": "#f5d0fe", "label": "Interieur"},
    ModCategory.SOUND: {"bg": "#854d0e", "fg": "#fef08a", "label": "Sound (FMOD)"},
    ModCategory.PHYSICS: {"bg": "#374151", "fg": "#e5e7eb", "label": "Physik"},
    ModCategory.AI_TRAFFIC: {"bg": "#365314", "fg": "#d9f99d", "label": "KI-Verkehr"},
    ModCategory.PAINT_JOB: {"bg": "#581c87", "fg": "#e9d5ff", "label": "Skin / Lackierung"},
    ModCategory.CARGO: {"bg": "#451a03", "fg": "#fed7aa", "label": "Fracht (Cargo)"},
    ModCategory.GRAPHICS: {"bg": "#0c4a6e", "fg": "#bae6fd", "label": "Grafik"},
    ModCategory.WEATHER: {"bg": "#134e4a", "fg": "#99f6e4", "label": "Wetter / Klima"},
    ModCategory.UI: {"bg": "#312e81", "fg": "#c7d2fe", "label": "UI / HUD"},
    ModCategory.OTHER: {"bg": "#334155", "fg": "#cbd5e1", "label": "Sonstige"},
}


def get_category_badge_style(category: ModCategory) -> str:
    """Returns CSS style string for a category badge."""
    info = CATEGORY_STYLES.get(category, CATEGORY_STYLES[ModCategory.OTHER])
    return (
        f"background-color: {info['bg']}; "
        f"color: {info['fg']}; "
        f"padding: 3px 8px; "
        f"border-radius: 4px; "
        f"font-size: 11px; "
        f"font-weight: bold;"
    )
