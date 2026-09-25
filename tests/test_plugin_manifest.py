import pytest
import yaml

from cs2_tools.plugin_manifest import PluginCatalog, PluginManifestError


def test_plugin_catalog_loads_locked_plugin_metadata(tmp_path):
    manifest = tmp_path / "plugins.yaml"
    manifest.write_text(yaml.safe_dump({
        "plugins": {
            "cs2rcon": {
                "displayName": "CS2Rcon",
                "phase": "planned",
                "loader": "counterstrikesharp",
                "enabledByDefault": False,
                "source": "https://example.invalid/cs2rcon",
                "version": "0.0.0",
                "sha256": "0" * 64,
                "entrypoint": "addons/counterstrikesharp/plugins/CS2Rcon/CS2Rcon.dll",
            }
        }
    }))

    catalog = PluginCatalog.load(manifest)
    plugin = catalog.require("cs2rcon")

    assert plugin.name == "cs2rcon"
    assert plugin.loader == "counterstrikesharp"
    assert plugin.phase == "planned"
    assert plugin.enabled_by_default is False


def test_plugin_catalog_rejects_unknown_phase(tmp_path):
    manifest = tmp_path / "plugins.yaml"
    manifest.write_text(yaml.safe_dump({
        "plugins": {
            "bad": {
                "displayName": "Bad",
                "phase": "random",
                "loader": "counterstrikesharp",
                "enabledByDefault": False,
                "source": "https://example.invalid/bad",
                "version": "0.0.0",
                "sha256": "1" * 64,
                "entrypoint": "bad.dll",
            }
        }
    }))

    with pytest.raises(PluginManifestError, match="phase"):
        PluginCatalog.load(manifest)


def test_plugin_catalog_rejects_invalid_hash(tmp_path):
    manifest = tmp_path / "plugins.yaml"
    manifest.write_text(yaml.safe_dump({
        "plugins": {
            "bad": {
                "displayName": "Bad",
                "phase": "planned",
                "loader": "counterstrikesharp",
                "enabledByDefault": False,
                "source": "https://example.invalid/bad",
                "version": "0.0.0",
                "sha256": "not-a-hash",
                "entrypoint": "bad.dll",
            }
        }
    }))

    with pytest.raises(PluginManifestError, match="sha256"):
        PluginCatalog.load(manifest)


def test_repository_plugin_manifest_only_enables_cs2rcon():
    catalog = PluginCatalog.load()

    enabled = [plugin.name for plugin in catalog.plugins.values() if plugin.phase == "enabled"]
    defaults = [plugin.name for plugin in catalog.plugins.values() if plugin.enabled_by_default]

    assert enabled == ["cs2rcon", "simpleadmin", "menumanager", "playersettings", "anybaselib"]
    assert defaults == ["cs2rcon", "simpleadmin", "menumanager", "playersettings", "anybaselib"]
    assert catalog.plugins["cs2rcon"].version == "1.2.0"
    assert catalog.plugins["cs2rcon"].sha256 == "311425a06d7a4af980c6dfab188b8b60a598c2edae1fa33828bcb25b47b85639"
    assert catalog.plugins["simpleadmin"].version == "1.8.2b"
    assert catalog.plugins["simpleadmin"].sha256 == "3879f74a000582c407f9795be62f718cb1d512e58ba9c81accf12d691696c201"
