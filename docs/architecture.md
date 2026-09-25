# Architecture

The platform separates CS2 server operation into four layers:

1. **Image** — operating system dependencies, SteamCMD, Python runtime, and vetted plugin binaries.
2. **Runtime app** — `cs2_server`, a Python lifecycle manager that replaces the legacy shell startup script.
3. **Config profiles** — base config plus one mode profile plus optional server-specific override.
4. **Kubernetes server instances** — one Deployment/Service/PVC per public CS2 server.

## Non-goals for MVP

- No ranks/skins economy.
- No Discord status plugin in the game process.
- No global GameCMS integration.
- No old custom-files NFS overlay.
- No multi-mode megaserver with every plugin loaded.

## Server scaling model

Scale horizontally by creating more server instances:

```text
eu-mirage-multicfg-01  -> port 26001
eu-dust2-allweapons-01 -> port 26002
eu-ancient-retake-01   -> port 26003
```

Each pod owns one CS2 process and one service port.
