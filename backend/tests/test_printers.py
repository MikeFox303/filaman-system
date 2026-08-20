import httpx
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import event
from sqlalchemy.orm.attributes import set_committed_value
from unittest.mock import AsyncMock, patch

from app.api.v1 import printers as printers_api
from app.models import Location, Printer, PrinterSlot


@pytest.fixture(autouse=True)
def mock_plugin_manager():
    with patch("app.api.v1.printers.plugin_manager") as mock_pm:
        mock_pm.start_printer = AsyncMock(return_value=True)
        mock_pm.stop_printer = AsyncMock(return_value=None)
        mock_pm.reconnect_all = AsyncMock(return_value={})
        mock_pm.drivers = {}
        yield mock_pm


@pytest.fixture(autouse=True)
def prevent_assignment_lazy_load(db_session):
    def _set_assignment(session, instance):
        if isinstance(instance, PrinterSlot):
            set_committed_value(instance, "assignment", None)

    event.listen(db_session.sync_session, "loaded_as_persistent", _set_assignment)
    yield
    event.remove(db_session.sync_session, "loaded_as_persistent", _set_assignment)


async def _create_printer(db_session, name: str = "Test Printer", driver_key: str = "bambu_mqtt", **kwargs) -> Printer:
    printer = Printer(name=name, driver_key=driver_key, **kwargs)
    db_session.add(printer)
    await db_session.commit()
    await db_session.refresh(printer)
    return printer


async def _create_slot(db_session, printer_id: int, slot_no: int = 1, **kwargs) -> PrinterSlot:
    slot = PrinterSlot(printer_id=printer_id, slot_no=slot_no, **kwargs)
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)
    set_committed_value(slot, "assignment", None)
    return slot


async def _create_location(db_session, name: str = "Shelf A") -> Location:
    location = Location(name=name)
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    return location


def _proxy_request(
    url: str = "http://192.168.0.100:8000/api/v1/printers/3/driver/action?unexpected=1",
    headers: dict[str, str] | None = None,
) -> Request:
    parsed = httpx.URL(url)
    request_headers = {"host": parsed.netloc.decode()}
    request_headers.update(headers or {})
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": parsed.scheme,
            "path": parsed.path,
            "raw_path": parsed.raw_path,
            "query_string": parsed.query,
            "headers": [
                (key.encode("latin-1"), value.encode("latin-1"))
                for key, value in request_headers.items()
            ],
            "server": (parsed.host, parsed.port),
            "client": ("192.168.0.50", 50000),
        }
    )


def _mock_async_client(*responses: httpx.Response) -> AsyncMock:
    client = AsyncMock()
    client.request = AsyncMock(side_effect=responses)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestPrimaryWorkerProxy:
    @pytest.mark.asyncio
    async def test_uses_loopback_url_and_forwards_required_headers(self):
        request = _proxy_request(
            headers={
                "authorization": "Bearer token",
                "cookie": "session=abc",
                "x-csrf-token": "csrf-token",
                "accept": "application/json",
                "x-filaman-primary-hop": "2",
            }
        )
        client = _mock_async_client(httpx.Response(200, json={"ok": True}))

        with patch("app.api.v1.printers.httpx.AsyncClient", return_value=client):
            result = await printers_api._proxy_to_primary(
                request,
                method="POST",
                path="/api/v1/printers/3/driver/action",
                json_body={"action": "assign_spool"},
            )

        assert result == {"ok": True}
        method, url = client.request.await_args.args[:2]
        assert method == "POST"
        assert url == "http://127.0.0.1:8000/api/v1/printers/3/driver/action"
        assert client.request.await_args.kwargs["params"] is None
        assert client.request.await_args.kwargs["headers"] == {
            "authorization": "Bearer token",
            "cookie": "session=abc",
            "x-csrf-token": "csrf-token",
            "accept": "application/json",
            "x-filaman-primary-hop": "3",
        }

    @pytest.mark.asyncio
    async def test_forwards_only_explicit_query_params(self):
        request = _proxy_request()
        client = _mock_async_client(httpx.Response(200, json={"presets": []}))

        with patch("app.api.v1.printers.httpx.AsyncClient", return_value=client):
            await printers_api._proxy_to_primary(
                request,
                method="GET",
                path="/api/v1/printers/3/driver/cloud-presets",
                query_params={"model": "X2D", "group": "base"},
            )

        assert client.request.await_args.args[1] == (
            "http://127.0.0.1:8000/api/v1/printers/3/driver/cloud-presets"
        )
        assert client.request.await_args.kwargs["params"] == {"model": "X2D", "group": "base"}

    @pytest.mark.asyncio
    async def test_retries_primary_required_and_returns_primary_payload(self):
        request = _proxy_request(headers={"x-filaman-primary-hop": "0"})
        client = _mock_async_client(
            httpx.Response(503, json={"detail": {"code": "primary_worker_required"}}),
            httpx.Response(200, json={"connected": True}),
        )

        with patch("app.api.v1.printers.httpx.AsyncClient", return_value=client):
            result = await printers_api._proxy_to_primary(
                request,
                method="POST",
                path="/api/v1/printers/3/driver/action",
            )

        assert result == {"connected": True}
        assert client.request.await_count == 2

    @pytest.mark.asyncio
    async def test_proxies_primary_http_error(self):
        request = _proxy_request()
        client = _mock_async_client(
            httpx.Response(400, json={"detail": {"code": "action_failed", "message": "bad action"}})
        )

        with patch("app.api.v1.printers.httpx.AsyncClient", return_value=client):
            with pytest.raises(HTTPException) as exc_info:
                await printers_api._proxy_to_primary(
                    request,
                    method="POST",
                    path="/api/v1/printers/3/driver/action",
                )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == {"code": "action_failed", "message": "bad action"}

    @pytest.mark.asyncio
    async def test_stops_at_max_hop_before_creating_request(self):
        request = _proxy_request(
            headers={"x-filaman-primary-hop": str(printers_api._PRIMARY_PROXY_MAX_HOPS)}
        )

        with pytest.raises(HTTPException) as exc_info:
            await printers_api._proxy_to_primary(
                request,
                method="POST",
                path="/api/v1/printers/3/driver/action",
            )

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "primary_proxy_failed"


