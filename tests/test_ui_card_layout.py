"""
Unit tests for UI ModCardWidget and ElidedLabel responsive layout.
"""
import os
import sys
import unittest
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize

os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from truck_mod_manager.core.models import ScsMod, ModCategory, GameType, TruckGame
from truck_mod_manager.ui.widgets.elided_label import ElidedLabel
from truck_mod_manager.ui.views.mods_view import ModCardWidget, ModsView
from truck_mod_manager.ui.views.load_order_view import LoadOrderItemWidget, LoadOrderView


class TestUiCardLayout(unittest.TestCase):
    def setUp(self):
        self.game = TruckGame(
            game_type=GameType.ETS2,
            name="Euro Truck Simulator 2",
            steam_appid="227300",
            is_installed=True,
            detected_game_version="1.50"
        )
        self.long_mod = ScsMod(
            file_path="/tmp/test_long_name_mod.scs",
            file_name="test_long_name_mod_by_some_author_version_2.4.1.scs",
            display_name="A Very Long Mod Display Name That Should Not Break Or Squish The Card Layout",
            author="Author With A Rather Long Name",
            package_version="2.4.1",
            description="Test mod",
            categories=[ModCategory.SOUND, ModCategory.TUNING],
            is_enabled=True,
            priority=1,
            compatible_versions=["1.50"]
        )

    def test_elided_label(self):
        lbl = ElidedLabel("Very long text that needs to be elided when width is small")
        lbl.resize(100, 24)
        lbl._update_elided_text()
        self.assertIn("…", lbl.text())
        self.assertEqual(lbl.full_text, "Very long text that needs to be elided when width is small")
        self.assertEqual(lbl.toolTip(), "Very long text that needs to be elided when width is small")

    def test_mod_card_widget_height(self):
        card = ModCardWidget(self.long_mod, game_version="1.50")
        self.assertGreaterEqual(card.minimumHeight(), 70)

    def test_mods_view_refresh_item_sizing(self):
        view = ModsView()
        view.set_game(self.game, [self.long_mod])
        self.assertEqual(view.mod_list.count(), 1)
        item = view.mod_list.item(0)
        # Verify vertical height is generous and non-zero
        self.assertGreaterEqual(item.sizeHint().height(), 80)
        # Verify width in sizeHint is 0 to allow full width expansion
        self.assertEqual(item.sizeHint().width(), 0)

    def test_load_order_item_sizing(self):
        view = LoadOrderView()
        view.set_game(self.game, [self.long_mod])
        self.assertEqual(view.list_widget.count(), 1)
        item = view.list_widget.item(0)
        self.assertGreaterEqual(item.sizeHint().height(), 74)
        self.assertEqual(item.sizeHint().width(), 0)


if __name__ == "__main__":
    unittest.main()
