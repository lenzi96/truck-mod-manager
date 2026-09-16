# Truck Mod Manager (TMM) for Linux

Ein nativer, moderner und zerstörungsfreier **Mod Manager für Euro Truck Simulator 2 (ETS2) und American Truck Simulator (ATS)** auf Linux (Steam Native & Proton).

![Truck Mod Manager Icon](truck_mod_manager/resources/icon.svg)

---

## 🚀 Highlights & Features

- **Zwei Spiele in einem Manager**:
  - Nahtloses Umschalten zwischen **Euro Truck Simulator 2** und **American Truck Simulator** mit einem Klick im Header.
  - Erkennt automatisch Steam-Installationen, Spielbibliotheken und Datenordner.
  - Vollständige Unterstützung für **Linux Native** (`~/.local/share/...`) und **Steam Proton** (Wine-Präfixe).

- **Spezialisierter SCS- & Manifest-Parser**:
  - Liest `.scs` und `.zip` Archive sowie unentpackte Mod-Ordner direkt.
  - Parst `manifest.sii` und extrahiert Mod-Titel, Autor, Version, Beschreibung und Convoy-Multiplayer-Unterstützung.
  - Extrahiert Mod-Vorschaubilder (`mod_icon.png`) automatisch für die Benutzeroberfläche.
  - Erkennt und kennzeichnet Kategorien: *Map, LKW, Trailer, Tuning, Sound (FMOD), Physik, KI-Verkehr, Lackierungen, Fracht, Grafik, Wetter, UI*.
  - Intelligenter Fallback für ältere Mods ohne `manifest.sii` anhand der internen Dateistruktur (`def/`, `sound/`, `vehicle/`, `map/`).

- **🔍 Automatische Versions- & Kompatibilitätsprüfung**:
  - Ermittelt automatisch die installierte Spielversion aus der `game.log.txt` (z. B. `v1.50.2s`) oder erlaubt manuelle Überschreibung in den Einstellungen.
  - Vergleicht `compatible_versions[]` der Mod mit der aktiven Spielversion (unterstützt Wildcards wie `1.50.*`).
  - Zeigt farbige Status-Badges: `✔ Kompatibel`, `❌ Inkompatibel (Erfordert 1.49.*)` oder `🌐 Universell`.
  - **Absturz-Schutz**: Warnt beim Aktivieren inkompatibler Mods vor möglichen Abstürzen (CTD).
  - Schnellfilter in der Toolbar: *Alle Versionen*, *Nur kompatible Mods*, *Nur inkompatible Mods*.

- **🗑️ Saubere Mod-Löschfunktion**:
  - Schneller Lösch-Button (`🗑️`) direkt auf jeder Mod-Karte sowie in den Mod-Details und im Kontextmenü.
  - Sicherheitsdialog mit Anzeige von Dateipfad, Dateigröße und Bereitstellungsstatus.
  - Entfernt restlos das Staging-Archiv, eventuelle Symlinks/Kopien im `mod/`-Verzeichnis des Spiels und generierte Icon-Caches.

- **Ladereihenfolge & Community Auto-Sort (Load Order)**:
  - Vollständige Prioritätsverwaltung mit Drag & Drop und Pfeiltasten (Position 1 = höchste Priorität).
  - **⚡ SCS Community Auto-Sort**: Sortiert alle aktiven Mods auf Knopfdruck nach der bewährten SCS-Modding-Hierarchie:
    1. *UI & HUD*
    2. *Physik & Wetter / Grafik*
    3. *Sound-Mods (FMOD)*
    4. *KI-Verkehr (AI Traffic)*
    5. *Skins & Lackierungen*
    6. *LKW & Trailer Zubehör / Tuning*
    7. *LKW- & Trailer-Modelle*
    8. *Frachten / Cargo*
    9. *Karten-Fixes & Road Connections (z. B. ProMods - RusMap Connector)*
    10. *Karten-Definitionen (Def)*
    11. *Karten-Dateien (Map)*
    12. *Karten-Modelle (Models 3, 2, 1)*
    13. *Karten-Assets & Backgrounds*

