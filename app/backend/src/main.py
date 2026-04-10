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
    get_summary,
    init_db,
    list_active_alerts,
    list_enabled_servers,
    list_groups,
    list_server_status,
    list_servers,
    ping_db,
    resolve_alert,
    set_alert_active,
    update_ping_status,
)
from src.probes import run_ping

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_VERSION = os.getenv("APP_VERSION", "0.1.6")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")
APP_PUBLIC_BASE_URL = os.getenv("APP_PUBLIC_BASE_URL", "http://192.168.5.22:18080")
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Server Orchestration API",
    version=APP_VERSION,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="srvops", min_length=1, max_length=100)
    description: Optional[str] = None
    is_enabled: bool = True
    has_3xui: bool = False
    has_ssl_monitoring: bool = False


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class PingProbeRequest(BaseModel):
    timeout_seconds: int = Field(default=2, ge=1, le=10)


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
def api_create_server(payload: ServerCreate):
    try:
        return create_server(
            name=payload.name,
            host=payload.host,
            ssh_port=payload.ssh_port,
            ssh_user=payload.ssh_user,
            description=payload.description,
            is_enabled=payload.is_enabled,
            has_3xui=payload.has_3xui,
            has_ssl_monitoring=payload.has_ssl_monitoring,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/groups")
def api_list_groups():
    return list_groups()


@app.post("/api/groups")
def api_create_group(payload: GroupCreate):
    try:
        return create_group(
            name=payload.name,
            description=payload.description,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/groups/{group_id}/servers/{server_id}")
def api_attach_server_to_group(group_id: int, server_id: int):
    try:
        return attach_server_to_group(group_id=group_id, server_id=server_id)
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
        update_ping_status(
            server_id=server["id"],
            ping_ok=probe["ok"],
            ping_latency_ms=probe["latency_ms"],
            error=probe["error"],
        )

        if probe["ok"]:
            ok_count += 1
            resolve_alert(server_id=server["id"], alert_type="ping_down")
        else:
            fail_count += 1
            set_alert_active(
                server_id=server["id"],
                alert_type="ping_down",
                severity="critical",
                message=f"Ping недоступен: {probe['error'] or 'host unreachable'}",
            )

        results.append(
            {
                "server_id": server["id"],
                "name": server["name"],
                "host": server["host"],
                "ok": probe["ok"],
                "latency_ms": probe["latency_ms"],
                "error": probe["error"],
            }
        )

    return {
        "processed": len(servers),
        "ok": ok_count,
        "failed": fail_count,
        "results": results,
    }
