# BiS Buddy - WoW Addon

Best-in-Slot Items für deine aktuelle Klasse & Spezialisierung, direkt im Spiel per Minimap-Icon.
Daten werden **automatisch** aus [SimulationCraft](https://github.com/simulationcraft/simc)-Profilen generiert — kein manuelles Updaten nötig.

## Features

- Minimap-Icon (verschiebbar per Drag)
- Automatische Klassen-/Spec-Erkennung
- Item-Tooltips bei Hover
- Grün/Rot-Markierung ob du ein BiS-Item schon trägst
- Fortschrittsanzeige (X/Y BiS Items)
- Auto-Refresh bei Spec-Wechsel
- Chat-Link per Klick auf Items
- Slash-Befehle: `/bis`, `/bis info`, `/bis help`

## Automatische Updates

Das Addon nutzt eine **vollautomatische Pipeline**:

```
SimulationCraft GitHub → GitHub Action (wöchentlich) → Data.lua → CurseForge Release
                                                                  ↓
                                                      CurseForge App / WowUp
                                                                  ↓
                                                         Dein Addon-Ordner ✓
```

Du musst nichts tun — CurseForge/WowUp aktualisiert das Addon automatisch mit frischen Daten.

## Eigenes Repo aufsetzen (Einmalig)

Falls du das Addon selber hosten/publishen willst:

### 1. GitHub Repository erstellen
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/DEIN-USER/BiSBuddy.git
git push -u origin main
```

### 2. CurseForge Projekt erstellen
1. Gehe zu [CurseForge Authors](https://authors.curseforge.com)
2. Erstelle ein neues WoW-Addon-Projekt
3. Notiere die **Projekt-ID** (steht in der URL)
4. Erstelle einen [API-Token](https://authors.curseforge.com/account/api-tokens)

### 3. GitHub Secrets setzen
Im GitHub Repository unter Settings → Secrets → Actions:
- `CF_API_TOKEN` = Dein CurseForge API Token
- `CF_PROJECT_ID` = Deine CurseForge Projekt-ID

### 4. Fertig!
Der GitHub Action Workflow läuft ab jetzt **jeden Mittwoch nach EU-Reset** automatisch.
Du kannst ihn auch manuell über Actions → "Update BiS Data & Release" → "Run workflow" starten.

## Manuelles Update (ohne GitHub Actions)

Falls du die Pipeline nicht nutzen willst:
```bash
pip install requests beautifulsoup4 lxml
python tools/simc_updater.py --output Data.lua
```

Dann `Data.lua` in den Addon-Ordner kopieren.

## Warum SimulationCraft?

SimC-Profile sind die zuverlässigste BiS-Quelle:
- Gepflegt von erfahrenen Theorycraftern der Community
- Strukturiertes Textformat (kein fragiles HTML-Scraping)
- Grundlage für Raidbots und die meisten BiS-Empfehlungen
- Öffentlich auf GitHub, maschinenlesbar, regelmäßig aktualisiert
