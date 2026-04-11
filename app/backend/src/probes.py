import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any

PING_LATENCY_RE = re.compile(r"time[=<](?P<latency>[0-9]+(?:\.[0-9]+)?)")
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "close",
}


def run_ping(host: str, timeout_seconds: int = 2) -> dict[str, Any]:
    cmd = ["ping", "-c", "1", "-W", str(timeout_seconds), host]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 2,
            check=False,
        )
    except FileNotFoundError:
        return {"ok": False, "latency_ms": None, "error": "ping binary not found in container", "stdout": "", "stderr": "", "returncode": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "latency_ms": None, "error": f"ping timeout after {timeout_seconds}s", "stdout": "", "stderr": "", "returncode": None}

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    latency_ms = None
    match = PING_LATENCY_RE.search(stdout)
    if match:
        latency_ms = int(round(float(match.group("latency"))))

    ok = completed.returncode == 0
    error = None if ok else (stderr.strip() or stdout.strip() or f"ping failed with rc={completed.returncode}")
    return {"ok": ok, "latency_ms": latency_ms, "error": error, "stdout": stdout, "stderr": stderr, "returncode": completed.returncode}


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
