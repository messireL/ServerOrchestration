import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
import logging
import os
import smtplib
import ssl
import threading
import urllib.parse
import urllib.request
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import src.db as db

from src.db import (
    attach_server_to_group,
    create_group,
    create_server,
    delete_group,
    delete_server,
    detach_server_from_group,
    get_alert_settings,
    get_monitor_settings,
    get_summary,
    init_db,
    insert_alert_delivery_log,
    insert_probe_history,
    list_active_alerts,
    list_alert_delivery_log,
    list_alerts_for_reminder,
    list_enabled_servers,
    list_group_links,
    list_groups,
    list_probe_history,
    list_server_status,
    list_servers,
    list_servers_requiring_stale_alert,
    mark_alert_delivery_attempt,
    mark_scheduler_probe_run,
    ping_db,
    resolve_alert,
    set_alert_active,
    update_alert_settings,
    update_group,
    update_http_status,
    update_monitor_settings,
    update_ping_status,
    update_server,
    update_ssh_status,
    update_3xui_status,
)
from src.probes import get_ping_diagnostics, run_http_check, run_ping, run_tcp_connect

APP_NAME = os.getenv("APP_NAME", "server-orchestration")
APP_DISPLAY_NAME = os.getenv("APP_DISPLAY_NAME", "Система мониторинга")
APP_VERSION = os.getenv("APP_VERSION", "0.1.27")
APP_TZ = os.getenv("APP_TZ", "Europe/Moscow")
APP_PUBLIC_BASE_URL = os.getenv("APP_PUBLIC_BASE_URL", "http://192.168.5.22:18080")
SCHEDULER_POLL_SECONDS = int(os.getenv("MONITOR_SCHEDULER_POLL_SECONDS", "5"))
STATIC_DIR = Path(__file__).resolve().parent / "static"

logger = logging.getLogger(__name__)
PROBE_BATCH_LOCK = threading.Lock()


def _normalize_probe_error(error: object) -> str | None:
    if error is None:
        return None
    text = str(error).strip()
    if not text:
        return None
    return text[:500]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _probe_due(last_run_at: object, interval_seconds: int) -> bool:
    if interval_seconds <= 0:
        return False
    last_dt = _coerce_dt(last_run_at)
    if last_dt is None:
        return True
    return _utc_now() >= last_dt + timedelta(seconds=interval_seconds)


def _channel_status() -> dict:
    telegram_token = os.getenv("ALERT_TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID", "").strip()
    smtp_host = os.getenv("ALERT_SMTP_HOST", "").strip()
    email_to = os.getenv("ALERT_EMAIL_TO", "").strip()
    email_from = os.getenv("ALERT_EMAIL_FROM", "").strip() or os.getenv("ALERT_SMTP_USER", "").strip()
    return {
        "telegram_configured": bool(telegram_token and telegram_chat_id),
        "telegram_target": telegram_chat_id or None,
        "email_configured": bool(smtp_host and email_to and email_from),
        "email_target": email_to or None,
    }


def _alert_subject_prefix(event_type: str) -> str:
    mapping = {
        "new": "Новый alert",
        "resolved": "Alert resolved",
        "reminder": "Напоминание",
        "test": "Тестовое уведомление",
    }
    return mapping.get(event_type, "Alert")


def _format_age(seconds: object) -> str:
    try:
        total = int(seconds or 0)
    except Exception:
        total = 0
    if total < 60:
        return f"{total} сек"
    minutes, secs = divmod(total, 60)
    if minutes < 60:
        return f"{minutes} мин {secs} сек"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} ч {mins} мин"
    days, hrs = divmod(hours, 24)
    return f"{days} д {hrs} ч"


