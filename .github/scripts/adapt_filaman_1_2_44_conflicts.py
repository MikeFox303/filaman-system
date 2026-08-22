from __future__ import annotations

import json
import subprocess
from pathlib import Path

BASE = "ebc0bcc83e34665bc699a0a259489f7d21d03a80"
LOCAL = "c463135e3eabc9f17e809f74d692b78bfb13dc56"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def git_json(ref: str, path: str) -> dict:
    return json.loads(subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True))


def leaf_changes(base: dict, local: dict, prefix: tuple[str, ...] = ()):
    changes: list[tuple[str, tuple[str, ...], object | None]] = []
    for key in sorted(set(base) | set(local)):
        path = prefix + (key,)
        if key not in local:
            changes.append(("delete", path, None))
        elif key not in base:
            changes.append(("set", path, local[key]))
        elif isinstance(base[key], dict) and isinstance(local[key], dict):
            changes.extend(leaf_changes(base[key], local[key], path))
        elif base[key] != local[key]:
            changes.append(("set", path, local[key]))
    return changes


def apply_leaf(target: dict, operation: str, path: tuple[str, ...], value: object | None) -> None:
    node = target
    for key in path[:-1]:
        node = node.setdefault(key, {})
    if operation == "delete":
        node.pop(path[-1], None)
    else:
        node[path[-1]] = value


def resolve_printers() -> None:
    path = Path("backend/app/api/v1/printers.py")
    run("git", "checkout", "--ours", "--", str(path))
    text = path.read_text()
    if "primary_proxy_invalid_response" not in text:
        anchor = """            return payload\n\n    raise HTTPException(\n"""
        replacement = """            if payload is None:\n                # A successful HTTP status can still carry an empty/non-JSON body.\n                # Preserve the local loopback proxy hardening while adopting the\n                # structured upstream 1.2.44 failure contract.\n                raise HTTPException(\n                    status_code=status.HTTP_502_BAD_GATEWAY,\n                    detail={\n                        \"code\": \"primary_proxy_invalid_response\",\n                        \"message\": \"Primary worker returned an invalid response\",\n                    },\n                )\n\n            return payload\n\n    raise HTTPException(\n"""
        if anchor not in text:
            raise SystemExit("printers.py: safe return-payload anchor not found")
        text = text.replace(anchor, replacement, 1)
        path.write_text(text)
    run("git", "add", str(path))


def resolve_printer_tests() -> None:
    path = Path("backend/tests/test_printers.py")
    run("git", "checkout", "--ours", "--", str(path))
    text = path.read_text()
    marker = "test_driver_action_invalid_proxy_response_returns_structured_502"
    if marker not in text:
        block = r'''

class _InvalidJsonProxyResponse:
    """Mimics an httpx response whose body cannot be decoded as JSON."""

    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.text = ""

    def json(self):
        raise ValueError("not valid JSON")


class _InvalidJsonProxyClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def request(self, *args, **kwargs):
        return _InvalidJsonProxyResponse()


class TestDriverInvalidProxyResponse:
    """Upstream 1.2.44 regression coverage for invalid primary responses."""

    @pytest.mark.asyncio
    async def test_driver_action_invalid_proxy_response_returns_structured_502(
        self, auth_client, db_session
    ):
        client, csrf_token = auth_client
        printer = await _create_printer(db_session)

        with (
            patch("app.api.v1.printers._is_primary_worker", return_value=False),
            patch("app.api.v1.printers.httpx.AsyncClient", _InvalidJsonProxyClient),
        ):
            response = await client.post(
                f"/api/v1/printers/{printer.id}/driver/action",
                json={"action": "send_filament_to_tray", "params": {}},
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "primary_proxy_invalid_response"

    @pytest.mark.asyncio
    async def test_start_driver_invalid_proxy_response_returns_structured_502(
        self, auth_client, db_session
    ):
        client, csrf_token = auth_client
        printer = await _create_printer(db_session)

        with (
            patch("app.api.v1.printers._is_primary_worker", return_value=False),
            patch("app.api.v1.printers.httpx.AsyncClient", _InvalidJsonProxyClient),
        ):
            response = await client.post(
                f"/api/v1/printers/{printer.id}/driver/start",
                headers={"X-CSRF-Token": csrf_token},
            )

        assert response.status_code == 502
        assert response.json()["detail"]["code"] == "primary_proxy_invalid_response"
'''
        path.write_text(text.rstrip() + block + "\n")
    run("git", "add", str(path))


def resolve_package() -> None:
    path = Path("frontend/package.json")
    run("git", "checkout", "--theirs", "--", str(path))
    data = json.loads(path.read_text())
    data.setdefault("scripts", {})["check:i18n"] = "node scripts/check-i18n.mjs"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    run("git", "add", str(path))


def resolve_en_de() -> None:
    files = ("frontend/src/i18n/de.json", "frontend/src/i18n/en.json")
    run("git", "checkout", "--theirs", "--", *files)
    for path_string in files:
        path = Path(path_string)
        changes = leaf_changes(git_json(BASE, path_string), git_json(LOCAL, path_string))
        if len(changes) != 4:
            raise SystemExit(f"{path_string}: expected 4 reviewed local leaf changes, got {changes}")
        target = json.loads(path.read_text())
        for change in changes:
            apply_leaf(target, *change)
        path.write_text(json.dumps(target, ensure_ascii=False, indent=2) + "\n")
        run("git", "add", path_string)


def resolve_spoolman_page() -> None:
    path = Path("frontend/src/pages/admin/system/spoolman-import.astro")
    run("git", "checkout", "--theirs", "--", str(path))
    text = path.read_text()
    old = 'id="btn-repair-transparency" class="fm-btn fm-btn-outline hidden"'
    new = old + ' data-i18n="spoolman.repairTransparency"'
    if new not in text:
        if old not in text:
            raise SystemExit("spoolman-import.astro: repair button anchor missing")
        text = text.replace(old, new, 1)
        path.write_text(text)
    run("git", "add", str(path))


def main() -> None:
    resolve_printers()
    resolve_printer_tests()
    resolve_package()
    resolve_en_de()
    resolve_spoolman_page()


if __name__ == "__main__":
    main()
