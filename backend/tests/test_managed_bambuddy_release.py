import hashlib
import json
from pathlib import Path
import zipfile

from app.services import managed_plugin_service as managed


def test_managed_bambuddy_1_3_10_asset_matches_pin():
    repo_backend = Path(__file__).resolve().parents[1]
    asset = repo_backend / "managed_plugins" / "bambuddy-1.3.10.zip"
    assert managed.BAMBUDDY_PLUGIN_VERSION == "1.3.10"
    assert asset.is_file()
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == managed.BAMBUDDY_PLUGIN_SHA256
    with zipfile.ZipFile(asset) as zf:
        manifest = json.loads(zf.read("bambuddy/plugin.json"))
    assert manifest["plugin_key"] == "bambuddy"
    assert manifest["version"] == "1.3.10"


def test_managed_bambuddy_does_not_ship_old_1_3_9_asset():
    repo_backend = Path(__file__).resolve().parents[1]
    assert not (repo_backend / "managed_plugins" / "bambuddy-1.3.9.zip").exists()
