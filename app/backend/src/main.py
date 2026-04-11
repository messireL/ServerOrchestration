from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
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
from src.probes import run_http_check, run_ping, run_tcp_connect

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_DISPLAY_NAME = os.getenv("APP_DISPLAY_NAME", "Система мониторинга")
APP_VERSION = os.getenv("APP_VERSION", "0.1.15")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")
APP_PUBLIC_BASE_URL = os.getenv("APP_PUBLIC_BASE_URL", "http://192.168.5.22:18080")
STATIC_DIR = Path(__file__).resolve().parent / "static"


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


@app.post("/api/probes/ping/run")
def api_run_ping_probe(payload: PingProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0

    for server in servers:
        probe = run_ping(server["host"], timeout_seconds=payload.timeout_seconds)
        update_ping_status(server_id=server["id"], ping_ok=probe["ok"], ping_latency_ms=probe["latency_ms"], error=probe["error"])

        if probe["ok"]:
            ok_count += 1
            resolve_alert(server_id=server["id"], alert_type="ping_down")
        else:
            fail_count += 1
            set_alert_active(server_id=server["id"], alert_type="ping_down", severity="critical", message=f"Ping недоступен: {probe['error'] or 'host unreachable'}")

        results.append({"server_id": server["id"], "name": server["name"], "host": server["host"], "ok": probe["ok"], "latency_ms": probe["latency_ms"], "error": probe["error"]})

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results}


@app.post("/api/probes/ssh/run")
def api_run_ssh_probe(payload: ConnectivityProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0

    for server in servers:
        probe = run_tcp_connect(server["host"], server["ssh_port"], timeout_seconds=payload.tcp_timeout_seconds)
        update_ssh_status(server_id=server["id"], ssh_ok=probe["ok"], ssh_latency_ms=probe["latency_ms"], error=probe["error"])
        if probe["ok"]:
            ok_count += 1
            resolve_alert(server_id=server["id"], alert_type="ssh_down")
        else:
            fail_count += 1
            set_alert_active(server_id=server["id"], alert_type="ssh_down", severity="critical", message=f"SSH порт недоступен: {probe['error'] or 'tcp connect failed'}")
        results.append({"server_id": server["id"], "name": server["name"], "host": server["host"], "port": server["ssh_port"], "ok": probe["ok"], "latency_ms": probe["latency_ms"], "error": probe["error"]})

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results}


@app.post("/api/probes/http/run")
def api_run_http_probe(payload: ConnectivityProbeRequest):
    servers = list_enabled_servers()
    results = []
    ok_count = 0
    fail_count = 0
    skipped_count = 0

    for server in servers:
        if not server.get("has_http_monitoring"):
            update_http_status(server_id=server["id"], http_ok=None, http_status_code=None, http_response_ms=None, error=None)
            results.append({"server_id": server["id"], "name": server["name"], "url": server.get("web_url"), "ok": None, "status_code": None, "response_ms": None, "error": "http monitoring disabled", "skipped": True})
            skipped_count += 1
            continue

        probe = run_http_check(server.get("web_url") or "", timeout_seconds=payload.http_timeout_seconds)
        update_http_status(server_id=server["id"], http_ok=probe["ok"], http_status_code=probe["status_code"], http_response_ms=probe["response_ms"], error=probe["error"])
        if probe["ok"] is True:
            ok_count += 1
            resolve_alert(server_id=server["id"], alert_type="http_down")
        elif probe["ok"] is False:
            fail_count += 1
            set_alert_active(server_id=server["id"], alert_type="http_down", severity="warning", message=f"HTTP/HTTPS недоступен: {probe['error'] or 'request failed'}")
        else:
            skipped_count += 1

        results.append({"server_id": server["id"], "name": server["name"], "url": server.get("web_url"), "ok": probe["ok"], "status_code": probe["status_code"], "response_ms": probe["response_ms"], "error": probe["error"], "skipped": probe["ok"] is None})

    return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "skipped": skipped_count, "results": results}


@app.post("/api/probes/connectivity/run")
def api_run_connectivity_probe(payload: ConnectivityProbeRequest):
    ping_result = api_run_ping_probe(PingProbeRequest(timeout_seconds=min(payload.tcp_timeout_seconds, 10)))
    ssh_result = api_run_ssh_probe(payload)
    http_result = api_run_http_probe(payload)
    return {"ping": ping_result, "ssh": ssh_result, "http": http_result}
