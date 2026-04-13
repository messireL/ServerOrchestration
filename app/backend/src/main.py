from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.db import (
    attach_server_to_group,
    create_group,
    create_server,
    delete_group,
    delete_server,
    detach_server_from_group,
    get_summary,
    init_db,
    list_active_alerts,
    list_enabled_servers,
    list_group_links,
    list_groups,
    list_server_status,
    list_servers,
    ping_db,
    resolve_alert,
    set_alert_active,
    update_group,
    update_http_status,
    update_ping_status,
    update_server,
    update_ssh_status,
)
from src.probes import get_ping_diagnostics, run_http_check, run_ping, run_tcp_connect

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_DISPLAY_NAME = os.getenv("APP_DISPLAY_NAME", "Система мониторинга")
APP_VERSION = os.getenv("APP_VERSION", "0.1.21")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")
APP_PUBLIC_BASE_URL = os.getenv("APP_PUBLIC_BASE_URL", "http://192.168.5.22:18080")
STATIC_DIR = Path(__file__).resolve().parent / "static"


logger = logging.getLogger(__name__)


def _normalize_probe_error(error: object) -> str | None:
    if error is None:
        return None
    text = str(error).strip()
    if not text:
        return None
    return text[:500]


def _run_ping_probe_for_server(server: dict, timeout_seconds: int) -> dict:
    probe = run_ping(server["host"], timeout_seconds=timeout_seconds)
    persistence_error = None

    try:
        update_ping_status(
            server_id=server["id"],
            ping_ok=probe["ok"],
            ping_latency_ms=probe["latency_ms"],
            error=_normalize_probe_error(probe["error"]),
        )

        if probe["ok"]:
            resolve_alert(server_id=server["id"], alert_type="ping_down")
        else:
            set_alert_active(
                server_id=server["id"],
                alert_type="ping_down",
                severity="critical",
                message=f"Ping недоступен: {_normalize_probe_error(probe['error']) or 'host unreachable'}",
            )
    except Exception as exc:
        logger.exception("Ping probe persistence failed for server_id=%s host=%s", server.get("id"), server.get("host"))
        persistence_error = _normalize_probe_error(exc)

    result_ok = bool(probe["ok"]) and persistence_error is None
    result_error = _normalize_probe_error(probe["error"])
    if persistence_error:
        result_error = f"db persistence failed: {persistence_error}"

    return {
        "server_id": server["id"],
        "name": server["name"],
        "host": server["host"],
        "ok": result_ok,
        "probe_ok": bool(probe["ok"]),
        "latency_ms": probe["latency_ms"],
        "error": result_error,
        "persistence_error": persistence_error,
    }


def _run_ssh_probe_for_server(server: dict, timeout_seconds: int) -> dict:
    probe = run_tcp_connect(server["host"], server["ssh_port"], timeout_seconds=timeout_seconds)
    persistence_error = None

    try:
        update_ssh_status(
            server_id=server["id"],
            ssh_ok=probe["ok"],
            ssh_latency_ms=probe["latency_ms"],
            error=_normalize_probe_error(probe["error"]),
        )
        if probe["ok"]:
            resolve_alert(server_id=server["id"], alert_type="ssh_down")
        else:
            set_alert_active(
                server_id=server["id"],
                alert_type="ssh_down",
                severity="critical",
                message=f"SSH порт недоступен: {_normalize_probe_error(probe['error']) or 'tcp connect failed'}",
            )
    except Exception as exc:
        logger.exception("SSH probe persistence failed for server_id=%s host=%s", server.get("id"), server.get("host"))
        persistence_error = _normalize_probe_error(exc)

    result_ok = bool(probe["ok"]) and persistence_error is None
    result_error = _normalize_probe_error(probe["error"])
    if persistence_error:
        result_error = f"db persistence failed: {persistence_error}"

    return {
        "server_id": server["id"],
        "name": server["name"],
        "host": server["host"],
        "port": server["ssh_port"],
        "ok": result_ok,
        "probe_ok": bool(probe["ok"]),
        "latency_ms": probe["latency_ms"],
        "error": result_error,
        "persistence_error": persistence_error,
    }