class TestPrinterCRUD:
    @pytest.mark.asyncio
    async def test_list_printers_paginated(self, auth_client, db_session):
        client, _ = auth_client

        await _create_printer(db_session, name="Printer A")
        await _create_printer(db_session, name="Printer B")

        response = await client.get("/api/v1/printers?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "total" in data
        names = {item["name"] for item in data["items"]}
        assert {"Printer A", "Printer B"}.issubset(names)

    @pytest.mark.asyncio
    async def test_create_printer(self, auth_client, db_session):
        client, csrf_token = auth_client
        location = await _create_location(db_session)

        response = await client.post(
            "/api/v1/printers",
            json={"name": "My Printer", "driver_key": "bambu_mqtt", "location_id": location.id},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Printer"
        assert data["driver_key"] == "bambu_mqtt"
        assert data["is_active"] is True
        assert data["location_id"] == location.id

    @pytest.mark.asyncio
    async def test_create_printer_with_invalid_location(self, auth_client):
        client, csrf_token = auth_client

        response = await client.post(
            "/api/v1/printers",
            json={"name": "Bad Printer", "driver_key": "bambu_mqtt", "location_id": 999999},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "validation_error"

    @pytest.mark.asyncio
    async def test_get_printer_detail(self, auth_client, db_session):
        client, _ = auth_client

        printer = await _create_printer(db_session, name="Detail Printer")
        await _create_slot(db_session, printer.id, slot_no=1, name="Slot 1")

        response = await client.get(f"/api/v1/printers/{printer.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == printer.id
        assert data["name"] == "Detail Printer"
        assert len(data["slots"]) == 1
        assert data["slots"][0]["slot_no"] == 1

    @pytest.mark.asyncio
    async def test_get_printer_not_found(self, auth_client):
        client, _ = auth_client

        response = await client.get("/api/v1/printers/999999")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"

    @pytest.mark.asyncio
    async def test_update_printer(self, auth_client, db_session):
        client, csrf_token = auth_client

        printer = await _create_printer(db_session, name="Old Name")

        response = await client.patch(
            f"/api/v1/printers/{printer.id}",
            json={"name": "New Name"},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_delete_printer_soft_delete(self, auth_client, db_session):
        client, csrf_token = auth_client

        printer = await _create_printer(db_session, name="Delete Printer")

        response = await client.delete(
            f"/api/v1/printers/{printer.id}",
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 204
        await db_session.refresh(printer)
        assert printer.deleted_at is not None

        list_response = await client.get("/api/v1/printers?page=1&page_size=10")
        assert list_response.status_code == 200
        items = list_response.json()["items"]
        assert printer.id not in {item["id"] for item in items}

    @pytest.mark.asyncio
    async def test_delete_printer_not_found(self, auth_client):
        client, csrf_token = auth_client

        response = await client.delete(
            "/api/v1/printers/999999",
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"


class TestPrinterSlots:
    @pytest.mark.asyncio
    async def test_list_slots_empty(self, auth_client, db_session):
        client, _ = auth_client

        printer = await _create_printer(db_session)

        response = await client.get(f"/api/v1/printers/{printer.id}/slots")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_slots_with_slots(self, auth_client, db_session):
        client, _ = auth_client

        printer = await _create_printer(db_session)
        await _create_slot(db_session, printer.id, slot_no=2, name="Slot 2")
        await _create_slot(db_session, printer.id, slot_no=1, name="Slot 1")

        response = await client.get(f"/api/v1/printers/{printer.id}/slots")

        assert response.status_code == 200
        data = response.json()
        assert [item["slot_no"] for item in data] == [1, 2]

    @pytest.mark.asyncio
    async def test_list_slots_after_soft_delete(self, auth_client, db_session):
        client, csrf_token = auth_client

        printer = await _create_printer(db_session)
        await _create_slot(db_session, printer.id, slot_no=1)

        response = await client.delete(
            f"/api/v1/printers/{printer.id}",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 204

        list_response = await client.get(f"/api/v1/printers/{printer.id}/slots")
        assert list_response.status_code == 200
        assert [item["slot_no"] for item in list_response.json()] == [1]

    @pytest.mark.asyncio
    async def test_list_slots_printer_not_found_returns_empty(self, auth_client):
        client, _ = auth_client

        response = await client.get("/api/v1/printers/999999/slots")

        assert response.status_code == 200
        assert response.json() == []
