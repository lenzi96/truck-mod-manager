"""
Unit tests for TruckyClient and TruckyModCard parsing.
"""
import unittest

from truck_mod_manager.core.trucky_api import (
    TRUCKY_CATEGORIES, TruckyClient, TruckyModCard
)


SAMPLE_HTML = """
<div class="card mb-10">
    <div class="grid columns-3">
        <div class="card project-card card-bordered">
            <div class="mx-6 mt-6 position-relative">
                <div class="info-overlay category-overlay">
                    <a href="https://truckymods.io/euro-truck-simulator-2/maps" class="text-white">Maps</a>
                </div>
                <div class="me-3 info-overlay rating-overlay">
                    <span class="text-premium">4.9</span>
                </div>
                <div class="info-overlay download-overlay">
                    <div class="percent text-success"><i class="bi bi-download"></i> 150,200</div>
                </div>
                <a href=https://truckymods.io/euro-truck-simulator-2/maps/grand-utopia-map title="Grand Utopia Map">
                    <img class="card-img lazy" src="/assets/placeholder.png" data-src="https://storage.truckymods.io/utopia.webp">
                </a>
            </div>
            <div class="card-body">
                <a href="https://truckymods.io/user/123" class="text-muted"><i class="bi bi-person"></i> MyGodness</a>
                <div class="card-title fs-2">
                    <a class="text-white" href=https://truckymods.io/euro-truck-simulator-2/maps/grand-utopia-map title="Grand Utopia Map">Grand Utopia Map</a>
                </div>
            </div>
        </div>

        <div class="card project-card card-bordered">
            <div class="mx-6 mt-6 position-relative">
                <div class="info-overlay category-overlay">
                    <a href="https://truckymods.io/american-truck-simulator/trucks" class="text-white">Trucks</a>
                </div>
                <div class="me-3 info-overlay rating-overlay">
                    <span class="text-premium">4.8</span>
                </div>
                <div class="info-overlay download-overlay">
                    <div class="percent text-success">85,410</div>
                </div>
                <a href=https://truckymods.io/american-truck-simulator/trucks/kenworth-w900-custom title="Kenworth W900 Custom">
                    <img class="card-img lazy" src="https://storage.truckymods.io/kenworth.png">
                </a>
            </div>
            <div class="card-body">
                <a href="https://truckymods.io/user/456" class="text-muted">TruckerDan</a>
                <div class="card-title fs-2">
                    <a class="text-white" href=https://truckymods.io/american-truck-simulator/trucks/kenworth-w900-custom title="Kenworth W900 Custom">Kenworth W900 Custom</a>
                </div>
            </div>
        </div>
    </div>
</div>
"""


class TestTruckyApi(unittest.TestCase):
    def test_parse_cards_success(self):
        cards = TruckyClient.parse_cards(SAMPLE_HTML, default_game="euro-truck-simulator-2")
        self.assertEqual(len(cards), 2)

        # Card 1: ETS2 Grand Utopia
        c1 = cards[0]
        self.assertEqual(c1.title, "Grand Utopia Map")
        self.assertEqual(c1.author, "MyGodness")
        self.assertEqual(c1.category, "Maps")
        self.assertEqual(c1.rating, "4.9")
        self.assertEqual(c1.downloads, "150,200")
        self.assertEqual(c1.url, "https://truckymods.io/euro-truck-simulator-2/maps/grand-utopia-map")
        self.assertEqual(c1.image_url, "https://storage.truckymods.io/utopia.webp")
        self.assertEqual(c1.game_slug, "euro-truck-simulator-2")

        # Card 2: ATS Kenworth
        c2 = cards[1]
        self.assertEqual(c2.title, "Kenworth W900 Custom")
        self.assertEqual(c2.author, "TruckerDan")
        self.assertEqual(c2.category, "Trucks")
        self.assertEqual(c2.rating, "4.8")
        self.assertEqual(c2.downloads, "85,410")
        self.assertEqual(c2.url, "https://truckymods.io/american-truck-simulator/trucks/kenworth-w900-custom")
        self.assertEqual(c2.image_url, "https://storage.truckymods.io/kenworth.png")
        self.assertEqual(c2.game_slug, "american-truck-simulator")

    def test_parse_empty_html(self):
        cards = TruckyClient.parse_cards("<html><body>No cards here</body></html>")
        self.assertEqual(len(cards), 0)

    def test_categories_dict(self):
        self.assertIn("all", TRUCKY_CATEGORIES)
        self.assertIn("maps", TRUCKY_CATEGORIES)
        self.assertIn("trucks", TRUCKY_CATEGORIES)
        self.assertIn("sounds", TRUCKY_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