def _run_http_probe_for_server(server: dict, timeout_seconds: int) -> dict:
    if not server.get("has_http_monitoring"):
        try:
            update_http_status(server_id=server["id"], http_ok=None, http_status_code=None, http_response_ms=None, error=None)
        except Exception as exc:
            logger.exception("HTTP probe status reset failed for server_id=%s host=%s", server.get("id"), server.get("host"))
            return {
                "server_id": server["id"],
                "name": server["name"],
                "url": server.get("web_url"),
                "ok": False,
                "probe_ok": None,
                "status_code": None,
                "response_ms": None,
                "error": f"db persistence failed: {_normalize_probe_error(exc)}",
                "skipped": False,
                "persistence_error": _normalize_probe_error(exc),
            }

        return {
            "server_id": server["id"],
            "name": server["name"],
            "url": server.get("web_url"),
            "ok": None,
            "probe_ok": None,
            "status_code": None,
            "response_ms": None,
            "error": "http monitoring disabled",
            "skipped": True,
            "persistence_error": None,
        }

    probe = run_http_check(server.get("web_url") or "", timeout_seconds=timeout_seconds)
    persistence_error = None

    try:
        update_http_status(
            server_id=server["id"],
            http_ok=probe["ok"],
            http_status_code=probe["status_code"],
            http_response_ms=probe["response_ms"],
            error=_normalize_probe_error(probe["error"]),
        )
        if probe["ok"] is True:
            resolve_alert(server_id=server["id"], alert_type="http_down")
        elif probe["ok"] is False:
            set_alert_active(
                server_id=server["id"],
                alert_type="http_down",
                severity="warning",
                message=f"HTTP/HTTPS недоступен: {_normalize_probe_error(probe['error']) or 'request failed'}",
            )
    except Exception as exc:
        logger.exception("HTTP probe persistence failed for server_id=%s host=%s", server.get("id"), server.get("host"))
        persistence_error = _normalize_probe_error(exc)

    result_ok = probe["ok"] if persistence_error is None else False
    result_error = _normalize_probe_error(probe["error"])
    if persistence_error:
        result_error = f"db persistence failed: {persistence_error}"

    return {
        "server_id": server["id"],
        "name": server["name"],
        "url": server.get("web_url"),
        "ok": result_ok,
        "probe_ok": probe["ok"],
        "status_code": probe["status_code"],
        "response_ms": probe["response_ms"],
        "error": result_error,
        "skipped": probe["ok"] is None and persistence_error is None,
        "persistence_error": persistence_error,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Server Orchestration API", version=APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ServerPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="srvops", min_length=1, max_length=100)
    web_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None
    is_enabled: bool = True
    has_3xui: bool = False
    has_ssl_monitoring: bool = False
    has_http_monitoring: bool = False


class GroupPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class PingProbeRequest(BaseModel):
    timeout_seconds: int = Field(default=2, ge=1, le=10)


class ConnectivityProbeRequest(BaseModel):
    tcp_timeout_seconds: int = Field(default=3, ge=1, le=15)
    http_timeout_seconds: int = Field(default=5, ge=1, le=30)


@app.get("/", response_class=FileResponse)
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    db_ok = False
    try:
        db_ok = ping_db()
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "service": APP_NAME,
        "version": APP_VERSION,
        "database": db_ok,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/version")
def version():
    return {
        "service": APP_NAME,
        "display_name": APP_DISPLAY_NAME,
        "version": APP_VERSION,
        "timezone": APP_TZ,
        "public_base_url": APP_PUBLIC_BASE_URL,
    }


@app.get("/api/summary")
def api_summary():
    return get_summary()


@app.get("/api/servers")
def api_list_servers():
    return list_servers()


@app.post("/api/servers")
def api_create_server(payload: ServerPayload):
    try:
        return create_server(
            name=payload.name,
            host=payload.host,
            ssh_port=payload.ssh_port,
            ssh_user=payload.ssh_user,
            web_url=payload.web_url,
            description=payload.description,
            is_enabled=payload.is_enabled,
            has_3xui=payload.has_3xui,
            has_ssl_monitoring=payload.has_ssl_monitoring,
            has_http_monitoring=payload.has_http_monitoring,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/servers/{server_id}")
def api_update_server(server_id: int, payload: ServerPayload):
    try:
        return update_server(
            server_id=server_id,
            name=payload.name,
            host=payload.host,
            ssh_port=payload.ssh_port,
            ssh_user=payload.ssh_user,
            web_url=payload.web_url,
            description=payload.description,
            is_enabled=payload.is_enabled,
            has_3xui=payload.has_3xui,
            has_ssl_monitoring=payload.has_ssl_monitoring,
            has_http_monitoring=payload.has_http_monitoring,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/servers/{server_id}")
def api_delete_server(server_id: int):
    try:
        return delete_server(server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/groups")
def api_list_groups():
    return list_groups()


@app.post("/api/groups")
def api_create_group(payload: GroupPayload):
    try:
        return create_group(name=payload.name, description=payload.description)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.put("/api/groups/{group_id}")
def api_update_group(group_id: int, payload: GroupPayload):
    try:
        return update_group(group_id=group_id, name=payload.name, description=payload.description)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/groups/{group_id}")
def api_delete_group(group_id: int):
    try:
        return delete_group(group_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/group-links")
def api_list_group_links():
    return list_group_links()


@app.post("/api/groups/{group_id}/servers/{server_id}")
def api_attach_server_to_group(group_id: int, server_id: int):
    try:
        return attach_server_to_group(group_id=group_id, server_id=server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/groups/{group_id}/servers/{server_id}")
def api_detach_server_from_group(group_id: int, server_id: int):
    try:
        return detach_server_from_group(group_id=group_id, server_id=server_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/status/servers")
def api_list_server_status():
    return list_server_status()


@app.get("/api/alerts")
def api_list_alerts():
    return list_active_alerts()


@app.get("/api/probes/ping/diagnostics")
def api_ping_diagnostics():
    return get_ping_diagnostics()


@app.post("/api/probes/ping/run")
def api_run_ping_probe(payload: PingProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0

    for server in servers:
        try:
            result = _run_ping_probe_for_server(server, payload.timeout_seconds)
        except Exception as exc:
            logger.exception("Ping probe execution crashed for server_id=%s host=%s", server.get("id"), server.get("host"))
            result = {
                "server_id": server["id"],
                "name": server["name"],
                "host": server["host"],
                "ok": False,
                "probe_ok": False,
                "latency_ms": None,
                "error": f"unexpected ping probe error: {_normalize_probe_error(exc)}",
                "persistence_error": None,
            }

        if result["ok"]:
            ok_count += 1
        else:
            fail_count += 1
        results.append(result)

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results}


@app.post("/api/probes/ssh/run")
def api_run_ssh_probe(payload: ConnectivityProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0

    for server in servers:
        try:
            result = _run_ssh_probe_for_server(server, payload.tcp_timeout_seconds)
        except Exception as exc:
            logger.exception("SSH probe execution crashed for server_id=%s host=%s", server.get("id"), server.get("host"))
            result = {
                "server_id": server["id"],
                "name": server["name"],
                "host": server["host"],
                "port": server["ssh_port"],
                "ok": False,
                "probe_ok": False,
                "latency_ms": None,
                "error": f"unexpected ssh probe error: {_normalize_probe_error(exc)}",
                "persistence_error": None,
            }

        if result["ok"]:
            ok_count += 1
        else:
            fail_count += 1
        results.append(result)

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results}


@app.post("/api/probes/http/run")
def api_run_http_probe(payload: ConnectivityProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0
    skipped_count = 0

    for server in servers:
        try:
            result = _run_http_probe_for_server(server, payload.http_timeout_seconds)
        except Exception as exc:
            logger.exception("HTTP probe execution crashed for server_id=%s host=%s", server.get("id"), server.get("host"))
            result = {
                "server_id": server["id"],
                "name": server["name"],
                "url": server.get("web_url"),
                "ok": False,
                "probe_ok": False,
                "status_code": None,
                "response_ms": None,
                "error": f"unexpected http probe error: {_normalize_probe_error(exc)}",
                "skipped": False,
                "persistence_error": None,
            }

        if result.get("skipped"):
            skipped_count += 1
        elif result["ok"]:
            ok_count += 1
        else:
            fail_count += 1
        results.append(result)

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "skipped": skipped_count, "results": results}


@app.post("/api/probes/connectivity/run")
def api_run_connectivity_probe(payload: ConnectivityProbeRequest):
    ping_result = api_run_ping_probe(PingProbeRequest(timeout_seconds=min(payload.tcp_timeout_seconds, 10)))
    ssh_result = api_run_ssh_probe(payload)
    http_result = api_run_http_probe(payload)
    return {"ping": ping_result, "ssh": ssh_result, "http": http_result}
