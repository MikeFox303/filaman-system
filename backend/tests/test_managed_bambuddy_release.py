import hashlib
import json
from pathlib import Path
import zipfile

from app.services import managed_plugin_service as managed


def test_managed_bambuddy_asset_matches_pin():
    repo_backend = Path(__file__).resolve().parents[1]
    asset = repo_backend / "managed_plugins" / f"bambuddy-{managed.BAMBUDDY_PLUGIN_VERSION}.zip"
    assert asset.is_file()
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == managed.BAMBUDDY_PLUGIN_SHA256
    with zipfile.ZipFile(asset) as zf:
        manifest = json.loads(zf.read("bambuddy/plugin.json"))
    assert manifest["plugin_key"] == "bambuddy"
    assert manifest["version"] == managed.BAMBUDDY_PLUGIN_VERSION


def test_managed_bambuddy_ships_one_release_asset():
    repo_backend = Path(__file__).resolve().parents[1]
    assets = sorted((repo_backend / "managed_plugins").glob("bambuddy-*.zip"))
    expected = repo_backend / "managed_plugins" / f"bambuddy-{managed.BAMBUDDY_PLUGIN_VERSION}.zip"
    assert assets == [expected]