def _compose_alert_message(alert: dict, event_type: str, server_name: str | None, server_host: str | None) -> tuple[str, str]:
    title = _alert_subject_prefix(event_type)
    server_line = f"{server_name or '—'} ({server_host or '—'})"
    message = alert.get("message") or "Без текста"
    if alert.get("alert_type") == "monitor_stale":
        stale_for = alert.get("stale_for_seconds")
        if stale_for:
            message = f"{message} · stale_for={_format_age(stale_for)}"
    subject = f"[{APP_DISPLAY_NAME}] {title}: {server_name or 'server'} / {alert.get('alert_type') or 'alert'}"
    body = "\n".join([
        f"{title}",
        f"Сервер: {server_line}",
        f"Тип: {alert.get('alert_type') or 'alert'}",
        f"Severity: {alert.get('severity') or 'warning'}",
        f"Сообщение: {message}",
        f"Время: {_utc_now().isoformat()}",
        f"Панель: {APP_PUBLIC_BASE_URL}",
    ])
    return subject, body


def _send_telegram_message(subject: str, body: str) -> tuple[bool, str | None, str | None]:
    token = os.getenv("ALERT_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False, None, "telegram not configured"
    text = f"{subject}\n\n{body}"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return True, chat_id, raw[:500]
    except Exception as exc:
        return False, chat_id, _normalize_probe_error(exc)


def _send_email_message(subject: str, body: str) -> tuple[bool, str | None, str | None]:
    smtp_host = os.getenv("ALERT_SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("ALERT_SMTP_PORT", "587"))
    smtp_user = os.getenv("ALERT_SMTP_USER", "").strip()
    smtp_password = os.getenv("ALERT_SMTP_PASSWORD", "")
    smtp_from = os.getenv("ALERT_EMAIL_FROM", "").strip() or smtp_user
    email_to = os.getenv("ALERT_EMAIL_TO", "").strip()
    smtp_mode = os.getenv("ALERT_SMTP_MODE", "starttls").strip().lower()
    if not smtp_host or not email_to or not smtp_from:
        return False, email_to or None, "smtp/email not configured"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = email_to
    msg.set_content(body)
    try:
        if smtp_mode == "ssl":
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10, context=ssl.create_default_context()) as client:
                if smtp_user:
                    client.login(smtp_user, smtp_password)
                client.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as client:
                client.ehlo()
                if smtp_mode != "plain":
                    client.starttls(context=ssl.create_default_context())
                    client.ehlo()
                if smtp_user:
                    client.login(smtp_user, smtp_password)
                client.send_message(msg)
        return True, email_to, "sent"
    except Exception as exc:
        return False, email_to, _normalize_probe_error(exc)


def _dispatch_alert_notification(alert: dict, event_type: str, server_name: str | None, server_host: str | None, settings: dict | None = None) -> dict:
    settings = settings or get_alert_settings()
    alert_id = alert.get("id")
    subject, body = _compose_alert_message(alert, event_type, server_name, server_host)
    channels = _channel_status()
    if not settings.get("notifications_enabled"):
        if alert_id:
            mark_alert_delivery_attempt(alert_id=alert_id, status="skipped", error="notifications disabled")
        return {"sent": 0, "failed": 0, "skipped": 1}

    attempts = []
    if channels.get("telegram_configured"):
        ok, target, response_or_error = _send_telegram_message(subject, body)
        insert_alert_delivery_log(alert_id, alert.get("server_id"), server_name, server_host, alert.get("alert_type"), event_type, "telegram", target, "sent" if ok else "failed", subject, None if ok else response_or_error)
        attempts.append(ok)
    if channels.get("email_configured"):
        ok, target, response_or_error = _send_email_message(subject, body)
        insert_alert_delivery_log(alert_id, alert.get("server_id"), server_name, server_host, alert.get("alert_type"), event_type, "email", target, "sent" if ok else "failed", subject, None if ok else response_or_error)
        attempts.append(ok)

    if not attempts:
        if alert_id:
            insert_alert_delivery_log(alert_id, alert.get("server_id"), server_name, server_host, alert.get("alert_type"), event_type, "system", None, "skipped", subject, "no delivery channels configured")
            mark_alert_delivery_attempt(alert_id=alert_id, status="skipped", error="no delivery channels configured")
        return {"sent": 0, "failed": 0, "skipped": 1}

    sent = sum(1 for item in attempts if item)
    failed = sum(1 for item in attempts if not item)
    if alert_id:
        mark_alert_delivery_attempt(alert_id=alert_id, status="sent" if sent > 0 else "failed", error=None if sent > 0 else "all delivery channels failed")
    return {"sent": sent, "failed": failed, "skipped": 0}


def _maybe_notify_new_alert(alert_row: dict | None, server_name: str | None, server_host: str | None, settings: dict | None = None) -> None:
    if not alert_row or alert_row.get("_event") != "created":
        return
    settings = settings or get_alert_settings()
    if settings.get("notify_on_new_alert"):
        _dispatch_alert_notification(alert_row, "new", server_name, server_host, settings)


def _maybe_notify_resolved_alerts(resolved_rows: list[dict], server_name: str | None, server_host: str | None, settings: dict | None = None) -> None:
    if not resolved_rows:
        return
    settings = settings or get_alert_settings()
    if not settings.get("notify_on_resolved"):
        return
    for row in resolved_rows:
        _dispatch_alert_notification(row, "resolved", server_name, server_host, settings)


def _evaluate_stale_alerts(settings: dict | None = None) -> dict:
    settings = settings or get_alert_settings()
    if not settings.get("stale_alert_enabled"):
        resolved = 0
        for row in list_active_alerts():
            if row.get("alert_type") == "monitor_stale":
                resolved_rows = resolve_alert(server_id=row["server_id"], alert_type="monitor_stale")
                if resolved_rows:
                    resolved += len(resolved_rows)
                    _maybe_notify_resolved_alerts(resolved_rows, row.get("server_name"), row.get("server_host"), settings)
        return {"created": 0, "resolved": resolved}
    created = 0
    resolved = 0
    stale_candidates = list_servers_requiring_stale_alert(int(settings.get("stale_after_seconds") or 900))
    stale_ids = {int(item["id"]) for item in stale_candidates}
    for server in stale_candidates:
        message = f"Данные мониторинга устарели: последняя проверка {server.get('last_check_at')}"
        alert_row = set_alert_active(server_id=server["id"], alert_type="monitor_stale", severity="warning", message=message)
        alert_row["stale_for_seconds"] = server.get("stale_for_seconds")
        if alert_row.get("_event") == "created":
            created += 1
            _maybe_notify_new_alert(alert_row, server.get("name"), server.get("host"), settings)
    for row in list_active_alerts():
        if row.get("alert_type") == "monitor_stale" and int(row.get("server_id") or 0) not in stale_ids:
            resolved_rows = resolve_alert(server_id=row["server_id"], alert_type="monitor_stale")
            if resolved_rows:
                resolved += len(resolved_rows)
                _maybe_notify_resolved_alerts(resolved_rows, row.get("server_name"), row.get("server_host"), settings)
    return {"created": created, "resolved": resolved}


def _dispatch_due_reminders(settings: dict | None = None) -> int:
    settings = settings or get_alert_settings()
    sent = 0
    for alert in list_alerts_for_reminder(int(settings.get("reminder_interval_seconds") or 3600)):
        result = _dispatch_alert_notification(alert, "reminder", alert.get("server_name"), alert.get("server_host"), settings)
        sent += int(result.get("sent") or 0)
    return sent


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
            _maybe_notify_resolved_alerts(resolve_alert(server_id=server["id"], alert_type="ping_down"), server.get("name"), server.get("host"))
        else:
            _maybe_notify_new_alert(
                set_alert_active(
                    server_id=server["id"],
                    alert_type="ping_down",
                    severity="critical",
                    message=f"Ping недоступен: {_normalize_probe_error(probe['error']) or 'host unreachable'}",
                ),
                server.get("name"),
                server.get("host"),
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
            _maybe_notify_resolved_alerts(resolve_alert(server_id=server["id"], alert_type="ssh_down"), server.get("name"), server.get("host"))
        else:
            _maybe_notify_new_alert(
                set_alert_active(
                    server_id=server["id"],
                    alert_type="ssh_down",
                    severity="critical",
                    message=f"SSH порт недоступен: {_normalize_probe_error(probe['error']) or 'tcp connect failed'}",
                ),
                server.get("name"),
                server.get("host"),
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
            _maybe_notify_resolved_alerts(resolve_alert(server_id=server["id"], alert_type="http_down"), server.get("name"), server.get("host"))
        elif probe["ok"] is False:
            _maybe_notify_new_alert(
                set_alert_active(
                    server_id=server["id"],
                    alert_type="http_down",
                    severity="warning",
                    message=f"HTTP/HTTPS недоступен: {_normalize_probe_error(probe['error']) or 'request failed'}",
                ),
                server.get("name"),
                server.get("host"),
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


def _pick_preferred_status(*values: object) -> int | None:
    for value in values:
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            continue
    return None


def _pick_preferred_latency(*values: object) -> int | None:
    numeric: list[int] = []
    for value in values:
        if value is None:
            continue
        try:
            numeric.append(int(value))
        except Exception:
            continue
    return max(numeric) if numeric else None


def _join_probe_errors(*parts: object) -> str | None:
    cleaned: list[str] = []
    for part in parts:
        normalized = _normalize_probe_error(part)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    if not cleaned:
        return None
    return " | ".join(cleaned)[:500]


def _run_xui_probe_for_server(server: dict, timeout_seconds: int) -> dict:
    if not server.get("has_3xui"):
        try:
            update_3xui_status(
                server_id=server["id"],
                console_ok=None,
                console_response_ms=None,
                console_status_code=None,
                console_error=None,
                subscription_ok=None,
                subscription_response_ms=None,
                subscription_status_code=None,
                subscription_error=None,
            )
        except Exception as exc:
            logger.exception("3x-ui probe status reset failed for server_id=%s host=%s", server.get("id"), server.get("host"))
            persistence_error = _normalize_probe_error(exc)
            return {
                "server_id": server["id"],
                "name": server["name"],
                "host": server["host"],
                "console_url": server.get("console_3xui_url"),
                "subscription_url": server.get("subscription_3xui_url"),
                "ok": False,
                "probe_ok": None,
                "status_code": None,
                "response_ms": None,
                "console_ok": None,
                "console_status_code": None,
                "console_response_ms": None,
                "subscription_ok": None,
                "subscription_status_code": None,
                "subscription_response_ms": None,
                "error": f"db persistence failed: {persistence_error}",
                "skipped": False,
                "persistence_error": persistence_error,
            }

        return {
            "server_id": server["id"],
            "name": server["name"],
            "host": server["host"],
            "console_url": server.get("console_3xui_url"),
            "subscription_url": server.get("subscription_3xui_url"),
            "ok": None,
            "probe_ok": None,
            "status_code": None,
            "response_ms": None,
            "console_ok": None,
            "console_status_code": None,
            "console_response_ms": None,
            "subscription_ok": None,
            "subscription_status_code": None,
            "subscription_response_ms": None,
            "error": "3x-ui monitoring disabled",
            "skipped": True,
            "persistence_error": None,
        }

    console_probe = run_http_check(server.get("console_3xui_url") or "", timeout_seconds=timeout_seconds)
    subscription_probe = run_http_check(server.get("subscription_3xui_url") or "", timeout_seconds=timeout_seconds)
    persistence_error = None

    try:
        update_3xui_status(
            server_id=server["id"],
            console_ok=console_probe["ok"],
            console_response_ms=console_probe["response_ms"],
            console_status_code=console_probe["status_code"],
            console_error=_normalize_probe_error(console_probe["error"]),
            subscription_ok=subscription_probe["ok"],
            subscription_response_ms=subscription_probe["response_ms"],
            subscription_status_code=subscription_probe["status_code"],
            subscription_error=_normalize_probe_error(subscription_probe["error"]),
        )
        probe_states = [item for item in (console_probe.get("ok"), subscription_probe.get("ok")) if item is not None]
        if probe_states and all(item is True for item in probe_states):
            _maybe_notify_resolved_alerts(resolve_alert(server_id=server["id"], alert_type="xui_down"), server.get("name"), server.get("host"))
        elif any(item is False for item in probe_states):
            _maybe_notify_new_alert(
                set_alert_active(
                    server_id=server["id"],
                    alert_type="xui_down",
                    severity="warning",
                    message=f"3x-ui недоступен: {_join_probe_errors(console_probe.get('error'), subscription_probe.get('error')) or 'request failed'}",
                ),
                server.get("name"),
                server.get("host"),
            )
    except Exception as exc:
        logger.exception("3x-ui probe persistence failed for server_id=%s host=%s", server.get("id"), server.get("host"))
        persistence_error = _normalize_probe_error(exc)

    probe_states = [item for item in (console_probe.get("ok"), subscription_probe.get("ok")) if item is not None]
    probe_ok = None if not probe_states else all(item is True for item in probe_states)
    result_ok = probe_ok if persistence_error is None else False
    result_error = _join_probe_errors(console_probe.get("error"), subscription_probe.get("error"))
    if persistence_error:
        result_error = f"db persistence failed: {persistence_error}"

    return {
        "server_id": server["id"],
        "name": server["name"],
        "host": server["host"],
        "console_url": server.get("console_3xui_url"),
        "subscription_url": server.get("subscription_3xui_url"),
        "ok": result_ok,
        "probe_ok": probe_ok,
        "status_code": _pick_preferred_status(
            console_probe.get("status_code") if console_probe.get("ok") is False else None,
            subscription_probe.get("status_code") if subscription_probe.get("ok") is False else None,
            console_probe.get("status_code"),
            subscription_probe.get("status_code"),
        ),
        "response_ms": _pick_preferred_latency(console_probe.get("response_ms"), subscription_probe.get("response_ms")),
        "console_ok": console_probe.get("ok"),
        "console_status_code": console_probe.get("status_code"),
        "console_response_ms": console_probe.get("response_ms"),
        "subscription_ok": subscription_probe.get("ok"),
        "subscription_status_code": subscription_probe.get("status_code"),
        "subscription_response_ms": subscription_probe.get("response_ms"),
        "error": result_error,
        "skipped": probe_ok is None and persistence_error is None,
        "persistence_error": persistence_error,
    }


def _execute_xui_batch(timeout_seconds: int, source: str) -> dict:
    with PROBE_BATCH_LOCK:
        servers = list_enabled_servers()
        results = []
        ok_count = 0
        fail_count = 0
        skipped_count = 0
        errors: list[str] = []

        for server in servers:
            started_at = _utc_now()
            try:
                result = _run_xui_probe_for_server(server, timeout_seconds)
            except Exception as exc:
                logger.exception("3x-ui probe execution crashed for server_id=%s host=%s", server.get("id"), server.get("host"))
                result = {
                    "server_id": server["id"],
                    "name": server["name"],
                    "host": server["host"],
                    "console_url": server.get("console_3xui_url"),
                    "subscription_url": server.get("subscription_3xui_url"),
                    "ok": False,
                    "probe_ok": False,
                    "status_code": None,
                    "response_ms": None,
                    "console_ok": None,
                    "console_status_code": None,
                    "console_response_ms": None,
                    "subscription_ok": None,
                    "subscription_status_code": None,
                    "subscription_response_ms": None,
                    "error": f"unexpected 3x-ui probe error: {_normalize_probe_error(exc)}",
                    "skipped": False,
                    "persistence_error": None,
                }
            finished_at = _utc_now()
            _record_probe_history(result, probe_type="xui", source=source, started_at=started_at, finished_at=finished_at)

            if result.get("skipped"):
                skipped_count += 1
            elif result.get("ok"):
                ok_count += 1
            else:
                fail_count += 1
                if result.get("error"):
                    errors.append(str(result["error"]))
            results.append(result)

        if source == "scheduler":
            mark_scheduler_probe_run("xui")

        return {
            "processed": len(servers),
            "ok": ok_count,
            "failed": fail_count,
            "skipped": skipped_count,
            "results": results,
            "errors": errors[:10],
            "source": source,
        }



def _record_probe_history(result: dict, probe_type: str, source: str, started_at: datetime, finished_at: datetime) -> None:
    try:
        latency_value = result.get("response_ms") if probe_type in {"http", "xui"} else result.get("latency_ms")
        insert_probe_history(
            server_id=result["server_id"],
            server_name_snapshot=result.get("name") or f"server-{result['server_id']}",
            server_host_snapshot=result.get("host") or result.get("url") or result.get("console_url") or result.get("subscription_url") or "—",
            probe_type=probe_type,
            source=source,
            ok=result.get("ok"),
            latency_ms=latency_value,
            status_code=result.get("status_code"),
            error=_normalize_probe_error(result.get("error")),
            started_at=started_at,
            finished_at=finished_at,
        )
    except Exception:
        logger.exception(
            "Probe history persistence failed for server_id=%s probe_type=%s source=%s",
            result.get("server_id"),
            probe_type,
            source,
        )


def _execute_ping_batch(timeout_seconds: int, source: str) -> dict:
    with PROBE_BATCH_LOCK:
        servers = list_enabled_servers()
        results = []
        ok_count = 0
        fail_count = 0

        for server in servers:
            started_at = _utc_now()
            try:
                result = _run_ping_probe_for_server(server, timeout_seconds)
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
            finished_at = _utc_now()
            _record_probe_history(result, probe_type="ping", source=source, started_at=started_at, finished_at=finished_at)

            if result["ok"]:
                ok_count += 1
            else:
                fail_count += 1
            results.append(result)

        if source == "scheduler":
            mark_scheduler_probe_run("ping")

        return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results, "source": source}


def _execute_ssh_batch(timeout_seconds: int, source: str) -> dict:
    with PROBE_BATCH_LOCK:
        servers = list_enabled_servers()
        results = []
        ok_count = 0
        fail_count = 0

        for server in servers:
            started_at = _utc_now()
            try:
                result = _run_ssh_probe_for_server(server, timeout_seconds)
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
            finished_at = _utc_now()
            _record_probe_history(result, probe_type="ssh", source=source, started_at=started_at, finished_at=finished_at)

            if result["ok"]:
                ok_count += 1
            else:
                fail_count += 1
            results.append(result)

        if source == "scheduler":
            mark_scheduler_probe_run("ssh")

        return {"processed": len(servers), "ok": ok_count, "failed": fail_count, "results": results, "source": source}


def _execute_http_batch(timeout_seconds: int, source: str) -> dict:
    with PROBE_BATCH_LOCK:
        servers = list_enabled_servers()
        results = []
        ok_count = 0
        fail_count = 0
        skipped_count = 0

        for server in servers:
            started_at = _utc_now()
            try:
                result = _run_http_probe_for_server(server, timeout_seconds)
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
            finished_at = _utc_now()
            _record_probe_history(result, probe_type="http", source=source, started_at=started_at, finished_at=finished_at)

            if result.get("skipped"):
                skipped_count += 1
            elif result["ok"]:
                ok_count += 1
            else:
                fail_count += 1
            results.append(result)

        if source == "scheduler":
            mark_scheduler_probe_run("http")

        return {
            "processed": len(servers),
            "ok": ok_count,
            "failed": fail_count,
            "skipped": skipped_count,
            "results": results,
            "source": source,
        }


async def _scheduler_loop(stop_event: asyncio.Event) -> None:
    logger.info("Background scheduler loop started with poll=%ss", SCHEDULER_POLL_SECONDS)
    while not stop_event.is_set():
        try:
            settings = get_monitor_settings()
            alert_settings = get_alert_settings()
            if settings.get("scheduler_enabled"):
                if _probe_due(settings.get("last_ping_scheduler_run_at"), int(settings.get("ping_interval_seconds") or 0)):
                    logger.info("Scheduler starting ping batch")
                    await asyncio.to_thread(_execute_ping_batch, int(settings.get("ping_timeout_seconds") or 2), "scheduler")
                    settings = get_monitor_settings()
                if _probe_due(settings.get("last_ssh_scheduler_run_at"), int(settings.get("ssh_interval_seconds") or 0)):
                    logger.info("Scheduler starting ssh batch")
                    await asyncio.to_thread(_execute_ssh_batch, int(settings.get("tcp_timeout_seconds") or 3), "scheduler")
                    settings = get_monitor_settings()
                http_due = _probe_due(settings.get("last_http_scheduler_run_at"), int(settings.get("http_interval_seconds") or 0))
                xui_due = _probe_due(settings.get("last_xui_scheduler_run_at"), int(settings.get("xui_interval_seconds") or 0))
                if http_due:
                    logger.info("Scheduler starting http batch")
                    await asyncio.to_thread(_execute_http_batch, int(settings.get("http_timeout_seconds") or 5), "scheduler")
                if xui_due:
                    logger.info("Scheduler starting xui batch")
                    await asyncio.to_thread(_execute_xui_batch, int(settings.get("xui_timeout_seconds") or 5), "scheduler")
            await asyncio.to_thread(_evaluate_stale_alerts, alert_settings)
            await asyncio.to_thread(_dispatch_due_reminders, alert_settings)
        except Exception:
            logger.exception("Background scheduler iteration failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=SCHEDULER_POLL_SECONDS)
        except asyncio.TimeoutError:
            continue

    logger.info("Background scheduler loop stopped")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(_scheduler_loop(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        await scheduler_task


app = FastAPI(title="Server Orchestration API", version=APP_VERSION, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ServerPayload(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    host: str = Field(min_length=1, max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="srvops", min_length=1, max_length=100)
    web_url: Optional[str] = Field(default=None, max_length=500)
    console_3xui_url: Optional[str] = Field(default=None, max_length=500)
    subscription_3xui_url: Optional[str] = Field(default=None, max_length=500)
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
    xui_timeout_seconds: int = Field(default=5, ge=1, le=30)


class MonitorSettingsPayload(BaseModel):
    scheduler_enabled: bool = True
    ping_interval_seconds: int = Field(default=60, ge=15, le=86400)
    ssh_interval_seconds: int = Field(default=120, ge=15, le=86400)
    http_interval_seconds: int = Field(default=180, ge=15, le=86400)
    xui_interval_seconds: int = Field(default=240, ge=15, le=86400)
    ping_timeout_seconds: int = Field(default=2, ge=1, le=10)
    tcp_timeout_seconds: int = Field(default=3, ge=1, le=15)
    http_timeout_seconds: int = Field(default=5, ge=1, le=30)
    xui_timeout_seconds: int = Field(default=5, ge=1, le=30)


class AlertSettingsPayload(BaseModel):
    notifications_enabled: bool = False
    notify_on_new_alert: bool = True
    notify_on_resolved: bool = True
    stale_alert_enabled: bool = True
    stale_after_seconds: int = Field(default=900, ge=60, le=86400)
    reminder_interval_seconds: int = Field(default=3600, ge=60, le=604800)


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
        "time_utc": _utc_now().isoformat(),
    }


@app.get("/version")
def version():
    return {
        "service": APP_NAME,
        "display_name": APP_DISPLAY_NAME,
        "version": APP_VERSION,
        "timezone": APP_TZ,
        "public_base_url": APP_PUBLIC_BASE_URL,
        "scheduler_poll_seconds": SCHEDULER_POLL_SECONDS,
    }


@app.get("/api/summary")
def api_summary():
    return get_summary()


@app.get("/api/monitor/settings")
def api_get_monitor_settings():
    return get_monitor_settings()


@app.put("/api/monitor/settings")
def api_update_monitor_settings(payload: MonitorSettingsPayload):
    try:
        return update_monitor_settings(
            scheduler_enabled=payload.scheduler_enabled,
            ping_interval_seconds=payload.ping_interval_seconds,
            ssh_interval_seconds=payload.ssh_interval_seconds,
            http_interval_seconds=payload.http_interval_seconds,
            xui_interval_seconds=payload.xui_interval_seconds,
            ping_timeout_seconds=payload.ping_timeout_seconds,
            tcp_timeout_seconds=payload.tcp_timeout_seconds,
            http_timeout_seconds=payload.http_timeout_seconds,
            xui_timeout_seconds=payload.xui_timeout_seconds,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/probes/history")
def api_probe_history(
    limit: int = Query(default=50, ge=1, le=500),
    server_id: int | None = Query(default=None),
    probe_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
):
    return list_probe_history(limit=limit, server_id=server_id, probe_type=probe_type, source=source)


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
            console_3xui_url=payload.console_3xui_url,
            subscription_3xui_url=payload.subscription_3xui_url,
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
            console_3xui_url=payload.console_3xui_url,
            subscription_3xui_url=payload.subscription_3xui_url,
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


@app.get("/api/alerts/settings")
def api_get_alert_settings():
    settings = get_alert_settings()
    settings.update(_channel_status())
    return settings


@app.put("/api/alerts/settings")
def api_update_alert_settings(payload: AlertSettingsPayload):
    try:
        row = update_alert_settings(
            notifications_enabled=payload.notifications_enabled,
            notify_on_new_alert=payload.notify_on_new_alert,
            notify_on_resolved=payload.notify_on_resolved,
            stale_alert_enabled=payload.stale_alert_enabled,
            stale_after_seconds=payload.stale_after_seconds,
            reminder_interval_seconds=payload.reminder_interval_seconds,
        )
        row.update(_channel_status())
        return row
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/alerts/deliveries")
def api_list_alert_deliveries(limit: int = Query(default=50, ge=1, le=500)):
    return list_alert_delivery_log(limit=limit)


@app.post("/api/alerts/test")
def api_send_test_alert():
    payload = {
        "id": None,
        "server_id": None,
        "alert_type": "test_notification",
        "severity": "info",
        "message": "Тестовое уведомление из панели ServerOrchestration.",
    }
    return _dispatch_alert_notification(payload, "test", "test-panel", APP_PUBLIC_BASE_URL, get_alert_settings())


@app.get("/api/probes/ping/diagnostics")
def api_ping_diagnostics():
    return get_ping_diagnostics()


@app.post("/api/probes/ping/run")
def api_run_ping_probe(payload: PingProbeRequest):
    return _execute_ping_batch(timeout_seconds=payload.timeout_seconds, source="manual")


@app.post("/api/probes/ssh/run")
def api_run_ssh_probe(payload: ConnectivityProbeRequest):
    return _execute_ssh_batch(timeout_seconds=payload.tcp_timeout_seconds, source="manual")


@app.post("/api/probes/http/run")
def api_run_http_probe(payload: ConnectivityProbeRequest):
    http = _execute_http_batch(timeout_seconds=payload.http_timeout_seconds, source="manual")
    xui = _execute_xui_batch(timeout_seconds=payload.xui_timeout_seconds, source="manual")
    return {
        "processed": http["processed"],
        "ok": http["ok"],
        "failed": http["failed"],
        "skipped": http["skipped"],
        "xui_processed": xui["processed"],
        "xui_ok": xui["ok"],
        "xui_failed": xui["failed"],
        "xui_skipped": xui["skipped"],
        "errors": (http.get("errors") or [])[:5] + (xui.get("errors") or [])[:5],
    }


@app.post("/api/probes/connectivity/run")
def api_run_connectivity_probe(payload: ConnectivityProbeRequest):
    ping_result = _execute_ping_batch(timeout_seconds=min(payload.tcp_timeout_seconds, 10), source="manual")
    ssh_result = _execute_ssh_batch(timeout_seconds=payload.tcp_timeout_seconds, source="manual")
    http_result = _execute_http_batch(timeout_seconds=payload.http_timeout_seconds, source="manual")
    xui_result = _execute_xui_batch(timeout_seconds=payload.xui_timeout_seconds, source="manual")
    return {
        "ping": ping_result,
        "ssh": ssh_result,
        "http": {**http_result, "xui_processed": xui_result["processed"], "xui_ok": xui_result["ok"], "xui_failed": xui_result["failed"], "xui_skipped": xui_result["skipped"], "errors": (http_result.get("errors") or [])[:5] + (xui_result.get("errors") or [])[:5]},
        "xui": xui_result,
    }
