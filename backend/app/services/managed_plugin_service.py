"""Install release-managed plugins before printer drivers start."""

import hashlib
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import plugin_service
from app.services.plugin_service import PluginInstallService

logger = logging.getLogger(__name__)

BAMBUDDY_PLUGIN_KEY = "bambuddy"
BAMBUDDY_PLUGIN_VERSION = "1.3.10"
BAMBUDDY_PLUGIN_SHA256 = "5aabadc617c85cbe0d4bc0c5c13fe88820ee5cee5174a3455f4e6e3489c4c227"
BAMBUDDY_PLUGIN_ASSET = Path("/app/managed_plugins/bambuddy-1.3.10.zip")


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    try:
        core = value.split("-", 1)[0]
        parts = tuple(int(part) for part in core.split("."))
    except (AttributeError, TypeError, ValueError):
        return None
    return parts if len(parts) == 3 else None


def _read_verified_asset(path: Path, expected_sha256: str) -> bytes:
    data = path.read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected_sha256:
        raise RuntimeError(
            f"Managed plugin checksum mismatch for {path.name}: expected {expected_sha256}, got {actual}"
        )
    return data


async def ensure_managed_plugins(db: AsyncSession) -> None:
    service = PluginInstallService(db)
    existing = await service.get_plugin(BAMBUDDY_PLUGIN_KEY)
    desired = _version_tuple(BAMBUDDY_PLUGIN_VERSION)
    current = _version_tuple(existing.version) if existing else None
    target_dir = plugin_service.PLUGINS_DIR / BAMBUDDY_PLUGIN_KEY

    if existing and current and desired and current > desired:
        logger.warning(
            "Managed Bambuddy plugin v%s is older than installed v%s; refusing downgrade",
            BAMBUDDY_PLUGIN_VERSION,
            existing.version,
        )
        return

    if (
        existing
        and existing.version == BAMBUDDY_PLUGIN_VERSION
        and target_dir.is_dir()
        and (target_dir / "plugin.json").is_file()
    ):
        logger.info(
            "Managed Bambuddy plugin v%s already installed", BAMBUDDY_PLUGIN_VERSION
        )
        return

    data = _read_verified_asset(BAMBUDDY_PLUGIN_ASSET, BAMBUDDY_PLUGIN_SHA256)
    plugin, is_upgrade = await service.install_from_zip(
        data, installed_by=None, stop_callback=None
    )
    if plugin.plugin_key != BAMBUDDY_PLUGIN_KEY or plugin.version != BAMBUDDY_PLUGIN_VERSION:
        raise RuntimeError(
            f"Managed Bambuddy plugin identity mismatch: {plugin.plugin_key} v{plugin.version}"
        )
    logger.info(
        "Managed Bambuddy plugin %s to v%s",
        "upgraded" if is_upgrade else "installed",
        BAMBUDDY_PLUGIN_VERSION,
    )
