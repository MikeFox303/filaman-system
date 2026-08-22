from unittest.mock import AsyncMock, patch

import pytest

from app.services.managed_plugin_service import (
    BAMBUDDY_PLUGIN_ASSET,
    BAMBUDDY_PLUGIN_KEY,
    BAMBUDDY_PLUGIN_SHA256,
    BAMBUDDY_PLUGIN_VERSION,
    _read_verified_asset,
    _version_tuple,
    ensure_managed_plugins,
)


def test_version_tuple():
    assert _version_tuple("1.3.10") == (1, 3, 10)
    assert _version_tuple("1.3.10-rc1") == (1, 3, 10)
    assert _version_tuple("broken") is None


def test_x2d_managed_plugin_release_pin_shape():
    assert _version_tuple(BAMBUDDY_PLUGIN_VERSION) is not None
    assert BAMBUDDY_PLUGIN_ASSET.name == f"bambuddy-{BAMBUDDY_PLUGIN_VERSION}.zip"
    assert len(BAMBUDDY_PLUGIN_SHA256) == 64
    assert all(c in "0123456789abcdef" for c in BAMBUDDY_PLUGIN_SHA256)


def test_checksum_mismatch_fails_closed(tmp_path):
    asset = tmp_path / "plugin.zip"
    asset.write_bytes(b"wrong")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        _read_verified_asset(asset, "0" * 64)


@pytest.mark.asyncio
async def test_exact_version_is_noop_when_files_exist(db_session, tmp_path):
    target = tmp_path / BAMBUDDY_PLUGIN_KEY
    target.mkdir()
    (target / "plugin.json").write_text("{}")
    existing = type("Plugin", (), {"version": BAMBUDDY_PLUGIN_VERSION})()
    with patch(
        "app.services.managed_plugin_service.plugin_service.PLUGINS_DIR", tmp_path
    ), patch(
        "app.services.managed_plugin_service.PluginInstallService.get_plugin",
        AsyncMock(return_value=existing),
    ), patch(
        "app.services.managed_plugin_service.PluginInstallService.install_from_zip",
        AsyncMock(),
    ) as install:
        await ensure_managed_plugins(db_session)
        install.assert_not_awaited()


@pytest.mark.asyncio
async def test_newer_version_is_not_downgraded(db_session, tmp_path):
    existing = type("Plugin", (), {"version": "9.0.0"})()
    with patch(
        "app.services.managed_plugin_service.plugin_service.PLUGINS_DIR", tmp_path
    ), patch(
        "app.services.managed_plugin_service.PluginInstallService.get_plugin",
        AsyncMock(return_value=existing),
    ), patch(
        "app.services.managed_plugin_service.PluginInstallService.install_from_zip",
        AsyncMock(),
    ) as install:
        await ensure_managed_plugins(db_session)
        install.assert_not_awaited()
