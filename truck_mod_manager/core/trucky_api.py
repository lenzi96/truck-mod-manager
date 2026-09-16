"""
TruckyMods API and Web client for ETS2 and ATS.
Fetches popular, trending, category and searched mods from truckymods.io.
Supports asynchronous background downloading and thumbnail caching.
"""
import hashlib
import html
import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from truck_mod_manager.core.config import config



CACHE_DIR = Path(config.get("cache_dir", Path.home() / ".cache" / "truck-mod-manager")) / "thumbnails"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


@dataclass
class TruckyModCard:
    id: str
    title: str
    author: str
    category: str
    downloads: str
    rating: str
    url: str
    image_url: str
    game_slug: str


TRUCKY_CATEGORIES: Dict[str, str] = {
    "all": "Alle Kategorien",
    "maps": "Karten & Maps",
    "trucks": "LKWs & Zugmaschinen",
    "trailers": "Auflieger & Trailer",
    "sounds": "Sounds & Audio",
    "physics": "Physik & Fahrverhalten",
    "graphics": "Grafik & Wetter",
    "cabin-accessories": "Kabine & Zubehör",
    "ai-traffic": "KI-Verkehr & Autos",
    "trailer-paint-jobs": "Trailer-Lackierungen",
    "truck-paint-jobs": "LKW-Lackierungen",
    "bus": "Busse",
    "ui": "UI & Interface",
    "tools": "Tools & Programme",
    "other": "Sonstige Mods",
}


