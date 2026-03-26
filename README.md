# BiS Buddy - WoW Addon

Best-in-Slot gear for your current class & specialization, right in the game via a minimap icon.
Data is **automatically** generated from [SimulationCraft](https://github.com/simulationcraft/simc) profiles — no manual updating required.

## Features

- Minimap icon (draggable)
- Automatic class/spec detection
- Item tooltips on hover
- Green/red indicator for equipped BiS items
- Progress tracker (X/Y BiS items equipped)
- Auto-refresh on spec change
- Post item links to chat by clicking
- Slash commands: `/bis`, `/bis info`, `/bis help`

## Automatic Updates

The addon uses a **fully automated pipeline**:

```
SimulationCraft GitHub → GitHub Action (weekly) → Data.lua → CurseForge Release
                                                              ↓
                                                  CurseForge App / WowUp
                                                              ↓
                                                     Your Addon Folder ✓
```

No action needed — CurseForge/WowUp updates the addon automatically with fresh data.

## Why SimulationCraft?

SimC profiles are the most reliable BiS source:
- Maintained by experienced community theorycrafters
- Structured text format (no fragile HTML scraping)
- Powers Raidbots and most BiS recommendations
- Public on GitHub, machine-readable, regularly updated

## Manual Update (without GitHub Actions)

If you don't want to use the pipeline:
```bash
python tools/simc_updater.py --output Data.lua
```

Then copy `Data.lua` into the addon folder.
