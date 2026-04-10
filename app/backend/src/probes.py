import re
import subprocess
from typing import Any

PING_LATENCY_RE = re.compile(r"time[=<](?P<latency>[0-9]+(?:\.[0-9]+)?)")


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
        return {
            "ok": False,
            "latency_ms": None,
            "error": "ping binary not found in container",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "latency_ms": None,
            "error": f"ping timeout after {timeout_seconds}s",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    latency_ms = None
    match = PING_LATENCY_RE.search(stdout)
    if match:
        latency_ms = int(round(float(match.group("latency"))))

    ok = completed.returncode == 0
    error = None if ok else (stderr.strip() or stdout.strip() or f"ping failed with rc={completed.returncode}")

    return {
        "ok": ok,
        "latency_ms": latency_ms,
        "error": error,
        "stdout": stdout,
        "stderr": stderr,
        "returncode": completed.returncode,
    }
