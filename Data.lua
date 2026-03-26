-- ============================================================================
-- BiS Buddy - Data (Platzhalter)
-- Diese Datei wird automatisch durch den GitHub Action Workflow ersetzt.
-- Bei Erstinstallation: Führe 'python tools/simc_updater.py' aus oder
-- warte auf das erste automatische Update via CurseForge/WowUp.
-- ============================================================================

BiSBuddyData = BiSBuddyData or {}

BiSBuddyData.dataVersion = "Platzhalter"
BiSBuddyData.dataTier = "Tier33"
BiSBuddyData.dataSource = "SimulationCraft"

BiSBuddyData.SLOTS = {
    [1]  = { name = "Kopf",        slotID = 1  },
    [2]  = { name = "Hals",        slotID = 2  },
    [3]  = { name = "Schulter",    slotID = 3  },
    [5]  = { name = "Brust",       slotID = 5  },
    [6]  = { name = "Taille",      slotID = 6  },
    [7]  = { name = "Beine",       slotID = 7  },
    [8]  = { name = "Füße",        slotID = 8  },
    [9]  = { name = "Handgelenke", slotID = 9  },
    [10] = { name = "Hände",       slotID = 10 },
    [11] = { name = "Ring 1",      slotID = 11 },
    [12] = { name = "Ring 2",      slotID = 12 },
    [13] = { name = "Schmuck 1",   slotID = 13 },
    [14] = { name = "Schmuck 2",   slotID = 14 },
    [15] = { name = "Umhang",      slotID = 15 },
    [16] = { name = "Haupthand",   slotID = 16 },
    [17] = { name = "Nebenhand",   slotID = 17 },
}

BiSBuddyData.items = {}

BiSBuddyData.classMap = {
    ["Krieger"]        = "WARRIOR",
    ["Magier"]         = "MAGE",
    ["Priester"]       = "PRIEST",
    ["Schurke"]        = "ROGUE",
    ["Jäger"]          = "HUNTER",
    ["Hexenmeister"]   = "WARLOCK",
    ["Schamane"]       = "SHAMAN",
    ["Druide"]         = "DRUID",
    ["Paladin"]        = "PALADIN",
    ["Todesritter"]    = "DEATHKNIGHT",
    ["Mönch"]          = "MONK",
    ["Dämonenjäger"]   = "DEMONHUNTER",
    ["Rufer"]          = "EVOKER",
    ["Warrior"]        = "WARRIOR",
    ["Mage"]           = "MAGE",
    ["Priest"]         = "PRIEST",
    ["Rogue"]          = "ROGUE",
    ["Hunter"]         = "HUNTER",
    ["Warlock"]        = "WARLOCK",
    ["Shaman"]         = "SHAMAN",
    ["Druid"]          = "DRUID",
    ["Death Knight"]   = "DEATHKNIGHT",
    ["Monk"]           = "MONK",
    ["Demon Hunter"]   = "DEMONHUNTER",
    ["Evoker"]         = "EVOKER",
}
