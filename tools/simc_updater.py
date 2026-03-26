#!/usr/bin/env python3
"""
BiS Buddy - SimulationCraft Profile Parser
============================================
Holt BiS-Profile direkt aus dem SimulationCraft GitHub-Repository
und generiert die Data.lua für das WoW Addon.

SimC-Profile sind die zuverlässigste BiS-Quelle:
- Gepflegt von Top-Theorycraftern
- Strukturiertes Textformat (kein HTML-Scraping)
- Grundlage für Raidbots & Co.
- Öffentlich auf GitHub verfügbar

Nutzung:
    python simc_updater.py
    python simc_updater.py --tier Tier33
    python simc_updater.py --output /pfad/zu/Data.lua
"""

import argparse
import os
import re
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

# =============================================================================
# Konfiguration
# =============================================================================

# SimC GitHub Raw-URL Basis
SIMC_RAW_BASE = "https://raw.githubusercontent.com/simulationcraft/simc"
SIMC_API_BASE = "https://api.github.com/repos/simulationcraft/simc"

# Standard-Branch und Tier (wird bei neuen Raids aktualisiert)
DEFAULT_BRANCH = "midnight"
DEFAULT_TIER = "MID1"

# SimC Slot-Name -> WoW Inventory Slot ID
SIMC_SLOT_MAP = {
    "head":      1,
    "neck":      2,
    "shoulder":  3,
    "shoulders": 3,
    "chest":     5,
    "waist":     6,
    "legs":      7,
    "feet":      8,
    "wrist":     9,
    "wrists":    9,
    "hands":     10,
    "finger1":   11,
    "finger2":   12,
    "trinket1":  13,
    "trinket2":  14,
    "back":      15,
    "main_hand": 16,
    "off_hand":  17,
}

# SimC Klassen-Slug -> Addon-Key + Spec-Mapping
# SimC Dateinamen: z.B. "T33_Death_Knight_Blood.simc"
CLASS_CONFIG = {
    "Death_Knight": {
        "key": "DEATHKNIGHT",
        "specs": {
            "Blood":  {"index": 1, "de": "Blut"},
            "Frost":  {"index": 2, "de": "Frost"},
            "Unholy": {"index": 3, "de": "Unheilig"},
        },
    },
    "Demon_Hunter": {
        "key": "DEMONHUNTER",
        "specs": {
            "Havoc":     {"index": 1, "de": "Verwüstung"},
            "Vengeance": {"index": 2, "de": "Rachsucht"},
        },
    },
    "Druid": {
        "key": "DRUID",
        "specs": {
            "Balance":     {"index": 1, "de": "Gleichgewicht"},
            "Feral":       {"index": 2, "de": "Wildheit"},
            "Guardian":    {"index": 3, "de": "Wächter"},
            "Restoration": {"index": 4, "de": "Wiederherstellung"},
        },
    },
    "Evoker": {
        "key": "EVOKER",
        "specs": {
            "Devastation":  {"index": 1, "de": "Verheerung"},
            "Preservation": {"index": 2, "de": "Bewahrung"},
            "Augmentation": {"index": 3, "de": "Erweiterung"},
        },
    },
    "Hunter": {
        "key": "HUNTER",
        "specs": {
            "Beast_Mastery": {"index": 1, "de": "Tierherrschaft"},
            "Marksmanship":  {"index": 2, "de": "Treffsicherheit"},
            "Survival":      {"index": 3, "de": "Überleben"},
        },
    },
    "Mage": {
        "key": "MAGE",
        "specs": {
            "Arcane": {"index": 1, "de": "Arkan"},
            "Fire":   {"index": 2, "de": "Feuer"},
            "Frost":  {"index": 3, "de": "Frost"},
        },
    },
    "Monk": {
        "key": "MONK",
        "specs": {
            "Brewmaster": {"index": 1, "de": "Braumeister"},
            "Mistweaver": {"index": 2, "de": "Nebelwirker"},
            "Windwalker": {"index": 3, "de": "Windläufer"},
        },
    },
    "Paladin": {
        "key": "PALADIN",
        "specs": {
            "Holy":        {"index": 1, "de": "Heilig"},
            "Protection":  {"index": 2, "de": "Schutz"},
            "Retribution": {"index": 3, "de": "Vergeltung"},
        },
    },
    "Priest": {
        "key": "PRIEST",
        "specs": {
            "Discipline": {"index": 1, "de": "Disziplin"},
            "Holy":       {"index": 2, "de": "Heilig"},
            "Shadow":     {"index": 3, "de": "Schatten"},
        },
    },
    "Rogue": {
        "key": "ROGUE",
        "specs": {
            "Assassination": {"index": 1, "de": "Meucheln"},
            "Outlaw":        {"index": 2, "de": "Gesetzlosigkeit"},
            "Subtlety":      {"index": 3, "de": "Täuschung"},
        },
    },
    "Shaman": {
        "key": "SHAMAN",
        "specs": {
            "Elemental":   {"index": 1, "de": "Elementar"},
            "Enhancement": {"index": 2, "de": "Verstärkung"},
            "Restoration": {"index": 3, "de": "Wiederherstellung"},
        },
    },
    "Warlock": {
        "key": "WARLOCK",
        "specs": {
            "Affliction":  {"index": 1, "de": "Gebrechen"},
            "Demonology":  {"index": 2, "de": "Dämonologie"},
            "Destruction": {"index": 3, "de": "Zerstörung"},
        },
    },
    "Warrior": {
        "key": "WARRIOR",
        "specs": {
            "Arms":       {"index": 1, "de": "Waffen"},
            "Fury":       {"index": 2, "de": "Furor"},
            "Protection": {"index": 3, "de": "Schutz"},
        },
    },
}

