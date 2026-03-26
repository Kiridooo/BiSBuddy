#!/usr/bin/env python3
"""
BiS Buddy - SimulationCraft Profile Parser
============================================
Holt BiS-Profile direkt aus dem SimulationCraft GitHub-Repository
und generiert die Data.lua fuer das WoW Addon.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# =============================================================================
# Konfiguration
# =============================================================================

SIMC_RAW_BASE = "https://raw.githubusercontent.com/simulationcraft/simc"
SIMC_API_BASE = "https://api.github.com/repos/simulationcraft/simc"

DEFAULT_BRANCH = "midnight"
DEFAULT_TIER = "MID1"

# SimC Slot-Name -> WoW Inventory Slot ID
SIMC_SLOT_MAP = {
    "head": 1, "neck": 2, "shoulder": 3, "shoulders": 3,
    "chest": 5, "waist": 6, "legs": 7, "feet": 8,
    "wrist": 9, "wrists": 9, "hands": 10,
    "finger1": 11, "finger2": 12,
    "trinket1": 13, "trinket2": 14,
    "back": 15, "main_hand": 16, "off_hand": 17,
}

# Bekannte Klassen-Slugs im SimC-Dateinamen
CLASS_CONFIG = {
    "Death_Knight": {
        "key": "DEATHKNIGHT",
        "specs": {
            "Blood": {"index": 1, "de": "Blut"},
            "Frost": {"index": 2, "de": "Frost"},
            "Unholy": {"index": 3, "de": "Unheilig"},
        },
    },
    "Demon_Hunter": {
        "key": "DEMONHUNTER",
        "specs": {
            "Havoc": {"index": 1, "de": "Verwuestung"},
            "Vengeance": {"index": 2, "de": "Rachsucht"},
        },
    },
    "Druid": {
        "key": "DRUID",
        "specs": {
            "Balance": {"index": 1, "de": "Gleichgewicht"},
            "Feral": {"index": 2, "de": "Wildheit"},
            "Guardian": {"index": 3, "de": "Waechter"},
            "Restoration": {"index": 4, "de": "Wiederherstellung"},
        },
    },
    "Evoker": {
        "key": "EVOKER",
        "specs": {
            "Devastation": {"index": 1, "de": "Verheerung"},
            "Preservation": {"index": 2, "de": "Bewahrung"},
            "Augmentation": {"index": 3, "de": "Erweiterung"},
        },
    },
    "Hunter": {
        "key": "HUNTER",
        "specs": {
            "Beast_Mastery": {"index": 1, "de": "Tierherrschaft"},
            "Marksmanship": {"index": 2, "de": "Treffsicherheit"},
            "Survival": {"index": 3, "de": "Ueberleben"},
        },
    },
    "Mage": {
        "key": "MAGE",
        "specs": {
            "Arcane": {"index": 1, "de": "Arkan"},
            "Fire": {"index": 2, "de": "Feuer"},
            "Frost": {"index": 3, "de": "Frost"},
        },
    },
    "Monk": {
        "key": "MONK",
        "specs": {
            "Brewmaster": {"index": 1, "de": "Braumeister"},
            "Mistweaver": {"index": 2, "de": "Nebelwirker"},
            "Windwalker": {"index": 3, "de": "Windlaeufer"},
        },
    },
    "Paladin": {
        "key": "PALADIN",
        "specs": {
            "Holy": {"index": 1, "de": "Heilig"},
            "Protection": {"index": 2, "de": "Schutz"},
            "Retribution": {"index": 3, "de": "Vergeltung"},
        },
    },
    "Priest": {
        "key": "PRIEST",
        "specs": {
            "Discipline": {"index": 1, "de": "Disziplin"},
            "Holy": {"index": 2, "de": "Heilig"},
            "Shadow": {"index": 3, "de": "Schatten"},
        },
    },
    "Rogue": {
        "key": "ROGUE",
        "specs": {
            "Assassination": {"index": 1, "de": "Meucheln"},
            "Outlaw": {"index": 2, "de": "Gesetzlosigkeit"},
            "Subtlety": {"index": 3, "de": "Taeuschung"},
        },
    },
    "Shaman": {
        "key": "SHAMAN",
        "specs": {
            "Elemental": {"index": 1, "de": "Elementar"},
            "Enhancement": {"index": 2, "de": "Verstaerkung"},
            "Restoration": {"index": 3, "de": "Wiederherstellung"},
        },
    },
    "Warlock": {
        "key": "WARLOCK",
        "specs": {
            "Affliction": {"index": 1, "de": "Gebrechen"},
            "Demonology": {"index": 2, "de": "Daemonologie"},
            "Destruction": {"index": 3, "de": "Zerstoerung"},
        },
    },
    "Warrior": {
        "key": "WARRIOR",
        "specs": {
            "Arms": {"index": 1, "de": "Waffen"},
            "Fury": {"index": 2, "de": "Furor"},
            "Protection": {"index": 3, "de": "Schutz"},
        },
    },
}

SLOT_NAMES_DE = {
    1: "Kopf", 2: "Hals", 3: "Schulter", 5: "Brust",
    6: "Taille", 7: "Beine", 8: "Fuesse", 9: "Handgelenke",
    10: "Haende", 11: "Ring 1", 12: "Ring 2",
    13: "Schmuck 1", 14: "Schmuck 2", 15: "Umhang",
    16: "Haupthand", 17: "Nebenhand",
}


# =============================================================================
# HTTP Helper
# =============================================================================

def fetch_url(url):
    req = Request(url, headers={
        "User-Agent": "BiSBuddy-Updater/1.0",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except URLError as e:
        print("  FEHLER beim Abrufen von {}: {}".format(url, e))
        return None


# =============================================================================
# SimC Profil-Dateien auflisten
# =============================================================================

def list_simc_profiles(branch, tier):
    api_url = "{}/contents/profiles/{}?ref={}".format(SIMC_API_BASE, tier, branch)
    content = fetch_url(api_url)
    if not content:
        print("  GitHub API nicht erreichbar, verwende bekannte Dateinamen...")
        return generate_expected_filenames(tier)
    try:
        files = json.loads(content)
        return [f["name"] for f in files if f["name"].endswith(".simc") and f["type"] == "file"]
    except (json.JSONDecodeError, KeyError):
        return generate_expected_filenames(tier)


def generate_expected_filenames(tier):
    names = []
    for class_slug, class_info in CLASS_CONFIG.items():
        for spec_slug in class_info["specs"]:
            names.append("{}_{}_{}. simc".format(tier, class_slug, spec_slug))
    return names


def fetch_simc_profile(branch, tier, filename):
    url = "{}/{}/profiles/{}/{}".format(SIMC_RAW_BASE, branch, tier, filename)
    return fetch_url(url)


# =============================================================================
# Dateiname parsen - erkennt beliebige Prefixe (MID1_, TWW1_, T33_, etc.)
# =============================================================================

def parse_filename(filename):
    """
    Parst SimC-Dateinamen und gibt (class_slug, spec_slug, is_variant) zurueck.

    Beispiele:
        MID1_Warrior_Arms.simc          -> ("Warrior", "Arms", False)
        MID1_Death_Knight_Blood.simc    -> ("Death_Knight", "Blood", False)
        MID1_Death_Knight_Blood_Deathbringer.simc -> ("Death_Knight", "Blood", True)
        MID1_Mage_Fire_Frostfire.simc   -> ("Mage", "Fire", True)
        TWW1_Warrior_Arms.simc          -> ("Warrior", "Arms", False)
        T33_Warrior_Arms.simc           -> ("Warrior", "Arms", False)
    """
    name = filename.replace(".simc", "")

    # Prefix entfernen: alles vor dem ersten bekannten Klassen-Slug
    # Unterstuetzt MID1_, TWW1_, TWW2_, T33_, PR_ etc.
    name = re.sub(r'^[A-Z0-9]+_', '', name, count=1)

    # Jetzt versuchen wir die Klasse zu erkennen (laengste zuerst)
    for class_slug in sorted(CLASS_CONFIG.keys(), key=len, reverse=True):
        if name.startswith(class_slug + "_"):
            rest = name[len(class_slug) + 1:]

            # Rest koennte "Arms" oder "Blood_Deathbringer" sein
            # Versuche bekannte Specs zu matchen
            for spec_slug in sorted(CLASS_CONFIG[class_slug]["specs"].keys(), key=len, reverse=True):
                if rest == spec_slug:
                    return (class_slug, spec_slug, False)
                elif rest.startswith(spec_slug + "_"):
                    # Variante (z.B. Blood_Deathbringer)
                    return (class_slug, spec_slug, True)

            # Spec nicht erkannt - vielleicht anderes Format
            # Versuche den ersten Teil als Spec
            parts = rest.split("_", 1)
            if parts[0] in CLASS_CONFIG[class_slug]["specs"]:
                is_variant = len(parts) > 1
                return (class_slug, parts[0], is_variant)

        elif name == class_slug:
            return (class_slug, None, False)

    # Nichts erkannt - vielleicht hat der Prefix mehr als ein Segment
    # z.B. "PR_Raid_Warrior_Arms" -> versuche ohne weiteren Prefix
    for class_slug in sorted(CLASS_CONFIG.keys(), key=len, reverse=True):
        idx = name.find(class_slug)
        if idx >= 0:
            subname = name[idx:]
            if subname.startswith(class_slug + "_"):
                rest = subname[len(class_slug) + 1:]
                for spec_slug in CLASS_CONFIG[class_slug]["specs"]:
                    if rest == spec_slug or rest.startswith(spec_slug):
                        is_variant = rest != spec_slug
                        return (class_slug, spec_slug, is_variant)

    return None


# =============================================================================
# SimC Profil parsen
# =============================================================================

def parse_simc_profile(content):
    gear = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Gear-Zeilen: slot=,id=XXXXX,... oder slot=itemname,id=XXXXX,...
        match = re.match(r'^(\w+)=[^,]*,id=(\d+)', line)
        if not match:
            continue

        slot_name = match.group(1).lower()
        item_id = int(match.group(2))

        if slot_name not in SIMC_SLOT_MAP:
            continue

        slot_id = SIMC_SLOT_MAP[slot_name]

        bonus_match = re.search(r'bonus_id=([0-9/]+)', line)
        bonus_ids = bonus_match.group(1) if bonus_match else ""

        gear[slot_id] = {
            "itemID": item_id,
            "bonus_ids": bonus_ids,
        }

    return gear


# =============================================================================
# Lua Generator
# =============================================================================

def escape_lua(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generate_data_lua(all_data, tier):
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "-- ============================================================================",
        "-- BiS Buddy - Data (auto-generated {})".format(today),
        "-- Quelle: SimulationCraft {} Profile".format(tier),
        "-- NICHT MANUELL BEARBEITEN!",
        "-- ============================================================================",
        "",
        "BiSBuddyData = BiSBuddyData or {}",
        "",
        'BiSBuddyData.dataVersion = "{}"'.format(today),
        'BiSBuddyData.dataTier = "{}"'.format(tier),
        'BiSBuddyData.dataSource = "SimulationCraft"',
        "",
        "BiSBuddyData.SLOTS = {",
    ]

    for slot_id, name in sorted(SLOT_NAMES_DE.items()):
        lines.append('    [{}] = {{ name = "{}", slotID = {} }},'.format(slot_id, name, slot_id))

    lines.append("}")
    lines.append("")
    lines.append("BiSBuddyData.items = {")

    for class_key in sorted(all_data.keys()):
        specs = all_data[class_key]
        lines.append("")
        lines.append('    ["{}"] = {{'.format(class_key))

        for spec_idx in sorted(specs.keys()):
            spec_data = specs[spec_idx]
            spec_name = escape_lua(spec_data["specName"])
            lines.append("        [{}] = {{".format(spec_idx))
            lines.append('            specName = "{}",'.format(spec_name))
            lines.append('            source   = "SimulationCraft {}",'.format(tier))
            lines.append('            updated  = "{}",'.format(today))
            lines.append("            gear = {")

            for slot_id in sorted(spec_data["gear"].keys()):
                item = spec_data["gear"][slot_id]
                item_id = item["itemID"]
                item_name = "Item #{}".format(item_id)
                bonus = escape_lua(item.get("bonus_ids", ""))

                parts = ['itemID = {}'.format(item_id), 'name = "{}"'.format(item_name)]
                if bonus:
                    parts.append('bonusIDs = "{}"'.format(bonus))

                lines.append('                [{}] = {{ {} }},'.format(slot_id, ", ".join(parts)))

            lines.append("            }")
            lines.append("        },")

        lines.append("    },")

    lines.append("}")
    lines.append("")

    lines.extend([
        "BiSBuddyData.classMap = {",
        '    ["Krieger"]        = "WARRIOR",',
        '    ["Magier"]         = "MAGE",',
        '    ["Priester"]       = "PRIEST",',
        '    ["Schurke"]        = "ROGUE",',
        '    ["Jaeger"]         = "HUNTER",',
        '    ["Hexenmeister"]   = "WARLOCK",',
        '    ["Schamane"]       = "SHAMAN",',
        '    ["Druide"]         = "DRUID",',
        '    ["Paladin"]        = "PALADIN",',
        '    ["Todesritter"]    = "DEATHKNIGHT",',
        '    ["Moench"]         = "MONK",',
        '    ["Daemonenjaeger"] = "DEMONHUNTER",',
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
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--tier", default=DEFAULT_TIER)
    parser.add_argument("--output", "-o", default="Data.lua")
    parser.add_argument("--classes", nargs="*")
    args = parser.parse_args()

    print("BiS Buddy - SimulationCraft Profile Updater")
    print("Branch: {} | Tier: {}".format(args.branch, args.tier))
    print("=" * 60)

    print("\nSuche Profile in {}...".format(args.tier))
    filenames = list_simc_profiles(args.branch, args.tier)
    print("  {} Dateien gefunden".format(len(filenames)))

    if args.classes:
        filter_classes = [c.lower() for c in args.classes]
        filenames = [f for f in filenames if any(c in f.lower() for c in filter_classes)]
        print("  Nach Filter: {} Dateien".format(len(filenames)))

    all_data = {}
    processed = 0
    skipped = 0
    variants_skipped = 0

    for filename in sorted(filenames):
        parsed = parse_filename(filename)
        if not parsed:
            print("  Uebersprungen (unbekanntes Format): {}".format(filename))
            skipped += 1
            continue

        class_slug, spec_slug, is_variant = parsed

        if spec_slug is None:
            print("  Uebersprungen (kein Spec): {}".format(filename))
            skipped += 1
            continue

        if class_slug not in CLASS_CONFIG:
            print("  Uebersprungen (unbekannte Klasse): {}".format(filename))
            skipped += 1
            continue

        class_info = CLASS_CONFIG[class_slug]

        if spec_slug not in class_info["specs"]:
            print("  Uebersprungen (unbekannte Spec '{}'): {}".format(spec_slug, filename))
            skipped += 1
            continue

        # Varianten-Profile ueberspringen (nur Basis-Profile nehmen)
        if is_variant:
            print("  Variante uebersprungen: {}".format(filename))
            variants_skipped += 1
            continue

        spec_info = class_info["specs"][spec_slug]
        class_key = class_info["key"]
        spec_index = spec_info["index"]

        # Wenn wir fuer diese Klasse/Spec schon Daten haben, ueberspringen
        if class_key in all_data and spec_index in all_data[class_key]:
            print("  Duplikat uebersprungen: {}".format(filename))
            continue

        print("\n  {} - {} ({})".format(class_key, spec_info["de"], filename))

        content = fetch_simc_profile(args.branch, args.tier, filename)
        if not content:
            print("    FEHLER: Konnte Profil nicht laden")
            continue

        gear = parse_simc_profile(content)
        if not gear:
            print("    WARNUNG: Keine Gear-Daten gefunden")
            continue

        print("    {} Slots gefunden".format(len(gear)))

        if class_key not in all_data:
            all_data[class_key] = {}

        all_data[class_key][spec_index] = {
            "specName": spec_info["de"],
            "gear": {slot_id: {"itemID": item["itemID"], "bonus_ids": item.get("bonus_ids", "")}
                     for slot_id, item in gear.items()},
        }
        processed += 1

    print("\n" + "=" * 60)
    print("Verarbeitet: {} | Uebersprungen: {} | Varianten: {}".format(
        processed, skipped, variants_skipped))

    if not all_data:
        print("FEHLER: Keine Daten gesammelt!")
        sys.exit(1)

    lua_content = generate_data_lua(all_data, args.tier)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(lua_content)

    total_specs = sum(len(s) for s in all_data.values())
    print("\nData.lua geschrieben: {}".format(args.output))
    print("  {} Klassen, {} Spezialisierungen".format(len(all_data), total_specs))


if __name__ == "__main__":
    main()