- **Dateikonflikt-Erkennung (Conflict Detector)**:
  - Prüft alle aktiven `.scs` Archive auf identische Pfade (z. B. kollidierende Sound-Banks, Physik-Dateien oder Sektoren).
  - Visualisiert Konflikte direkt in der Ladereihenfolge mit Warn-Badges.
  - Detaillierter Konflikt-Inspektor zeigt an, welche Mod gewinnt und welche Dateien überschrieben werden.

- **`game.log.txt` & Crash Analyzer**:
  - Liest direkt die Spiel-Logdatei und filtert nach `<ERROR>` und `<WARNING>`.
  - Intelligente Ursachen-Erkennung:
    - *Memory Pool Overflow*: Empfiehlt `-mm_pool_size 4096` oder `8192`
    - *Dangling Pointer / Unbekannte Units*: Zeigt defekte LKW- oder Zubehördefinitionen
    - *Missing Sound Bank*: Erkennt veraltete FMOD-Soundmods
    - *Missing Textures*: Findet fehlende Texturen
  - Erkennt Spielabstürze (Crash Dumps) und bietet einen 1-Klick-Export für Foren und Discord.

- **Mod-Presets & Profile**:
  - Speichere beliebige Mod-Zusammenstellungen (z. B. "ProMods 1.50 Komplett", "Vanilla / Convoy Multiplayer", "Heavy Haul").
  - Schneller Wechsel mit einem Klick.
  - Export und Import von Presets als `.json` zum Teilen mit Freunden.

- **Telemetrie- & Plugin-Verwaltung**:
  - Verwaltet native Linux-Plugins (`.so`) in `bin/linux_x64/plugins/` und Proton-DLLs (`.dll`) in `bin/win_x64/plugins/`.
  - Perfekt für SimHub, ETS2 Local Radio, Telemetry Server und Force-Feedback-Plugins.

- **Steam Workshop Integration**:
  - Erkennt abonnierte Workshop-Mods für ETS2 (227300) und ATS (270880).
  - Direktlink zur Steam-Community-Webseite und Größenanzeige.

- **🗺️ ProMods Toolkit & Paket-Inspektor**:
  - Automatische Erkennung aller ProMods-Pakete für ETS2 (**Europe 7-Teiler**, **Middle East Add-On**, **The Great Steppe**, **Trailer & Company Pack (TCP)**) sowie für ATS (**ProMods Canada**).
  - **📥 1-Klick Auto-Import & Multi-Part Entpacker**: Erkennt heruntergeladene ProMods-Archive (z. B. mehrteilige `.7z.001` bis `.007` oder `.zip`) in `~/Downloads`, entpackt alle Teile vollautomatisch mit `7z` und verschiebt die fertigen `.scs`-Dateien direkt in den Mod-Ordner.
  - **🔗 Direktlink-Downloader**: Erlaubt das direkte Einfügen beliebiger URLs (z. B. ProMods 1-Datei-Bezahllink, Google Drive, Mediafire) zum Herunterladen direkt im Manager mit Live-Fortschrittsbalken, Speed- und ETA-Anzeige.
  - **Vollständigkeitsprüfung**: Erkennt unvollständige Archive sofort und benennt fehlende Dateien (z. B. vergessenes `promods-model2-...`).
  - **⚡ 1-Klick offizielle Ladereihenfolge**: Ordnet alle ProMods-Archive und Straßenverbindungen (Road Connectors) exakt nach den offiziellen Entwickler-Vorgaben ein.
  - **Preset-Erstellung**: Speichert die sortierte ProMods-Kombination direkt als Mod-Profil.
  - **Def-Generator Assistent & Map-Combo Guide**: Schneller Sprung zum offiziellen ProMods Definition-Generator sowie Cheatsheet für Kartenkombinationen (ProMods + RusMap + RoEx + Poland Rebuilding).

