import re
import shutil
import socket
import ssl
import subprocess
from datetime import datetime, timezone
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from typing import Any

PING_LATENCY_RE = re.compile(r"time\s*[=<]?\s*(?P<latency>[0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "close",
}


def _squash_probe_text(*parts: str, limit: int = 500) -> str:
    combined = " | ".join(part.strip() for part in parts if part and part.strip())
    combined = re.sub(r"\s+", " ", combined).strip()
    if len(combined) <= limit:
        return combined
    return combined[: limit - 1] + "…"


def _normalize_ping_error(stdout: str, stderr: str, returncode: int | None) -> str:
    raw = _squash_probe_text(stderr, stdout)
    if not raw:
        raw = f"ping failed with rc={returncode}"

    lowered = raw.lower()
    if "operation not permitted" in lowered or "permission denied" in lowered:
        return f"{raw} (контейнеру нужен NET_RAW для ICMP ping)"
    if "not found" in lowered or "no such file" in lowered:
        return f"{raw} (в контейнере отсутствует системный ping)"
    return raw


def run_ping(host: str, timeout_seconds: int = 2) -> dict[str, Any]:
    ping_path = shutil.which("ping")
    if not ping_path:
        return {
            "ok": False,
            "latency_ms": None,
            "error": "ping binary not found in container",
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "command": None,
        }

    cmd = [ping_path, "-c", "1", "-W", str(timeout_seconds), host]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 2,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "latency_ms": None,
            "error": "ping binary not found in container",
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "latency_ms": None,
            "error": f"ping timeout after {timeout_seconds}s",
            "stdout": "",
            "stderr": "",
            "returncode": None,
            "command": " ".join(cmd),
        }

    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    latency_ms = None
    match = PING_LATENCY_RE.search(stdout) or PING_LATENCY_RE.search(stderr)
    if match:
        latency_raw = match.group("latency").replace(",", ".")
        latency_ms = int(round(float(latency_raw)))

    ok = completed.returncode == 0
    if ok and latency_ms is None:
        latency_ms = elapsed_ms

    error = None if ok else _normalize_ping_error(stdout, stderr, completed.returncode)
    return {
        "ok": ok,
        "latency_ms": latency_ms,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": completed.returncode,
        "command": " ".join(cmd),
    }


def get_ping_diagnostics(timeout_seconds: int = 1) -> dict[str, Any]:
    ping_path = shutil.which("ping")
    diagnostics: dict[str, Any] = {
        "binary_found": bool(ping_path),
        "binary_path": ping_path,
        "capability_hint": "Для non-root ICMP ping контейнеру нужен cap_add: NET_RAW; в image дополнительно выставляется setcap для ping.",
    }
    if not ping_path:
        diagnostics["self_test"] = {
            "ok": False,
            "latency_ms": None,
            "error": "ping binary not found in container",
        }
        return diagnostics

    diagnostics["self_test"] = run_ping("127.0.0.1", timeout_seconds=timeout_seconds)
    return diagnostics


def run_tcp_connect(host: str, port: int, timeout_seconds: int = 3) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_seconds):
            latency_ms = int(round((time.perf_counter() - started) * 1000))
            return {"ok": True, "latency_ms": latency_ms, "error": None}
    except Exception as exc:
        return {"ok": False, "latency_ms": None, "error": str(exc)}


def run_http_check(url: str, timeout_seconds: int = 5) -> dict[str, Any]:
    if not url:
        return {"ok": None, "status_code": None, "response_ms": None, "error": "web_url not configured"}

    request = urllib.request.Request(url=url, headers=BROWSER_HEADERS, method="GET")
    context = ssl._create_unverified_context()
    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            elapsed_ms = int(round((time.perf_counter() - started) * 1000))
            status_code = getattr(response, "status", None) or response.getcode()
            ok = status_code is not None and status_code < 500 and status_code != 404
            return {"ok": ok, "status_code": status_code, "response_ms": elapsed_ms, "error": None if ok else f"HTTP {status_code}"}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int(round((time.perf_counter() - started) * 1000))
        status_code = exc.code
        ok = status_code < 500 and status_code != 404
        return {"ok": ok, "status_code": status_code, "response_ms": elapsed_ms, "error": None if ok else f"HTTP {status_code}"}
    except Exception as exc:
        return {"ok": False, "status_code": None, "response_ms": None, "error": str(exc)}



def probe_ssl_certificate(url: str | None, timeout_seconds: int = 5) -> dict[str, Any]:
    if not url:
        return {"ok": False, "error": "subscription_3xui_url is not configured"}

    raw = str(url).strip()
    if not raw:
        return {"ok": False, "error": "subscription_3xui_url is empty"}

    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = parsed.hostname
    scheme = (parsed.scheme or "https").lower()
    port = parsed.port or (443 if scheme == "https" else 443)

    if not host:
        return {"ok": False, "error": "invalid subscription URL"}
    if scheme != "https":
        return {"ok": False, "error": f"SSL probe requires https URL, got {scheme}"}

    started = time.perf_counter()
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert() or {}
        latency_ms = int((time.perf_counter() - started) * 1000)
        not_after = cert.get("notAfter")
        expires_at = None
        days_remaining = None
        if not_after:
            expires_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            expires_at = expires_dt.isoformat()
            days_remaining = max(int((expires_dt - datetime.now(timezone.utc)).total_seconds() // 86400), -1)
        subject_parts = []
        for item in cert.get("subject", ()):
            if isinstance(item, tuple):
                for key, value in item:
                    subject_parts.append(f"{key}={value}")
        return {
            "ok": True,
            "latency_ms": latency_ms,
            "host": host,
            "port": port,
            "scheme": scheme,
            "expires_at": expires_at,
            "days_remaining": days_remaining,
            "subject": ", ".join(subject_parts) if subject_parts else None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "host": host,
            "port": port,
            "scheme": scheme,
            "error": str(exc),
        }
