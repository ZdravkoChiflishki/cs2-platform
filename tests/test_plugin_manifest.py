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


def test_repository_plugin_manifest_has_no_runtime_enabled_plugins():
    catalog = PluginCatalog.load()

    assert "cs2rcon" in catalog.plugins
    assert all(plugin.phase in {"planned", "disabled"} for plugin in catalog.plugins.values())
    assert all(not plugin.enabled_by_default for plugin in catalog.plugins.values())
