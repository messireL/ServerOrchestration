from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.db import (
    attach_server_to_group,
    create_group,
    create_server,
    get_summary,
    init_db,
    list_groups,
    list_servers,
    ping_db,
)

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_VERSION = os.getenv("APP_VERSION", "0.1.3")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Server Orchestration API",
    version=APP_VERSION,
    lifespan=lifespan,
)

class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="root", min_length=1, max_length=100)
    description: Optional[str] = None
    is_enabled: bool = True
    has_3xui: bool = False
    has_ssl_monitoring: bool = False

class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None

@app.get("/")
def root():
    return {
        "message": "Server Orchestration backend is running",
        "docs": "/docs",
    }

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
