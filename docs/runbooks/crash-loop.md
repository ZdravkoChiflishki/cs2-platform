# Crash Loop Runbook

## First checks

```bash
kubectl -n cs2-servers get pod -l zizo.gg/server-id=staging-mirage-multicfg-01 -o wide
kubectl -n cs2-servers describe pod -l zizo.gg/server-id=staging-mirage-multicfg-01
kubectl -n cs2-servers logs deploy/staging-mirage-multicfg-01 --tail=300
kubectl -n cs2-servers logs deploy/staging-mirage-multicfg-01 --previous --tail=300
```

Look for:

```text
Segmentation fault
FATAL ERROR
Failed to initialize Steamworks SDK
libserver.so
libv8.so
steamclient.so
CounterStrikeSharp
ClientPutInServer
NETWORK_DISCONNECT_LOOPSHUTDOWN
```

## Known startup fixes in this platform

The Python runtime must:

1. bootstrap SteamCMD so `/opt/steamcmd/linux64/steamclient.so` exists
2. copy SteamCMD SDK libraries to `$HOME/.steam/sdk64` and `$HOME/.steam/sdk32`
3. copy CS2 `game/bin/linuxsteamrt64/*.so` into `game/csgo/bin/linuxsteamrt64/`

If logs show missing `steamclient.so`, check `steamcmd_bootstrapped` and `steamclient_libraries_prepared` JSON events.

If logs show missing `libv8.so` or failed `libserver.so`, check `server_libraries_prepared`.

## Steam update problems

Inspect the appmanifest:

```bash
kubectl -n cs2-servers exec deploy/staging-mirage-multicfg-01 -- \
  bash -lc 'grep -E "buildid|TargetBuildID|StateFlags|UpdateResult|BytesToDownload|BytesDownloaded" /home/steam/cs2/steamapps/appmanifest_730.acf'
```

Rules:

- `buildid == TargetBuildID` and non-zero: ready
- `buildid=0` with non-zero `TargetBuildID`: likely active download/verify, do not delete partial state
- non-zero `buildid != TargetBuildID`: stale partial update; runtime may repair by removing manifest/temp state

## Player-connect crashes

If the crash happens after `ClientPutInServer`, suspect plugins or mode logic first.

Isolation order:

1. verify no banned/global plugin stack is loaded
2. disable bots
3. test one human connect/disconnect
4. only then add plugins back one by one

## Rollback

Rollback the GitOps image digest or mode/env commit. Do not delete the PVC unless the Steam install is proven corrupt.