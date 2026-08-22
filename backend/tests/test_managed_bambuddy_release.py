import hashlib
import json
from pathlib import Path
import zipfile

from app.services import managed_plugin_service as managed


def test_managed_bambuddy_asset_matches_pin_and_provenance():
    repo_backend = Path(__file__).resolve().parents[1]
    asset = repo_backend / "managed_plugins" / f"bambuddy-{managed.BAMBUDDY_PLUGIN_VERSION}.zip"
    provenance_path = repo_backend / "managed_plugins" / "bambuddy-release.json"

    assert asset.is_file()
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    assert digest == managed.BAMBUDDY_PLUGIN_SHA256

    with zipfile.ZipFile(asset) as zf:
        manifest = json.loads(zf.read("bambuddy/plugin.json"))
    assert manifest["plugin_key"] == "bambuddy"
    assert manifest["version"] == managed.BAMBUDDY_PLUGIN_VERSION

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["repository"] == "MikeFox303/filaman-bambuddy-plugin"
    assert len(provenance["source_sha"]) == 40
    assert all(c in "0123456789abcdef" for c in provenance["source_sha"])
    assert provenance["version"] == managed.BAMBUDDY_PLUGIN_VERSION
    assert provenance["sha256"] == digest


def test_managed_bambuddy_ships_one_release_asset():
    repo_backend = Path(__file__).resolve().parents[1]
    assets = sorted((repo_backend / "managed_plugins").glob("bambuddy-*.zip"))
    expected = repo_backend / "managed_plugins" / f"bambuddy-{managed.BAMBUDDY_PLUGIN_VERSION}.zip"
    assert assets == [expected]
