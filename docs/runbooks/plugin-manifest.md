# Plugin Manifest / Lock

The plugin manifest is the safety layer before installing MetaMod, CounterStrikeSharp, or mode plugins.

Current file:

```text
plugins/plugins.yaml
```

It declares plugin candidates and their status, but does not install plugin binaries yet.

## Phases

```text
planned   known candidate, not installed yet
disabled  explicitly not allowed in mode startup
staged    installed in image/PVC for testing, not default everywhere
enabled   allowed to load for declared modes
```

## Rules

- Every plugin referenced by a mode profile must exist in `plugins/plugins.yaml`.
- A mode cannot enable a plugin with `phase: disabled`.
- Heavy plugins stay disabled or mode-specific; never default/global.
- `enabledByDefault` should remain `false` unless the plugin is safe in the base platform.
- `sha256` is required even while pending; placeholder zero hashes mark plugins not downloaded/pinned yet.

## Validate

```bash
PYTHONPATH=src python -m cs2_tools.plugin_manifest plugins/plugins.yaml
PYTHONPATH=src python -m cs2_tools.validate_mode \
  configs/modes/multicfg/mode.yaml \
  configs/modes/all-weapons-dm/mode.yaml \
  configs/modes/retake/mode.yaml
```

Expected now:

```text
cs2rcon/simpleadmin/gamemodemanager/quakesounds/deathmatch: planned
discordstatus/inventorysimulator: disabled
```

## Current policy

Minimal plugin runtime comes first:

```text
MetaMod
CounterStrikeSharp
one admin/RCON plugin candidate only
```

Only after connect/disconnect stability:

```text
GameModeManager / RTV
QuakeSounds
Deathmatch plugin
Retake plugin if Valve retake is insufficient
skins/ranks/DiscordStatus much later or not at all by default
```

## Why this exists

The old server had many global plugins and player-connect hooks. The new platform keeps plugin choices explicit, pinned, and mode-scoped before any binary is loaded.