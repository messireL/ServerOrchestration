import base64
import ipaddress
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

PING_LATENCY_RE = re.compile(r"time\s*[=<]?\s*(?P<latency>[0-9]+(?:[.,][0-9]+)?)", re.IGNORECASE)
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
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


def _target_url(value: str | dict | None, preferred_fields: tuple[str, ...] = ()) -> str | None:
    if isinstance(value, dict):
        for field in preferred_fields:
            candidate = (value.get(field) or "").strip()
            if candidate:
                return candidate
        for field in ("subscription_3xui_url", "web_url", "console_3xui_url"):
            candidate = (value.get(field) or "").strip()
            if candidate:
                return candidate
        return None
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def _normalize_cert_name(items) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for group in items or ():
        if not isinstance(group, (tuple, list)):
            continue
        for item in group:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                normalized.append((str(item[0]), str(item[1])))
    return tuple(normalized)


def _name_value(items, key: str) -> str | None:
    key = key.lower()
    for item_key, item_value in _normalize_cert_name(items):
        if item_key.lower() == key:
            return item_value
    return None


def _parse_cert_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    normalized = " ".join(str(raw).split())
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%Y%m%d%H%M%SZ"):
        try:
            parsed = datetime.strptime(normalized, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _decode_certificate(binary_cert: bytes) -> dict:
    pem = ssl.DER_cert_to_PEM_cert(binary_cert)
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=True) as fh:
        fh.write(pem)
        fh.flush()
        return ssl._ssl._test_decode_cert(fh.name)


def _dns_pattern_matches(pattern: str, hostname: str) -> bool:
    pattern = (pattern or '').strip().lower()
    hostname = (hostname or '').strip().lower()
    if not pattern or not hostname:
        return False
    if '*' not in pattern:
        return pattern == hostname
    if not pattern.startswith('*.'):
        return False
    suffix = pattern[1:]
    if not hostname.endswith(suffix):
        return False
    host_labels = hostname.split('.')
    suffix_labels = suffix.lstrip('.').split('.')
    return len(host_labels) == len(suffix_labels) + 1


def _hostname_matches(cert_dict: dict, hostname: str) -> tuple[bool, str | None]:
    if not hostname:
        return True, None

    normalized_host = hostname.strip()
    try:
        host_ip = ipaddress.ip_address(normalized_host)
    except ValueError:
        host_ip = None

    san_entries = cert_dict.get('subjectAltName') or ()
    dns_names: list[str] = []
    ip_names: list[str] = []
    for kind, value in san_entries:
        if not value:
            continue
        kind_normalized = str(kind).strip().lower()
        if kind_normalized == 'dns':
            dns_names.append(str(value).strip())
        elif kind_normalized in {'ip address', 'ip'}:
            ip_names.append(str(value).strip())

    common_name = _name_value(cert_dict.get('subject') or (), 'commonName')
    if common_name and not dns_names and not ip_names:
        dns_names.append(common_name)

    if host_ip is not None:
        for candidate in ip_names + dns_names:
            try:
                if ipaddress.ip_address(candidate.strip()) == host_ip:
                    return True, None
            except ValueError:
                if candidate.strip().lower() == normalized_host.lower():
                    return True, None
        expected = ', '.join(ip_names + dns_names) or 'SAN/CN missing'
        return False, f'certificate does not match IP {normalized_host} (expected: {expected})'

    for candidate in dns_names:
        if _dns_pattern_matches(candidate, normalized_host):
            return True, None

    expected = ', '.join(dns_names) or common_name or 'SAN/CN missing'
    return False, f'certificate does not match hostname {normalized_host} (expected: {expected})'


def _looks_like_subscription_payload(text: str) -> tuple[bool, int]:
    if not text:
        return False, 0
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
    schemes = (
        "vmess://",
        "vless://",
        "trojan://",
        "ss://",
        "ssr://",
        "hysteria://",
        "hysteria2://",
        "hy2://",
        "tuic://",
        "wireguard://",
    )
    matches = [line for line in lines if line.lower().startswith(schemes)]
    return bool(matches), len(matches)


def _decode_subscription_payload(raw_body: bytes) -> tuple[bool, dict, str | None]:
    text = raw_body.decode("utf-8", errors="ignore").strip()
    if not text:
        return False, {"encoding": "empty", "entries": 0}, "subscription payload is empty"

    ok_plain, plain_entries = _looks_like_subscription_payload(text)
    if ok_plain:
        return True, {
            "encoding": "plain",
            "entries": plain_entries,
            "payload_bytes": len(raw_body),
        }, None

    compact = "".join(text.split())
    if compact:
        candidates: list[str] = []
        candidates.append(compact + ("=" * (-len(compact) % 4)))
        if "-" in compact or "_" in compact:
            normalized = compact.replace("-", "+").replace("_", "/")
            candidates.append(normalized + ("=" * (-len(normalized) % 4)))
        for encoded in candidates:
            try:
                decoded_bytes = base64.b64decode(encoded, validate=False)
            except Exception:
                continue
            decoded_text = decoded_bytes.decode("utf-8", errors="ignore").strip()
            ok_decoded, decoded_entries = _looks_like_subscription_payload(decoded_text)
            if ok_decoded:
                return True, {
                    "encoding": "base64",
                    "entries": decoded_entries,
                    "payload_bytes": len(raw_body),
                    "decoded_bytes": len(decoded_bytes),
                }, None

    lowered = text.lower()
    if "<html" in lowered or "<!doctype html" in lowered:
        return False, {"encoding": "html", "entries": 0, "payload_bytes": len(raw_body)}, "subscription endpoint returned HTML instead of subscription data"
    return False, {"encoding": "unknown", "entries": 0, "payload_bytes": len(raw_body)}, "subscription payload is not a valid 3x-ui share list"


