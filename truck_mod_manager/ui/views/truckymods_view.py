"""
TruckyMods View for Truck Mod Manager.
Provides an integrated online browser for discovering, searching, and opening mods
from truckymods.io for ETS2 and ATS with safe asynchronous fetching and thumbnail caching.
"""
import math
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6 import sip
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget
)

from truck_mod_manager.core.models import GameType, TruckGame
from truck_mod_manager.core.trucky_api import (
    TRUCKY_CATEGORIES, TruckyClient, TruckyFetchWorker,
    TruckyImageWorker, TruckyModCard
)
from truck_mod_manager.ui.dialogs.download_dialog import DownloadDialog
from truck_mod_manager.ui.dialogs.url_download_dialog import UrlDownloadDialog


PAGE_SIZE = 15


class ModCardWidget(QFrame):
    download_requested = pyqtSignal(object)

    def __init__(self, mod: TruckyModCard, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.setObjectName("truckyCard")
        self.setStyleSheet("""
            QFrame#truckyCard {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame#truckyCard:hover {
                border-color: #3b82f6;
                background-color: #243248;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # 1. Thumbnail
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(140, 90)
        self.img_lbl.setStyleSheet("""
            background-color: #0f172a;
            border-radius: 6px;
            border: 1px solid #334155;
            color: #64748b;
            font-size: 24px;
        """)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setText("🚚")
        layout.addWidget(self.img_lbl)

        # 2. Mod Info (Title, Author, Category, Stats)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Title
        title_lbl = QLabel(self.mod.title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        title_lbl.setWordWrap(True)
        info_layout.addWidget(title_lbl)

        # Sub-row: Author & Category
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        author_lbl = QLabel(f"👤 {self.mod.author}")
        author_lbl.setStyleSheet("font-size: 11px; color: #94a3b8; font-weight: 500;")
        meta_layout.addWidget(author_lbl)

        cat_lbl = QLabel(f"🏷️ {self.mod.category}")
        cat_lbl.setStyleSheet("""
            font-size: 11px;
            color: #38bdf8;
            background-color: #0c4a6e;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        meta_layout.addWidget(cat_lbl)

        if self.mod.rating:
            rating_lbl = QLabel(f"⭐ {self.mod.rating}")
            rating_lbl.setStyleSheet("""
                font-size: 11px;
                color: #fbbf24;
                background-color: #451a03;
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: bold;
            """)
            meta_layout.addWidget(rating_lbl)

        dl_lbl = QLabel(f"📥 {self.mod.downloads}")
        dl_lbl.setStyleSheet("font-size: 11px; color: #10b981; font-weight: bold;")
        meta_layout.addWidget(dl_lbl)

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)
        info_layout.addStretch()

        layout.addLayout(info_layout, 1)

        # 3. Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dl_btn = QPushButton("⚡ Direkt installieren")
        dl_btn.setFixedHeight(30)
        dl_btn.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-weight: bold;
            border: 1px solid #10b981;
            border-radius: 6px;
            padding: 4px 10px;
        """)
        dl_btn.setToolTip("Lädt die Mod direkt von TruckyMods herunter und installiert sie im Mod-Ordner")
        dl_btn.clicked.connect(lambda: self.download_requested.emit(self.mod))
        btn_layout.addWidget(dl_btn)

        open_btn = QPushButton("🌐 Im Browser")
        open_btn.setFixedHeight(26)
        open_btn.setToolTip("Öffnet die Mod-Seite auf truckymods.io zum manuellen Download")
        open_btn.clicked.connect(self._open_in_browser)
        btn_layout.addWidget(open_btn)

        copy_btn = QPushButton("🔗 Link")
        copy_btn.setFixedHeight(24)
        copy_btn.setToolTip("Kopiert den direkten Web-Link in die Zwischenablage")
        copy_btn.clicked.connect(self._copy_link)
        btn_layout.addWidget(copy_btn)

        layout.addLayout(btn_layout)

    def set_thumbnail(self, pixmap: QPixmap):
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.img_lbl.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            self.img_lbl.setPixmap(scaled)

    def _open_in_browser(self):
        if self.mod.url:
            QDesktopServices.openUrl(QUrl(self.mod.url))

    def _copy_link(self):
        if self.mod.url:
            clipboard = QApplication.clipboard()
            clipboard.setText(self.mod.url)


class TruckyModsView(QWidget):
    status_message = pyqtSignal(str)
    mod_downloaded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_game: Optional[TruckGame] = None
        self.game_slug: str = "euro-truck-simulator-2"
        self.cards: List[TruckyModCard] = []
        self.card_widgets: Dict[str, ModCardWidget] = {}
        self.fetch_worker: Optional[TruckyFetchWorker] = None
        self.image_worker: Optional[TruckyImageWorker] = None
        self.current_page: int = 0

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. Search & Filter Bar
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 4px;
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(8, 6, 8, 6)
        filter_layout.setSpacing(10)

        # Game badge
        self.game_badge = QLabel("🇪🇺 ETS2")
        self.game_badge.setStyleSheet("""
            background-color: #1e3a8a;
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        filter_layout.addWidget(self.game_badge)

        # Category Dropdown
        cat_lbl = QLabel("Kategorie:")
        cat_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        filter_layout.addWidget(cat_lbl)

        self.cat_combo = QComboBox()
        self.cat_combo.setFixedHeight(32)
        for slug, label in TRUCKY_CATEGORIES.items():
            self.cat_combo.addItem(label, slug)
        self.cat_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.cat_combo)

        # Search Input
        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(32)
        self.search_input.setPlaceholderText("🔍 Auf TruckyMods suchen (z. B. Scania, Sound, Winter, Map)...")
        self.search_input.returnPressed.connect(self._do_search)
        filter_layout.addWidget(self.search_input, 1)

        # Search Button
        self.search_btn = QPushButton("Suchen")
        self.search_btn.setObjectName("primaryBtn")
        self.search_btn.setFixedHeight(32)
        self.search_btn.clicked.connect(self._do_search)
        filter_layout.addWidget(self.search_btn)

        # Clear / Reset Button
        self.reset_btn = QPushButton("✕")
        self.reset_btn.setToolTip("Suche zurücksetzen")
        self.reset_btn.setFixedSize(32, 32)
        self.reset_btn.clicked.connect(self._reset_search)
        filter_layout.addWidget(self.reset_btn)

        # Refresh Button
        self.refresh_btn = QPushButton("🔄 Neu laden")
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self.refresh_btn)

        # URL Download Button
        self.url_dl_btn = QPushButton("📥 URL-Download")
        self.url_dl_btn.setFixedHeight(32)
        self.url_dl_btn.setToolTip("Mod oder ProMods über beliebigen Direktlink herunterladen")
        self.url_dl_btn.clicked.connect(self._open_url_download_dialog)
        filter_layout.addWidget(self.url_dl_btn)

        main_layout.addWidget(filter_frame)

        # 2. Status & Loading Info
        self.info_lbl = QLabel("Bereit zum Durchstöbern von TruckyMods")
        self.info_lbl.setStyleSheet("color: #94a3b8; font-size: 12px; margin-left: 4px;")
        main_layout.addWidget(self.info_lbl)

        # 3. Mod Cards Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)

        self.scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll_area, 1)

        # 4. Pagination Bar
        self.pagination_frame = QFrame()
        self.pagination_frame.setStyleSheet("""
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 4px;
        """)
        p_layout = QHBoxLayout(self.pagination_frame)
        p_layout.setContentsMargins(8, 4, 8, 4)
        p_layout.setSpacing(10)

        self.prev_page_btn = QPushButton("◀ Vorherige Seite")
        self.prev_page_btn.setFixedHeight(28)
        self.prev_page_btn.clicked.connect(self._prev_page)
        p_layout.addWidget(self.prev_page_btn)

        p_layout.addStretch()

        self.page_info_lbl = QLabel("Seite 1 von 1")
        self.page_info_lbl.setStyleSheet("color: #f8fafc; font-weight: bold; font-size: 12px;")
        p_layout.addWidget(self.page_info_lbl)

        p_layout.addStretch()

        self.next_page_btn = QPushButton("Nächste Seite ▶")
        self.next_page_btn.setFixedHeight(28)
        self.next_page_btn.clicked.connect(self._next_page)
        p_layout.addWidget(self.next_page_btn)

        self.pagination_frame.setVisible(False)
        main_layout.addWidget(self.pagination_frame)

    def set_game(self, game: TruckGame):
        self.current_game = game
        old_slug = self.game_slug
        if game.game_type == GameType.ATS:
            self.game_slug = "american-truck-simulator"
            self.game_badge.setText("🇺🇸 ATS")
            self.game_badge.setStyleSheet("""
                background-color: #7f1d1d;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 6px;
            """)
        else:
            self.game_slug = "euro-truck-simulator-2"
            self.game_badge.setText("🇪🇺 ETS2")
            self.game_badge.setStyleSheet("""
                background-color: #1e3a8a;
                color: #ffffff;
                font-weight: bold;
                font-size: 12px;
                padding: 4px 10px;
                border-radius: 6px;
            """)

        # If game actually changed and we have cards loaded, refresh
        if old_slug != self.game_slug and self.cards:
            self.refresh()

    def ensure_loaded(self):
        if not self.cards and (not self.fetch_worker or not self.fetch_worker.isRunning()):
            self.refresh()

    def stop_workers(self):
        if self.fetch_worker and self.fetch_worker.isRunning():
            try:
                self.fetch_worker.results_ready.disconnect()
                self.fetch_worker.error_occurred.disconnect()
            except Exception:
                pass
            self.fetch_worker.requestInterruption()
            self.fetch_worker.wait(300)
        if self.image_worker and self.image_worker.isRunning():
            try:
                self.image_worker.image_ready.disconnect()
            except Exception:
                pass
            self.image_worker.requestInterruption()
            self.image_worker.wait(300)

    def refresh(self):
        cat_slug = self.cat_combo.currentData() or "all"
        query = self.search_input.text().strip()
        self._start_fetch(query=query, category=cat_slug)

    def _do_search(self):
        query = self.search_input.text().strip()
        self._start_fetch(query=query, category=self.cat_combo.currentData() or "all")

    def _reset_search(self):
        self.search_input.clear()
        self.cat_combo.setCurrentIndex(0)
        self._start_fetch(query="", category="all")

    def _on_filter_changed(self):
        if not self.search_input.text().strip():
            self._start_fetch(query="", category=self.cat_combo.currentData() or "all")

    def _start_fetch(self, query: str = "", category: str = "all"):
        # Safely disconnect any running worker without terminate()
        self.stop_workers()

        self.info_lbl.setText("⏳ Lade Mods von TruckyMods.io...")
        self.search_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)

        self.fetch_worker = TruckyFetchWorker(
            query=query,
            category=category,
            game_slug=self.game_slug,
            parent=self
        )
        self.fetch_worker.results_ready.connect(self._on_results_ready)
        self.fetch_worker.error_occurred.connect(self._on_fetch_error)
        self.fetch_worker.finished.connect(self._on_fetch_finished)
        self.fetch_worker.start()

    def _on_results_ready(self, cards: List[TruckyModCard]):
        self.cards = cards
        self.current_page = 0
        self._render_current_page()

    def _on_fetch_error(self, error_msg: str):
        self.info_lbl.setText(f"❌ Fehler beim Laden von TruckyMods: {error_msg}")

    def _on_fetch_finished(self):
        self.search_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)

    @property
    def total_pages(self) -> int:
        if not self.cards:
            return 1
        return max(1, math.ceil(len(self.cards) / PAGE_SIZE))

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._render_current_page()
            self.scroll_area.verticalScrollBar().setValue(0)

    def _next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._render_current_page()
            self.scroll_area.verticalScrollBar().setValue(0)

    def _render_current_page(self):
        # Disconnect and interrupt existing image worker
        if self.image_worker and self.image_worker.isRunning():
            try:
                self.image_worker.image_ready.disconnect()
            except Exception:
                pass
            self.image_worker.requestInterruption()

        # Clear existing card widgets
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.card_widgets.clear()

        if not self.cards:
            no_mods_lbl = QLabel("Keine Mods für diese Auswahl gefunden.")
            no_mods_lbl.setStyleSheet("color: #94a3b8; font-size: 14px; padding: 20px;")
            no_mods_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cards_layout.addWidget(no_mods_lbl)
            self.cards_layout.addStretch()
            self.info_lbl.setText("0 Mods gefunden.")
            self.pagination_frame.setVisible(False)
            return

        total_count = len(self.cards)
        tot_pages = self.total_pages
        start_idx = self.current_page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, total_count)
        page_cards = self.cards[start_idx:end_idx]

        # Update status and pagination
        game_name = self.current_game.name if self.current_game else "Truck Simulator"
        self.info_lbl.setText(f"{total_count} Mods auf TruckyMods gefunden für {game_name}")
        self.page_info_lbl.setText(f"Seite {self.current_page + 1} von {tot_pages} ({start_idx + 1}–{end_idx} von {total_count})")
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < tot_pages - 1)
        self.pagination_frame.setVisible(tot_pages > 1)

        images_to_download: List[str] = []

        for mod in page_cards:
            card_widget = ModCardWidget(mod)
            card_widget.download_requested.connect(self._on_download_requested)
            self.card_widgets[mod.image_url] = card_widget
            self.cards_layout.addWidget(card_widget)

            # Check if thumbnail is already cached locally (instant disk lookup, NO network call)
            if mod.image_url:
                cached = TruckyClient.get_cached_thumbnail(mod.image_url)
                if cached and cached.exists():
                    pix = QPixmap(str(cached))
                    card_widget.set_thumbnail(pix)
                else:
                    images_to_download.append(mod.image_url)

        self.cards_layout.addStretch()

        # Download missing thumbnails asynchronously in background worker
        if images_to_download:
            self.image_worker = TruckyImageWorker(images_to_download, parent=self)
            self.image_worker.image_ready.connect(self._on_image_ready)
            self.image_worker.start()

    def _on_download_requested(self, mod: TruckyModCard):
        target_dir = Path(self.current_game.mod_dir) if self.current_game and self.current_game.mod_dir else Path.home() / ".local/share/truck-mod-manager/mods"
        dlg = DownloadDialog(
            title=mod.title,
            target_dir=target_dir,
            trucky_mod_url=mod.url,
            suggested_filename=f"{mod.id}.scs",
            parent=self
        )
        dlg.download_completed.connect(lambda files: self.mod_downloaded.emit())
        dlg.exec()

    def _open_url_download_dialog(self):
        if not self.current_game:
            return
        dlg = UrlDownloadDialog(self.current_game, parent=self)
        dlg.download_success.connect(lambda files: self.mod_downloaded.emit())
        dlg.exec()

    def _on_image_ready(self, url: str, local_path: str):
        if url in self.card_widgets:
            widget = self.card_widgets[url]
            try:
                if not sip.isdeleted(widget):
                    pix = QPixmap(local_path)
                    if not pix.isNull():
                        widget.set_thumbnail(pix)
            except Exception:
                pass
