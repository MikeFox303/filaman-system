import io
import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.plugin_service import PluginInstallError, PluginInstallService


def _make_zip(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


VALID_MANIFEST = {
    "plugin_key": "test_plugin",
    "name": "Test Plugin",
    "version": "1.0.0",
    "description": "A test plugin",
    "author": "Test Author",
    "plugin_type": "driver",
    "driver_key": "test_plugin",
}

VALID_DRIVER_PY = """
from app.plugins.base import BaseDriver

class Driver(BaseDriver):
    driver_key = "test_plugin"

    async def start(self):
        pass

    async def stop(self):
        pass
"""

VALID_INIT_PY = ""


def _make_valid_plugin_zip() -> bytes:
    return _make_zip(
        {
            "plugin.json": json.dumps(VALID_MANIFEST),
            "driver.py": VALID_DRIVER_PY,
            "__init__.py": VALID_INIT_PY,
        }
    )


class TestZipValidation:
    @pytest.mark.asyncio
    async def test_validate_zip_valid(self, db_session):
        service = PluginInstallService(db_session)

        service._validate_zip(_make_valid_plugin_zip())

    @pytest.mark.asyncio
    async def test_validate_zip_invalid(self, db_session):
        service = PluginInstallService(db_session)

        with pytest.raises(PluginInstallError) as excinfo:
            service._validate_zip(b"not-a-zip")

        assert excinfo.value.code == "invalid_zip"

    @pytest.mark.asyncio
    async def test_validate_zip_too_large(self, db_session):
        service = PluginInstallService(db_session)
        oversized = b"0" * (10 * 1024 * 1024 + 1)

        with pytest.raises(PluginInstallError) as excinfo:
            await service.install_from_zip(oversized)

        assert excinfo.value.code == "zip_too_large"


class TestManifestValidation:
    @pytest.mark.asyncio
    async def test_validate_manifest_valid(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")

            manifest = service._validate_manifest(plugin_dir)

        assert manifest["plugin_key"] == "test_plugin"

    @pytest.mark.asyncio
    async def test_validate_manifest_missing_field(self, db_session):
        service = PluginInstallService(db_session)
        manifest = {**VALID_MANIFEST}
        manifest.pop("name")
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_manifest(plugin_dir)

        assert excinfo.value.code == "missing_field"

    @pytest.mark.asyncio
    async def test_validate_manifest_invalid_key(self, db_session):
        service = PluginInstallService(db_session)
        manifest = {**VALID_MANIFEST, "plugin_key": "INVALID!"}
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_manifest(plugin_dir)

        assert excinfo.value.code == "invalid_key"

    @pytest.mark.asyncio
    async def test_validate_manifest_invalid_version(self, db_session):
        service = PluginInstallService(db_session)
        manifest = {**VALID_MANIFEST, "version": "abc"}
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_manifest(plugin_dir)

        assert excinfo.value.code == "invalid_version"

    @pytest.mark.asyncio
    async def test_validate_manifest_reserved_key(self, db_session):
        service = PluginInstallService(db_session)
        manifest = {**VALID_MANIFEST, "plugin_key": "dummy", "driver_key": "dummy"}
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_manifest(plugin_dir)

        assert excinfo.value.code == "reserved_key"

    @pytest.mark.asyncio
    async def test_validate_manifest_driver_key_mismatch(self, db_session):
        service = PluginInstallService(db_session)
        manifest = {**VALID_MANIFEST, "driver_key": "other"}
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_manifest(plugin_dir)

        assert excinfo.value.code == "key_mismatch"


class TestStructureValidation:
    @pytest.mark.asyncio
    async def test_validate_structure_valid(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
            (plugin_dir / "driver.py").write_text(VALID_DRIVER_PY, encoding="utf-8")

            service._validate_structure(plugin_dir, "driver")

    @pytest.mark.asyncio
    async def test_validate_structure_missing_driver(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_structure(plugin_dir, "driver")

        assert excinfo.value.code == "missing_file"


class TestSecurityValidation:
    @pytest.mark.asyncio
    async def test_validate_security_forbidden_extension(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
            (plugin_dir / "driver.py").write_text(VALID_DRIVER_PY, encoding="utf-8")
            (plugin_dir / "bad.exe").write_text("boom", encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_security(plugin_dir)

        assert excinfo.value.code == "forbidden_extension"

    @pytest.mark.asyncio
    async def test_validate_security_hidden_file(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "plugin.json").write_text(json.dumps(VALID_MANIFEST), encoding="utf-8")
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
            (plugin_dir / "driver.py").write_text(VALID_DRIVER_PY, encoding="utf-8")
            (plugin_dir / ".hidden.txt").write_text("nope", encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_security(plugin_dir)

        assert excinfo.value.code == "hidden_file"


class TestDriverValidation:
    @pytest.mark.asyncio
    async def test_validate_driver_valid(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "driver.py").write_text(VALID_DRIVER_PY, encoding="utf-8")

            service._validate_driver(plugin_dir, VALID_MANIFEST)

    @pytest.mark.asyncio
    async def test_validate_driver_no_class(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "driver.py").write_text("class NotDriver: pass", encoding="utf-8")

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_driver(plugin_dir, VALID_MANIFEST)

        assert excinfo.value.code == "no_driver_class"

    @pytest.mark.asyncio
    async def test_validate_driver_no_base(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)
            (plugin_dir / "driver.py").write_text(
                "class Driver: driver_key = 'test_plugin'", encoding="utf-8"
            )

            with pytest.raises(PluginInstallError) as excinfo:
                service._validate_driver(plugin_dir, VALID_MANIFEST)

        assert excinfo.value.code == "invalid_inheritance"


class TestPluginDBOperations:
    @pytest.mark.asyncio
    async def test_register_builtin(self, db_session):
        service = PluginInstallService(db_session)

        plugin = await service.register_builtin(
            plugin_key="builtin_test",
            name="Builtin",
            version="1.0.0",
            description="Builtin plugin",
            author="System",
            plugin_type="driver",
            page_url="https://example.com",
            homepage="https://example.com/home",
        )

        assert plugin.plugin_key == "builtin_test"
        assert plugin.page_url == "https://example.com"
        assert plugin.homepage == "https://example.com/home"
        assert plugin.installed_by is None

    @pytest.mark.asyncio
    async def test_register_builtin_update(self, db_session):
        service = PluginInstallService(db_session)

        await service.register_builtin(
            plugin_key="builtin_test",
            name="Builtin",
            version="1.0.0",
            description="Builtin plugin",
            author="System",
            plugin_type="driver",
        )
        updated = await service.register_builtin(
            plugin_key="builtin_test",
            name="Builtin",
            version="1.0.1",
            description="Builtin plugin v2",
            author="System",
            plugin_type="driver",
        )

        assert updated.version == "1.0.1"
        assert updated.description == "Builtin plugin v2"

    @pytest.mark.asyncio
    async def test_list_installed(self, db_session):
        service = PluginInstallService(db_session)

        await service.register_builtin(
            plugin_key="alpha",
            name="Alpha",
            version="1.0.0",
            description="Alpha",
            author="System",
            plugin_type="driver",
        )
        await service.register_builtin(
            plugin_key="beta",
            name="Beta",
            version="1.0.0",
            description="Beta",
            author="System",
            plugin_type="driver",
        )

        plugins = await service.list_installed()

        names = [plugin.name for plugin in plugins]

        assert names == sorted(names)
        assert names.count("Alpha") == 1
        assert names.count("Beta") == 1

    @pytest.mark.asyncio
    async def test_get_plugin(self, db_session):
        service = PluginInstallService(db_session)

        await service.register_builtin(
            plugin_key="alpha",
            name="Alpha",
            version="1.0.0",
            description="Alpha",
            author="System",
            plugin_type="driver",
        )

        plugin = await service.get_plugin("alpha")

        assert plugin is not None
        assert plugin.plugin_key == "alpha"

    @pytest.mark.asyncio
    async def test_get_plugin_not_found(self, db_session):
        service = PluginInstallService(db_session)

        plugin = await service.get_plugin("missing")

        assert plugin is None

    @pytest.mark.asyncio
    async def test_set_active_deactivate(self, db_session):
        service = PluginInstallService(db_session)

        await service.register_builtin(
            plugin_key="alpha",
            name="Alpha",
            version="1.0.0",
            description="Alpha",
            author="System",
            plugin_type="driver",
        )

        plugin = await service.set_active("alpha", False)

        assert plugin.is_active is False

    @pytest.mark.asyncio
    async def test_uninstall_not_found(self, db_session):
        service = PluginInstallService(db_session)

        with pytest.raises(PluginInstallError) as excinfo:
            await service.uninstall("missing")

        assert excinfo.value.code == "not_found"


class TestInstallFromZip:
    @pytest.mark.asyncio
    async def test_install_valid_plugin(self, db_session):
        service = PluginInstallService(db_session)
        zip_data = _make_valid_plugin_zip()

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.services.plugin_service.PLUGINS_DIR", Path(tmpdir)):
                plugin, is_upgrade = await service.install_from_zip(zip_data)

        assert is_upgrade is False
        assert plugin.plugin_key == "test_plugin"


class TestAtomicPluginUpgrade:
    @staticmethod
    def _versioned_zip(version: str, *, dependencies=None, marker: str = "v1") -> bytes:
        manifest = {**VALID_MANIFEST, "version": version}
        if dependencies is not None:
            manifest["dependencies"] = dependencies
        return _make_zip({
            "plugin.json": json.dumps(manifest),
            "driver.py": VALID_DRIVER_PY + f"\nMARKER = {marker!r}\n",
            "__init__.py": VALID_INIT_PY,
        })

    @pytest.mark.asyncio
    async def test_dependency_failure_preserves_old_plugin_and_db_version(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir)
            with patch("app.services.plugin_service.PLUGINS_DIR", plugins_dir):
                await service.install_from_zip(
                    self._versioned_zip("1.0.0", marker="old"), installed_by=1
                )
                old_manifest = (plugins_dir / "test_plugin" / "plugin.json").read_text()
                stop_callback = AsyncMock()
                service._install_dependencies = AsyncMock(
                    side_effect=PluginInstallError(
                        "dependency failed", "dependency_install_failed"
                    )
                )
                with pytest.raises(PluginInstallError) as excinfo:
                    await service.install_from_zip(
                        self._versioned_zip(
                            "2.0.0",
                            dependencies=["definitely-not-installed"],
                            marker="new",
                        ),
                        installed_by=1,
                        stop_callback=stop_callback,
                    )
                assert excinfo.value.code == "dependency_install_failed"
                stop_callback.assert_not_awaited()
                assert (plugins_dir / "test_plugin" / "plugin.json").read_text() == old_manifest
                installed = await service.get_plugin("test_plugin")
                assert installed is not None and installed.version == "1.0.0"
                assert not list(plugins_dir.glob(".test_plugin.backup-*"))
                assert not list(plugins_dir.glob(".test_plugin.staging-*"))

    @pytest.mark.asyncio
    async def test_db_commit_failure_restores_old_plugin_directory(self, db_session):
        service = PluginInstallService(db_session)
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir)
            with patch("app.services.plugin_service.PLUGINS_DIR", plugins_dir):
                await service.install_from_zip(
                    self._versioned_zip("1.0.0", marker="old"), installed_by=1
                )
                old_driver = (plugins_dir / "test_plugin" / "driver.py").read_text()
                real_commit = db_session.commit
                db_session.commit = AsyncMock(side_effect=RuntimeError("db commit failed"))
                try:
                    with pytest.raises(RuntimeError, match="db commit failed"):
                        await service.install_from_zip(
                            self._versioned_zip("2.0.0", marker="new"), installed_by=1
                        )
                finally:
                    db_session.commit = real_commit
                assert (plugins_dir / "test_plugin" / "driver.py").read_text() == old_driver
                installed = await service.get_plugin("test_plugin")
                assert installed is not None and installed.version == "1.0.0"
                assert not list(plugins_dir.glob(".test_plugin.backup-*"))
                assert not list(plugins_dir.glob(".test_plugin.staging-*"))

    @pytest.mark.asyncio
    async def test_successful_upgrade_replaces_files_and_cleans_rollback_dirs(self, db_session):
        service = PluginInstallService(db_session)
        stop_callback = AsyncMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            plugins_dir = Path(tmpdir)
            with patch("app.services.plugin_service.PLUGINS_DIR", plugins_dir):
                await service.install_from_zip(
                    self._versioned_zip("1.0.0", marker="old"), installed_by=1
                )
                plugin, is_upgrade = await service.install_from_zip(
                    self._versioned_zip("2.0.0", marker="new"),
                    installed_by=1,
                    stop_callback=stop_callback,
                )
                assert is_upgrade is True and plugin.version == "2.0.0"
                assert "MARKER = 'new'" in (
                    plugins_dir / "test_plugin" / "driver.py"
                ).read_text()
                stop_callback.assert_awaited_once_with("test_plugin")
                assert not list(plugins_dir.glob(".test_plugin.backup-*"))
                assert not list(plugins_dir.glob(".test_plugin.staging-*"))
