from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_makes_steamcmd_owned_by_runtime_user():
    dockerfile = (ROOT / "image" / "Dockerfile").read_text()

    assert "useradd --create-home --home-dir /home/steam --shell /bin/bash steam" in dockerfile
    assert "chown -R steam:steam /opt/steamcmd" in dockerfile


def test_runtime_validation_runs_steamcmd_as_steam_user():
    script = (ROOT / "image" / "scripts" / "validate-runtime.sh").read_text()

    assert "su -s /bin/sh steam -c '/opt/steamcmd/steamcmd.sh +quit >/dev/null'" in script
