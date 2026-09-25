# Server Modes

## Multi-CFG

Status: live staging on `192.168.0.8:26001`.

Purpose: clean practice/casual baseline with no legacy plugin stack.

Key files:

- `configs/modes/multicfg/mode.yaml`
- `configs/modes/multicfg/cfg/multicfg.cfg`
- `configs/modes/multicfg/cfg/practice.cfg`
- `configs/modes/multicfg/cfg/live.cfg`
- `configs/modes/multicfg/cfg/pistol.cfg`
- `configs/modes/multicfg/cfg/rifle.cfg`

## All Weapons DM

Status: config profile implemented, not deployed as a second server yet.

Purpose: plugin-free Valve Deathmatch baseline for later testing before adding any DM plugin.

Key files:

- `configs/modes/all-weapons-dm/mode.yaml`
- `configs/modes/all-weapons-dm/cfg/all-weapons-dm.cfg`

Launch settings for this mode should use:

```text
GAME_TYPE=1
GAME_MODE=2
MAP_GROUP=mg_active
EXEC=all-weapons-dm.cfg
MAXPLAYERS=24
```

Policy:

- no Ranks
- no skins/inventory
- no DiscordStatus
- no legacy Deathmatch mega-plugin stack
- bots remain disabled by default until spawn/connect stability is proven
