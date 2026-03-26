#!/usr/bin/env python3
"""
BiS Buddy - SimulationCraft Profile Parser
============================================
Fetches BiS profiles from the SimulationCraft GitHub repository
and generates the Data.lua for the WoW addon.
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
# Configuration
# =============================================================================

SIMC_RAW_BASE = "https://raw.githubusercontent.com/simulationcraft/simc"
SIMC_API_BASE = "https://api.github.com/repos/simulationcraft/simc"

DEFAULT_BRANCH = "midnight"
DEFAULT_TIER = "MID1"

SIMC_SLOT_MAP = {
    "head": 1, "neck": 2, "shoulder": 3, "shoulders": 3,
    "chest": 5, "waist": 6, "legs": 7, "feet": 8,
    "wrist": 9, "wrists": 9, "hands": 10,
    "finger1": 11, "finger2": 12,
    "trinket1": 13, "trinket2": 14,
    "back": 15, "main_hand": 16, "off_hand": 17,
}

CLASS_CONFIG = {
    "Death_Knight": {
        "key": "DEATHKNIGHT",
        "specs": {
            "Blood": {"index": 1, "name": "Blood"},
            "Frost": {"index": 2, "name": "Frost"},
            "Unholy": {"index": 3, "name": "Unholy"},
        },
    },
    "Demon_Hunter": {
        "key": "DEMONHUNTER",
        "specs": {
            "Havoc": {"index": 1, "name": "Havoc"},
            "Vengeance": {"index": 2, "name": "Vengeance"},
        },
    },
    "Druid": {
        "key": "DRUID",
        "specs": {
            "Balance": {"index": 1, "name": "Balance"},
            "Feral": {"index": 2, "name": "Feral"},
            "Guardian": {"index": 3, "name": "Guardian"},
            "Restoration": {"index": 4, "name": "Restoration"},
        },
    },
    "Evoker": {
        "key": "EVOKER",
        "specs": {
            "Devastation": {"index": 1, "name": "Devastation"},
            "Preservation": {"index": 2, "name": "Preservation"},
            "Augmentation": {"index": 3, "name": "Augmentation"},
        },
    },
    "Hunter": {
        "key": "HUNTER",
        "specs": {
            "Beast_Mastery": {"index": 1, "name": "Beast Mastery"},
            "Marksmanship": {"index": 2, "name": "Marksmanship"},
            "Survival": {"index": 3, "name": "Survival"},
        },
    },
    "Mage": {
        "key": "MAGE",
        "specs": {
            "Arcane": {"index": 1, "name": "Arcane"},
            "Fire": {"index": 2, "name": "Fire"},
            "Frost": {"index": 3, "name": "Frost"},
        },
    },
    "Monk": {
        "key": "MONK",
        "specs": {
            "Brewmaster": {"index": 1, "name": "Brewmaster"},
            "Mistweaver": {"index": 2, "name": "Mistweaver"},
            "Windwalker": {"index": 3, "name": "Windwalker"},
        },
    },
    "Paladin": {
        "key": "PALADIN",
        "specs": {
            "Holy": {"index": 1, "name": "Holy"},
            "Protection": {"index": 2, "name": "Protection"},
            "Retribution": {"index": 3, "name": "Retribution"},
        },
    },
    "Priest": {
        "key": "PRIEST",
        "specs": {
            "Discipline": {"index": 1, "name": "Discipline"},
            "Holy": {"index": 2, "name": "Holy"},
            "Shadow": {"index": 3, "name": "Shadow"},
        },
    },
    "Rogue": {
        "key": "ROGUE",
        "specs": {
            "Assassination": {"index": 1, "name": "Assassination"},
            "Outlaw": {"index": 2, "name": "Outlaw"},
            "Subtlety": {"index": 3, "name": "Subtlety"},
        },
    },
    "Shaman": {
        "key": "SHAMAN",
        "specs": {
            "Elemental": {"index": 1, "name": "Elemental"},
            "Enhancement": {"index": 2, "name": "Enhancement"},
            "Restoration": {"index": 3, "name": "Restoration"},
        },
    },
    "Warlock": {
        "key": "WARLOCK",
        "specs": {
            "Affliction": {"index": 1, "name": "Affliction"},
            "Demonology": {"index": 2, "name": "Demonology"},
            "Destruction": {"index": 3, "name": "Destruction"},
        },
    },
    "Warrior": {
        "key": "WARRIOR",
        "specs": {
            "Arms": {"index": 1, "name": "Arms"},
            "Fury": {"index": 2, "name": "Fury"},
            "Protection": {"index": 3, "name": "Protection"},
        },
    },
}

SLOT_NAMES = {
    1: "Head", 2: "Neck", 3: "Shoulder", 5: "Chest",
    6: "Waist", 7: "Legs", 8: "Feet", 9: "Wrists",
    10: "Hands", 11: "Ring 1", 12: "Ring 2",
    13: "Trinket 1", 14: "Trinket 2", 15: "Back",
    16: "Main Hand", 17: "Off Hand",
}


def fetch_url(url):
    req = Request(url, headers={
        "User-Agent": "BiSBuddy-Updater/1.0",
        "Accept": "application/vnd.github.v3+json",
    })
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except URLError as e:
        print("  ERROR fetching {}: {}".format(url, e))
        return None


def list_simc_profiles(branch, tier):
    api_url = "{}/contents/profiles/{}?ref={}".format(SIMC_API_BASE, tier, branch)
    content = fetch_url(api_url)
    if not content:
        print("  GitHub API unreachable, using known filenames...")
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
            names.append("{}_{}_{}.simc".format(tier, class_slug, spec_slug))
    return names


def fetch_simc_profile(branch, tier, filename):
    url = "{}/{}/profiles/{}/{}".format(SIMC_RAW_BASE, branch, tier, filename)
    return fetch_url(url)


def parse_filename(filename):
    name = filename.replace(".simc", "")
    name = re.sub(r'^[A-Z0-9]+_', '', name, count=1)

    for class_slug in sorted(CLASS_CONFIG.keys(), key=len, reverse=True):
        if name.startswith(class_slug + "_"):
            rest = name[len(class_slug) + 1:]
            for spec_slug in sorted(CLASS_CONFIG[class_slug]["specs"].keys(), key=len, reverse=True):
                if rest == spec_slug:
                    return (class_slug, spec_slug, False)
                elif rest.startswith(spec_slug + "_"):
                    return (class_slug, spec_slug, True)
            parts = rest.split("_", 1)
            if parts[0] in CLASS_CONFIG[class_slug]["specs"]:
                return (class_slug, parts[0], len(parts) > 1)
        elif name == class_slug:
            return (class_slug, None, False)

    for class_slug in sorted(CLASS_CONFIG.keys(), key=len, reverse=True):
        idx = name.find(class_slug)
        if idx >= 0:
            subname = name[idx:]
            if subname.startswith(class_slug + "_"):
                rest = subname[len(class_slug) + 1:]
                for spec_slug in CLASS_CONFIG[class_slug]["specs"]:
                    if rest == spec_slug or rest.startswith(spec_slug):
                        return (class_slug, spec_slug, rest != spec_slug)
    return None


def parse_simc_profile(content):
    gear = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
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
        gear[slot_id] = {"itemID": item_id, "bonus_ids": bonus_ids}
    return gear


def escape_lua(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def generate_data_lua(all_data, tier):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        "-- ============================================================================",
        "-- BiS Buddy - Data (auto-generated {})".format(today),
        "-- Source: SimulationCraft {} Profiles".format(tier),
        "-- DO NOT EDIT MANUALLY!",
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
    for slot_id, name in sorted(SLOT_NAMES.items()):
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
                bonus = escape_lua(item.get("bonus_ids", ""))
                parts = ['itemID = {}'.format(item_id), 'name = "Item #{}"'.format(item_id)]
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
        '    ["Warrior"]        = "WARRIOR",',
        '    ["Mage"]           = "MAGE",',
        '    ["Priest"]         = "PRIEST",',
        '    ["Rogue"]          = "ROGUE",',
        '    ["Hunter"]         = "HUNTER",',
        '    ["Warlock"]        = "WARLOCK",',
        '    ["Shaman"]         = "SHAMAN",',
        '    ["Druid"]          = "DRUID",',
        '    ["Paladin"]        = "PALADIN",',
        '    ["Death Knight"]   = "DEATHKNIGHT",',
        '    ["Monk"]           = "MONK",',
        '    ["Demon Hunter"]   = "DEMONHUNTER",',
        '    ["Evoker"]         = "EVOKER",',
        '    ["Krieger"]        = "WARRIOR",',
        '    ["Magier"]         = "MAGE",',
        '    ["Priester"]       = "PRIEST",',
        '    ["Schurke"]        = "ROGUE",',
        '    ["Jaeger"]         = "HUNTER",',
        '    ["Hexenmeister"]   = "WARLOCK",',
        '    ["Schamane"]       = "SHAMAN",',
        '    ["Druide"]         = "DRUID",',
        '    ["Todesritter"]    = "DEATHKNIGHT",',
        '    ["Moench"]         = "MONK",',
        '    ["Daemonenjaeger"] = "DEMONHUNTER",',
        '    ["Rufer"]          = "EVOKER",',
        "}",
    ])
    return "\n".join(lines) + "\n"


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

    print("\nSearching profiles in {}...".format(args.tier))
    filenames = list_simc_profiles(args.branch, args.tier)
    print("  {} files found".format(len(filenames)))

    if args.classes:
        filter_classes = [c.lower() for c in args.classes]
        filenames = [f for f in filenames if any(c in f.lower() for c in filter_classes)]
        print("  After filter: {} files".format(len(filenames)))

    all_data = {}
    processed = 0
    skipped = 0
    variants_skipped = 0

    for filename in sorted(filenames):
        parsed = parse_filename(filename)
        if not parsed:
            print("  Skipped (unknown format): {}".format(filename))
            skipped += 1
            continue

        class_slug, spec_slug, is_variant = parsed

        if spec_slug is None:
            print("  Skipped (no spec): {}".format(filename))
            skipped += 1
            continue

        if class_slug not in CLASS_CONFIG:
            print("  Skipped (unknown class): {}".format(filename))
            skipped += 1
            continue

        class_info = CLASS_CONFIG[class_slug]

        if spec_slug not in class_info["specs"]:
            print("  Skipped (unknown spec '{}'): {}".format(spec_slug, filename))
            skipped += 1
            continue

        if is_variant:
            print("  Variant skipped: {}".format(filename))
            variants_skipped += 1
            continue

        spec_info = class_info["specs"][spec_slug]
        class_key = class_info["key"]
        spec_index = spec_info["index"]

        if class_key in all_data and spec_index in all_data[class_key]:
            print("  Duplicate skipped: {}".format(filename))
            continue

        print("\n  {} - {} ({})".format(class_key, spec_info["name"], filename))

        content = fetch_simc_profile(args.branch, args.tier, filename)
        if not content:
            print("    ERROR: Could not load profile")
            continue

        gear = parse_simc_profile(content)
        if not gear:
            print("    WARNING: No gear data found")
            continue

        print("    {} slots found".format(len(gear)))

        if class_key not in all_data:
            all_data[class_key] = {}

        all_data[class_key][spec_index] = {
            "specName": spec_info["name"],
            "gear": {slot_id: {"itemID": item["itemID"], "bonus_ids": item.get("bonus_ids", "")}
                     for slot_id, item in gear.items()},
        }
        processed += 1

    print("\n" + "=" * 60)
    print("Processed: {} | Skipped: {} | Variants: {}".format(
        processed, skipped, variants_skipped))

    if not all_data:
        print("ERROR: No data collected!")
        sys.exit(1)

    lua_content = generate_data_lua(all_data, args.tier)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(lua_content)

    total_specs = sum(len(s) for s in all_data.values())
    print("\nData.lua written: {}".format(args.output))
    print("  {} classes, {} specializations".format(len(all_data), total_specs))


if __name__ == "__main__":
    main()