class TruckyClient:
    BASE_URL = "https://truckymods.io"

    @classmethod
    def _http_get(cls, url: str, timeout: int = 12, extra_headers: Optional[Dict[str, str]] = None) -> Optional[str]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if extra_headers:
            headers.update(extra_headers)

        if requests is not None:
            try:
                s = requests.Session()
                s.headers.update(headers)
                r = s.get(url, timeout=timeout)
                if r.status_code == 200:
                    return r.text
            except Exception:
                pass

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if getattr(resp, "status", 200) == 200:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"[TruckyClient] Fehler bei Abruf von {url}: {e}")
        return None

    @classmethod
    def get_session(cls):
        if requests is not None:
            s = requests.Session()
            s.headers.update({
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            })
            return s
        return None

    @classmethod
    def fetch_category(cls, game_slug: str = "euro-truck-simulator-2", category_slug: str = "all") -> List[TruckyModCard]:
        url = f"{cls.BASE_URL}/{game_slug}/{category_slug}"
        text = cls._http_get(url, timeout=12)
        if text:
            return cls.parse_cards(text, default_game=game_slug)
        return []

    @classmethod
    def search(cls, query: str, game_slug: Optional[str] = None) -> List[TruckyModCard]:
        if not query.strip():
            return cls.fetch_category(game_slug or "euro-truck-simulator-2", "all")

        encoded_q = urllib.parse.quote_plus(query.strip())
        url = f"{cls.BASE_URL}/search?query={encoded_q}"
        text = cls._http_get(url, timeout=12)
        if text:
            mods = cls.parse_cards(text, default_game=game_slug or "euro-truck-simulator-2")
            if game_slug:
                filtered = [m for m in mods if game_slug in m.url or not m.game_slug or m.game_slug == game_slug]
                return filtered if filtered else mods
            return mods
        return []


    @classmethod
    def parse_cards(cls, html_content: str, default_game: str = "euro-truck-simulator-2") -> List[TruckyModCard]:
        cards: List[TruckyModCard] = []
        card_blocks = re.findall(
            r'<div class="[^"]*project-card[^"]*">(.*?)(?=<div class="[^"]*project-card|<div class="footer|\Z)',
            html_content,
            re.DOTALL
        )

        for b in card_blocks:
            # Category
            cat_m = re.search(r'category-overlay[^>]*>.*?<a[^>]*>([^<]+)</a>', b, re.DOTALL)
            cat = html.unescape(cat_m.group(1).strip()) if cat_m else "Mod"

            # Rating
            rate_m = re.search(r'rating-overlay[^>]*>.*?<span[^>]*>([0-9.]+)</span>', b, re.DOTALL)
            rate = rate_m.group(1).strip() if rate_m else ""

            # Downloads
            dl_m = re.search(r'download-overlay[^>]*>.*?<div class="percent[^"]*">(?:.*?</i>)?\s*([0-9,]+)', b, re.DOTALL)
            dl = dl_m.group(1).strip() if dl_m else "0"

            # Link & Title
            link_m = re.search(r'<a\s+(?:class="[^"]*"\s+)?href=([^\s>]+)\s+title="([^"]+)"', b)
            if not link_m:
                link_m = re.search(r'href="?(https://truckymods\.io/[^"\s>]+)"?\s+title="([^"]+)"', b)

            if not link_m:
                continue

            raw_link = link_m.group(1).strip('"\'')
            if not raw_link.startswith("http"):
                raw_link = f"https://truckymods.io{raw_link}" if raw_link.startswith("/") else f"https://truckymods.io/{raw_link}"

            raw_title = html.unescape(link_m.group(2).strip())

            # Image data-src or src
            img_m = re.search(r'data-src="([^"]+)"', b)
            if not img_m:
                img_m = re.search(r'src="([^"]+)"', b)
            img_url = img_m.group(1) if img_m else ""

            # Author
            author_m = re.search(r'<a\s+href="https://truckymods\.io/user/[^"]*"[^>]*>(?:.*?</i>)?\s*([^<]+)</a>', b, re.DOTALL)
            author = html.unescape(author_m.group(1).strip()) if author_m else "Community"

            detected_game = default_game
            if "american-truck-simulator" in raw_link:
                detected_game = "american-truck-simulator"
            elif "euro-truck-simulator-2" in raw_link:
                detected_game = "euro-truck-simulator-2"

            mod_id = raw_link.rstrip("/").split("/")[-1]

            cards.append(TruckyModCard(
                id=mod_id,
                title=raw_title,
                author=author,
                category=cat,
                downloads=dl,
                rating=rate,
                url=raw_link,
                image_url=img_url,
                game_slug=detected_game
            ))

        return cards

    @classmethod
    def resolve_direct_download(cls, mod_url: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Resolves the direct Cloudflare R2 download URL and filename from a TruckyMods project page.
        Returns: (success, direct_url, filename, error_message)
        """
        try:
            page_html = cls._http_get(mod_url, timeout=12)
            if not page_html:
                return False, None, None, "Mod-Seite konnte nicht geladen werden."

            proj_m = re.search(r':project_id=\"(\d+)\"', page_html)
            build_m = re.search(r':build_id=\"(\d+)\"', page_html)
            csrf_m = re.search(r'name=\"csrf-token\"\s+content=\"([^\"]+)\"', page_html)

            if not (proj_m and build_m):
                return False, None, None, "Keine direkte Download-Build-ID auf der Mod-Seite gefunden."

            post_url = "https://truckymods.io/projects/createDownloadUrl"
            payload = json.dumps({
                "project_id": int(proj_m.group(1)),
                "build_id": int(build_m.group(1))
            }).encode("utf-8")

            req = urllib.request.Request(post_url, data=payload, headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Referer": mod_url,
                "Origin": "https://truckymods.io",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-TOKEN": csrf_m.group(1) if csrf_m else ""
            })

            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("rateLimited"):
                    return False, None, None, "Rate-Limit erreicht (maximal 1 Download-Erstellung pro Mod pro Minute). Bitte kurz warten."
                if data.get("success") and data.get("url"):
                    return True, data["url"], data.get("fileName", "mod.scs"), None
                return False, None, None, data.get("message", "Direktlink konnte nicht generiert werden.")

        except urllib.error.HTTPError as e:
            return False, None, None, f"API antwortete mit HTTP {e.code}"
        except Exception as e:
            return False, None, None, f"Verbindungsfehler: {e}"

    @classmethod
    def get_cached_thumbnail(cls, image_url: str) -> Optional[Path]:
        """Returns the local path only if already cached on disk. NEVER performs network I/O."""
        if not image_url:
            return None
        ext = ".webp" if ".webp" in image_url else (".png" if ".png" in image_url else ".jpg")
        url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()
        local_path = CACHE_DIR / f"{url_hash}{ext}"
        if local_path.exists() and local_path.stat().st_size > 0:
            return local_path
        return None

    @classmethod
    def download_thumbnail(cls, image_url: str) -> Optional[Path]:
        """Downloads thumbnail to disk cache if not already present. Safe for background worker."""
        if not image_url:
            return None
        cached = cls.get_cached_thumbnail(image_url)
        if cached:
            return cached

        ext = ".webp" if ".webp" in image_url else (".png" if ".png" in image_url else ".jpg")
        url_hash = hashlib.md5(image_url.encode("utf-8")).hexdigest()
        local_path = CACHE_DIR / f"{url_hash}{ext}"

        try:
            req = urllib.request.Request(image_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as resp:
                content = resp.read()
                if len(content) > 0:
                    tmp_path = CACHE_DIR / f"{url_hash}.tmp"
                    with open(tmp_path, "wb") as f:
                        f.write(content)
                    tmp_path.replace(local_path)
                    return local_path
        except Exception:
            pass
        return None


    @classmethod
    def get_thumbnail_path(cls, image_url: str) -> Optional[Path]:
        return cls.get_cached_thumbnail(image_url)


class TruckyFetchWorker(QThread):
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    loading = pyqtSignal(bool)

    def __init__(self, query: str = "", category: str = "all", game_slug: str = "euro-truck-simulator-2", parent=None):
        super().__init__(parent)
        self.query = query.strip()
        self.category = category
        self.game_slug = game_slug

    def run(self):
        self.loading.emit(True)
        try:
            if self.query:
                results = TruckyClient.search(self.query, self.game_slug)
            else:
                results = TruckyClient.fetch_category(self.game_slug, self.category)
            if not self.isInterruptionRequested():
                self.results_ready.emit(results)
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(str(e))
        finally:
            self.loading.emit(False)


class TruckyImageWorker(QThread):
    image_ready = pyqtSignal(str, str)  # image_url, local_path

    def __init__(self, image_urls: List[str], parent=None):
        super().__init__(parent)
        self.image_urls = image_urls

    def run(self):
        for url in self.image_urls:
            if self.isInterruptionRequested():
                break
            try:
                local_path = TruckyClient.download_thumbnail(url)
                if local_path and local_path.exists() and not self.isInterruptionRequested():
                    self.image_ready.emit(url, str(local_path))
            except Exception:
                pass