# Deutsche Slot-Namen
SLOT_NAMES_DE = {
    1: "Kopf", 2: "Hals", 3: "Schulter", 5: "Brust",
    6: "Taille", 7: "Beine", 8: "Füße", 9: "Handgelenke",
    10: "Hände", 11: "Ring 1", 12: "Ring 2",
    13: "Schmuck 1", 14: "Schmuck 2", 15: "Umhang",
    16: "Haupthand", 17: "Nebenhand",
}


# =============================================================================
# GitHub API / Raw Content Fetcher
# =============================================================================

def fetch_url(url: str) -> Optional[str]:
    """Fetcht eine URL und gibt den Inhalt als String zurück."""
    req = Request(url, headers={
        "User-Agent": "BiSBuddy-Updater/1.0",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except URLError as e:
        print(f"  FEHLER beim Abrufen von {url}: {e}")
        return None


def list_simc_profiles(branch: str, tier: str) -> list[str]:
    """Listet alle .simc Profil-Dateien im Tier-Verzeichnis auf."""
    api_url = f"{SIMC_API_BASE}/contents/profiles/{tier}?ref={branch}"
    content = fetch_url(api_url)
    if not content:
        # Fallback: Bekannte Dateinamen generieren
        print("  GitHub API nicht erreichbar, verwende bekannte Dateinamen...")
        return generate_expected_filenames(tier)

    try:
        files = json.loads(content)
        return [f["name"] for f in files if f["name"].endswith(".simc") and f["type"] == "file"]
    except (json.JSONDecodeError, KeyError):
        return generate_expected_filenames(tier)


def generate_expected_filenames(tier: str) -> list[str]:
    """Generiert die erwarteten SimC-Dateinamen basierend auf CLASS_CONFIG."""
    prefix = tier  # "MID1" stays "MID1"
    names = []
    for class_slug, class_info in CLASS_CONFIG.items():
        for spec_slug in class_info["specs"]:
            names.append(f"{prefix}_{class_slug}_{spec_slug}.simc")
    return names


def fetch_simc_profile(branch: str, tier: str, filename: str) -> Optional[str]:
    """Holt den Inhalt einer SimC-Profildatei."""
    url = f"{SIMC_RAW_BASE}/{branch}/profiles/{tier}/{filename}"
    return fetch_url(url)


# =============================================================================
# SimC Profil-Parser
# =============================================================================

def parse_simc_profile(content: str) -> dict:
    """
    Parst ein SimC-Profil und extrahiert die Gear-Daten.

    SimC-Format Beispiel:
        head=,id=212065,bonus_id=1540/10299,enchant_id=7052
        neck=,id=225577,bonus_id=4786/10299
        ...

    Gibt ein Dict zurück: {slot_id: {"itemID": int, "bonus_ids": str}}
    """
    gear = {}

    for line in content.splitlines():
        line = line.strip()

        # Überspringe Kommentare und leere Zeilen
        if not line or line.startswith("#"):
            continue

        # Gear-Zeilen matchen: slot=,id=XXXXX,...
        match = re.match(r'^(\w+)=.*?,id=(\d+)', line)
        if not match:
            # Alternatives Format: slot=name,id=XXXXX
            match = re.match(r'^(\w+)=[^,]*,id=(\d+)', line)
        if not match:
            continue

        slot_name = match.group(1).lower()
        item_id = int(match.group(2))

        if slot_name not in SIMC_SLOT_MAP:
            continue

        slot_id = SIMC_SLOT_MAP[slot_name]

        # Bonus-IDs extrahieren (optional, für Tooltip-Genauigkeit)
        bonus_match = re.search(r'bonus_id=([0-9/]+)', line)
        bonus_ids = bonus_match.group(1) if bonus_match else ""

        # Enchant extrahieren
        enchant_match = re.search(r'enchant_id=(\d+)', line)
        enchant_id = enchant_match.group(1) if enchant_match else ""

        # Gem extrahieren
        gem_match = re.search(r'gem_id=([0-9/]+)', line)
        gem_ids = gem_match.group(1) if gem_match else ""

        gear[slot_id] = {
            "itemID": item_id,
            "bonus_ids": bonus_ids,
            "enchant_id": enchant_id,
            "gem_ids": gem_ids,
        }

    return gear


def parse_filename(filename: str) -> Optional[tuple[str, str]]:
    """
    Extrahiert Klasse und Spec aus dem SimC-Dateinamen.
    z.B. "T33_Death_Knight_Blood.simc" -> ("Death_Knight", "Blood")
         "T33_Warrior_Arms.simc"       -> ("Warrior", "Arms")
    """
    name = filename.replace(".simc", "")

    # Prefix entfernen (T33_, T32_, etc.)
    name = re.sub(r'^T\d+_', '', name)

    # Bekannte Klassen durchgehen (längste zuerst, für "Death_Knight" vor "Hunter")
    for class_slug in sorted(CLASS_CONFIG.keys(), key=len, reverse=True):
        if name.startswith(class_slug + "_"):
            spec_slug = name[len(class_slug) + 1:]
            return class_slug, spec_slug
        elif name == class_slug:
            return class_slug, None

    return None


# =============================================================================
# Blizzard Item-Name Resolver (optional, per API)
# =============================================================================

def resolve_item_name_blizzard(item_id: int, locale: str = "de_DE") -> Optional[str]:
    """
    Holt den Item-Namen über die Blizzard Community API.
    Braucht keinen API-Key für basic item data.
    """
    url = f"https://www.wowhead.com/item={item_id}&xml"
    try:
        content = fetch_url(url)
        if content:
            match = re.search(r'<name><!\[CDATA\[(.+?)\]\]></name>', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None


def resolve_item_names_batch(item_ids: list[int]) -> dict[int, str]:
    """
    Holt Item-Namen für eine Liste von IDs.
    Nutzt die Wowhead Tooltip-API als schnelle Quelle.
    """
    names = {}
    for item_id in item_ids:
        # Wowhead Tooltip JSON endpoint
        url = f"https://nether.wowhead.com/tooltip/item/{item_id}?dataEnv=1&locale=0"
        try:
            content = fetch_url(url)
            if content:
                data = json.loads(content)
                if "name" in data:
                    names[item_id] = data["name"]
                    continue
        except (json.JSONDecodeError, Exception):
            pass
        names[item_id] = f"Item #{item_id}"
    return names


# =============================================================================
# Lua Generator
# =============================================================================

def escape_lua(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generate_data_lua(all_data: dict, tier: str, resolve_names: bool = False) -> str:
    """Generiert die Data.lua aus den geparseten SimC-Daten."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Optional: Item-Namen auflösen
    if resolve_names:
        print("\nLöse Item-Namen auf (das kann etwas dauern)...")
        all_item_ids = set()
        for class_key, specs in all_data.items():
            for spec_idx, spec_data in specs.items():
                for slot_id, item in spec_data["gear"].items():
                    all_item_ids.add(item["itemID"])
        print(f"  {len(all_item_ids)} einzigartige Items...")
        name_map = resolve_item_names_batch(list(all_item_ids))
    else:
        name_map = {}

    lines = [
        "-- ============================================================================",
        f"-- BiS Buddy - Data (auto-generated {today})",
        f"-- Quelle: SimulationCraft {tier} Profile",
        "-- NICHT MANUELL BEARBEITEN - wird automatisch aktualisiert!",
        "-- ============================================================================",
        "",
        "BiSBuddyData = BiSBuddyData or {}",
        "",
        f'BiSBuddyData.dataVersion = "{today}"',
        f'BiSBuddyData.dataTier = "{tier}"',
        f'BiSBuddyData.dataSource = "SimulationCraft"',
        "",
        "BiSBuddyData.SLOTS = {",
    ]

    for slot_id, name in sorted(SLOT_NAMES_DE.items()):
        lines.append(f'    [{slot_id}] = {{ name = "{name}", slotID = {slot_id} }},')

    lines.append("}")
    lines.append("")
    lines.append("BiSBuddyData.items = {")

    for class_key in sorted(all_data.keys()):
        specs = all_data[class_key]
        lines.append(f"")
        lines.append(f'    ["{class_key}"] = {{')

        for spec_idx in sorted(specs.keys()):
            spec_data = specs[spec_idx]
            spec_name = escape_lua(spec_data["specName"])
            lines.append(f"        [{spec_idx}] = {{")
            lines.append(f'            specName = "{spec_name}",')
            lines.append(f'            source   = "SimulationCraft {tier}",')
            lines.append(f'            updated  = "{today}",')
            lines.append(f"            gear = {{")

            for slot_id in sorted(spec_data["gear"].keys()):
                item = spec_data["gear"][slot_id]
                item_id = item["itemID"]
                item_name = escape_lua(name_map.get(item_id, f"Item #{item_id}"))
                bonus = escape_lua(item.get("bonus_ids", ""))

                parts = [
                    f"itemID = {item_id}",
                    f'name = "{item_name}"',
                ]
                if bonus:
                    parts.append(f'bonusIDs = "{bonus}"')

                lines.append(f'                [{slot_id}] = {{ {", ".join(parts)} }},')

            lines.append(f"            }}")
            lines.append(f"        }},")

        lines.append(f"    }},")

    lines.append("}")
    lines.append("")

    # Klassen-Name Mapping
    lines.extend([
        "BiSBuddyData.classMap = {",
        '    ["Krieger"]        = "WARRIOR",',
        '    ["Magier"]         = "MAGE",',
        '    ["Priester"]       = "PRIEST",',
        '    ["Schurke"]        = "ROGUE",',
        '    ["Jäger"]          = "HUNTER",',
        '    ["Hexenmeister"]   = "WARLOCK",',
        '    ["Schamane"]       = "SHAMAN",',
        '    ["Druide"]         = "DRUID",',
        '    ["Paladin"]        = "PALADIN",',
        '    ["Todesritter"]    = "DEATHKNIGHT",',
        '    ["Mönch"]          = "MONK",',
        '    ["Dämonenjäger"]   = "DEMONHUNTER",',
        '    ["Rufer"]          = "EVOKER",',
        '    ["Warrior"]        = "WARRIOR",',
        '    ["Mage"]           = "MAGE",',
        '    ["Priest"]         = "PRIEST",',
        '    ["Rogue"]          = "ROGUE",',
        '    ["Hunter"]         = "HUNTER",',
        '    ["Warlock"]        = "WARLOCK",',
        '    ["Shaman"]         = "SHAMAN",',
        '    ["Druid"]          = "DRUID",',
        '    ["Death Knight"]   = "DEATHKNIGHT",',
        '    ["Monk"]           = "MONK",',
        '    ["Demon Hunter"]   = "DEMONHUNTER",',
        '    ["Evoker"]         = "EVOKER",',
        "}",
    ])

    return "\n".join(lines) + "\n"


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="BiS Buddy - SimC Profile Updater")
    parser.add_argument("--branch", default=DEFAULT_BRANCH,
                        help=f"SimC Git-Branch (Standard: {DEFAULT_BRANCH})")
    parser.add_argument("--tier", default=DEFAULT_TIER,
                        help=f"Raid-Tier (Standard: {DEFAULT_TIER})")
    parser.add_argument("--output", "-o", default="Data.lua",
                        help="Ausgabe-Pfad für Data.lua")
    parser.add_argument("--resolve-names", action="store_true",
                        help="Item-Namen von Wowhead auflösen (langsamer)")
    parser.add_argument("--classes", nargs="*",
                        help="Nur bestimmte Klassen (z.B. Warrior Mage)")
    args = parser.parse_args()

    print(f"BiS Buddy - SimulationCraft Profile Updater")
    print(f"Branch: {args.branch} | Tier: {args.tier}")
    print(f"{'='*60}")

    # Profil-Dateien auflisten
    print(f"\nSuche Profile in {args.tier}...")
    filenames = list_simc_profiles(args.branch, args.tier)
    print(f"  {len(filenames)} Dateien gefunden")

    # Filter
    if args.classes:
        filter_classes = [c.lower() for c in args.classes]
        filenames = [f for f in filenames
                     if any(c in f.lower() for c in filter_classes)]
        print(f"  Nach Filter: {len(filenames)} Dateien")

    all_data = {}
    processed = 0
    skipped = 0

    for filename in sorted(filenames):
        parsed = parse_filename(filename)
        if not parsed:
            print(f"  Übersprungen (unbekanntes Format): {filename}")
            skipped += 1
            continue

        class_slug, spec_slug = parsed

        if class_slug not in CLASS_CONFIG:
            print(f"  Übersprungen (unbekannte Klasse): {filename}")
            skipped += 1
            continue

        class_info = CLASS_CONFIG[class_slug]

        if spec_slug and spec_slug not in class_info["specs"]:
            # Versuche ohne Underscore (z.B. "BeastMastery" statt "Beast_Mastery")
            found = False
            for known_spec in class_info["specs"]:
                if known_spec.replace("_", "") == spec_slug.replace("_", ""):
                    spec_slug = known_spec
                    found = True
                    break
            if not found:
                print(f"  Übersprungen (unbekannte Spec): {filename}")
                skipped += 1
                continue

        spec_info = class_info["specs"][spec_slug]
        class_key = class_info["key"]
        spec_index = spec_info["index"]

        print(f"\n  {class_key} - {spec_info['de']} ({filename})")

        # Profil-Inhalt holen
        content = fetch_simc_profile(args.branch, args.tier, filename)
        if not content:
            print(f"    FEHLER: Konnte Profil nicht laden")
            continue

        # Parsen
        gear = parse_simc_profile(content)
        if not gear:
            print(f"    WARNUNG: Keine Gear-Daten gefunden")
            continue

        print(f"    {len(gear)} Slots gefunden: {sorted(gear.keys())}")

        # Speichern
        if class_key not in all_data:
            all_data[class_key] = {}

        all_data[class_key][spec_index] = {
            "specName": spec_info["de"],
            "gear": {slot_id: {"itemID": item["itemID"],
                               "bonus_ids": item.get("bonus_ids", ""),
                               "enchant_id": item.get("enchant_id", ""),
                               "gem_ids": item.get("gem_ids", "")}
                     for slot_id, item in gear.items()},
        }
        processed += 1

    print(f"\n{'='*60}")
    print(f"Verarbeitet: {processed} | Übersprungen: {skipped}")

    if not all_data:
        print("FEHLER: Keine Daten gesammelt!")
        sys.exit(1)

    # Lua generieren
    lua_content = generate_data_lua(all_data, args.tier, args.resolve_names)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(lua_content)

    total_specs = sum(len(s) for s in all_data.values())
    print(f"\nData.lua geschrieben: {args.output}")
    print(f"  {len(all_data)} Klassen, {total_specs} Spezialisierungen")


if __name__ == "__main__":
    main()