def fetch_url(url: str | None, timeout_seconds: int = 5, *, verify_tls: bool = True) -> tuple[bool, int | None, int | None, str | None, bytes, str | None]:
    url = (url or "").strip()
    if not url:
        return False, None, None, "url not configured", b"", None

    started = time.perf_counter()
    request = urllib.request.Request(url, headers=BROWSER_HEADERS, method="GET")
    context = None
    if url.lower().startswith("https://") and not verify_tls:
        context = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            body = response.read()
            status = getattr(response, "status", None)
            latency_ms = max(1, int(round((time.perf_counter() - started) * 1000)))
            final_url = getattr(response, "geturl", lambda: url)()
            return status is not None and int(status) < 400, int(status) if status is not None else None, latency_ms, None, body, final_url
    except urllib.error.HTTPError as exc:
        latency_ms = max(1, int(round((time.perf_counter() - started) * 1000)))
        try:
            body = exc.read()
        except Exception:
            body = b""
        return False, exc.code, latency_ms, f"HTTP {exc.code}", body, url
    except Exception as exc:
        latency_ms = max(1, int(round((time.perf_counter() - started) * 1000)))
        return False, None, latency_ms, str(exc), b"", url


def run_http_check(url: str | None, timeout_seconds: int = 5, *, verify_tls: bool = True) -> dict[str, Any]:
    ok, status_code, response_ms, error, _body, _final_url = fetch_url(url, timeout_seconds=timeout_seconds, verify_tls=verify_tls)
    return {
        "ok": ok,
        "status_code": status_code,
        "response_ms": response_ms,
        "error": error,
    }


def run_3xui_subscription_check(url: str | None, timeout_seconds: int = 5) -> dict[str, Any]:
    ok, status_code, response_ms, error, body, final_url = fetch_url(url, timeout_seconds=timeout_seconds, verify_tls=False)
    details: dict[str, Any] = {
        "target_url": url,
        "final_url": final_url,
    }
    if not ok:
        details["payload_bytes"] = len(body or b"")
        return {
            "ok": False,
            "status_code": status_code,
            "response_ms": response_ms,
            "error": error,
            "details": details,
        }

    payload_ok, payload_details, payload_error = _decode_subscription_payload(body)
    details.update(payload_details)
    if payload_error:
        details["payload_error"] = payload_error
    return {
        "ok": bool(payload_ok),
        "status_code": status_code,
        "response_ms": response_ms,
        "error": payload_error,
        "details": details,
    }


def probe_ssl_certificate(url: str | dict | None, timeout_seconds: int = 5) -> dict[str, Any]:
    target_url = _target_url(url, preferred_fields=("subscription_3xui_url", "web_url", "console_3xui_url"))
    if not target_url:
        return {"ok": False, "error": "ssl target url not configured", "details": {"target_url": None}}

    parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
    host = parsed.hostname
    scheme = (parsed.scheme or "https").lower()
    port = parsed.port or (443 if scheme == "https" else 443)
    details: dict[str, Any] = {
        "target_url": target_url,
        "host": host,
        "port": port,
        "scheme": scheme,
    }
    if not host:
        return {"ok": False, "error": "invalid ssl target url", "details": details}

    started = time.perf_counter()
    try:
        context = ssl._create_unverified_context()
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                binary_cert = tls_sock.getpeercert(binary_form=True)
                details["latency_ms"] = max(1, int(round((time.perf_counter() - started) * 1000)))
        cert_dict = _decode_certificate(binary_cert)
    except Exception as exc:
        details["latency_ms"] = max(1, int(round((time.perf_counter() - started) * 1000)))
        details["probe_error"] = str(exc)
        return {"ok": False, "error": str(exc), "details": details}

    subject = cert_dict.get("subject") or ()
    issuer = cert_dict.get("issuer") or ()
    not_before = _parse_cert_time(cert_dict.get("notBefore"))
    not_after = _parse_cert_time(cert_dict.get("notAfter"))
    now = datetime.now(timezone.utc)
    hostname_ok, hostname_error = _hostname_matches(cert_dict, host)
    days_remaining = None
    if not_after is not None:
        delta = not_after - now
        days_remaining = int(delta.total_seconds() // 86400)

    details.update(
        {
            "self_signed": _normalize_cert_name(subject) == _normalize_cert_name(issuer),
            "subject_cn": _name_value(subject, "commonName"),
            "issuer_cn": _name_value(issuer, "commonName"),
            "not_before": not_before.isoformat() if not_before else None,
            "not_after": not_after.isoformat() if not_after else None,
            "days_remaining": days_remaining,
            "hostname_match": hostname_ok,
            "san": [value for _kind, value in (cert_dict.get("subjectAltName") or ())],
        }
    )
    if hostname_error:
        details["hostname_error"] = hostname_error

    if not_before and now < not_before:
        return {"ok": False, "error": f"certificate is not valid before {not_before.isoformat()}", "details": details}
    if not_after and now > not_after:
        return {"ok": False, "error": f"certificate expired at {not_after.isoformat()}", "details": details}
    if not hostname_ok:
        return {"ok": False, "error": hostname_error or "certificate hostname mismatch", "details": details}
    return {"ok": True, "error": None, "details": details}