- **🌐 TruckyMods Online-Browser & Direkt-Download (`truckymods.io`)**:
  - Integrierter Online-Katalog für ETS2 und ATS mit Paginierung (15 Mods pro Seite) und Schnellsuche.
  - **⚡ 1-Klick Direkt-Download**: Generiert autorisierte Direktlinks über die Cloudflare-R2-API und lädt Mods direkt in der Anwendung herunter.
  - **Automatisches Entpacken**: Entpackt heruntergeladene `.7z` und `.zip` Archive selbstständig und bindet die `.scs`-Dateien sofort aktiv in die Mod-Bibliothek ein.
  - **Live-Download-Dialog**: Zeigt Fortschritt in Prozent, Download-Geschwindigkeit (MB/s), verbleibende Zeit und Dateinamen an.
  - Mod-Karten mit Thumbnail-Vorschau (im Hintergrund gecacht), Autor, Bewertung, Download-Zahlen und alternativem Browser-Link.
  - Vollständig asynchron (`QThread`) – Benutzeroberfläche bleibt jederzeit flüssig.

- **🔄 Integrierter GitHub Updater (Cachy Security Suite Architektur)**:
  - **Automatischer Versionsabgleich**: Prüft offizielle GitHub Releases und Tags (`lenzi96/truck-mod-manager`) über die GitHub REST API.
  - **Präziser Versionsvergleich**: Verwendet `vercmp` (Standard auf Arch Linux & CachyOS) mit semantischem Fallback.
  - **Stille Hintergrundprüfung**: Sucht beim Anwendungsstart unaufdringlich nach neuen Versionen und signalisiert Updates mit einem leuchtenden Badge im Header.
  - **1-Klick Self-Update**:
    - *Git-Modus*: Führt `git pull --rebase` und Reinstallation aus.
    - *Standalone-Modus*: Lädt Release-Archive (Tarball / Zip / Asset) herunter, entpackt sie und führt das Installationsskript aus.
  - **Changelog & Release Notes**: Formatierter Markdown-Viewer zeigt alle Neuerungen direkt im Manager.
  - **Live Terminal-Protokoll**: Echtzeit-Konsolenausgabe aller Update-Schritte.
  - **Repository & Token-Verwaltung**: Unterstützung für alternative Repositories und GitHub Personal Access Tokens (PAT) für private Forks oder erweiterte API-Rate-Limits.
  - **1-Klick Neustart**: Startet die aktualisierte Version nahtlos neu.

- **Zerstörungsfreies Staging (Zero Pollution)**:
  - Mods liegen isoliert in `~/.local/share/truck-mod-manager/mods/<game>/`.
  - Bereitstellung erfolgt über Symlinks in den `mod/`-Ordner des Spiels.
  - **"Vanilla Reset"** entfernt alle Mod-Verknüpfungen mit einem Klick restlos.

---


## 📦 Installation

### Option 1: Grafischer Installer (Wizard mit GUI) - Empfohlen

```bash
cd /run/media/julian/HDD/Linux/truck-mod-manager
./gui-installer.py
```
Startet den modernen 5-Schritte Installationsassistenten mit automatischer Systemprüfung, Auswahl des Installationsmodus (Benutzer `~/.local` oder systemweit `/usr`), Deinstallationsoption und Direktstart.

### Option 2: Schnelle Benutzer-Installation (Terminal, ohne Root/Sudo)

```bash
cd /run/media/julian/HDD/Linux/truck-mod-manager
./install.sh --user
```
Installiert den Starter nach `~/.local/bin/truck-mod-manager` und bindet das Programm in dein Startmenü ein.

### Option 3: Systemweite Terminal-Installation

```bash
cd /run/media/julian/HDD/Linux/truck-mod-manager
sudo ./install.sh
```

### Option 4: Direkt aus dem Quellverzeichnis starten

```bash
cd /run/media/julian/HDD/Linux/truck-mod-manager
python3 main.py
```

---

## 📂 Verzeichnisstruktur

- **Einstellungen**: `~/.config/truck-mod-manager/config.json`
- **Mod-Bibliothek**: `~/.local/share/truck-mod-manager/mods/ets2/` und `.../ats/`
- **Presets**: `~/.local/share/truck-mod-manager/presets/`
- **Icon-Cache**: `~/.cache/truck-mod-manager/icons/`

---

## 📜 Lizenz

GPL-3.0-or-later © Julian
