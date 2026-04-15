import base64
import html
from html.parser import HTMLParser
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
from urllib.parse import unquote, urlparse

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

SUBSCRIPTION_URI_RE = re.compile(r'''(?P<uri>(?:vmess|vless|trojan|ss|ssr|hysteria|hysteria2|hy2|tuic|wireguard)://[^\s"'<>]+)''', re.IGNORECASE)
BASE64_BLOB_RE = re.compile(r"[A-Za-z0-9+/_-]{120,}={0,2}")


_HTML_LABEL_ALIASES = {
    "id подписки": "subscription_id",
    "subscription id": "subscription_id",
    "статус": "profile_status",
    "status": "profile_status",
    "загружено": "downloaded_bytes",
    "download": "downloaded_bytes",
    "отправлено": "uploaded_bytes",
    "upload": "uploaded_bytes",
    "использование": "used_bytes",
    "usage": "used_bytes",
    "общий лимит": "total_bytes",
    "total": "total_bytes",
    "остаток": "remaining_bytes",
    "remaining": "remaining_bytes",
    "был(а) в сети": "last_online_text",
    "last online": "last_online_text",
    "срок действия": "expires_text",
    "expiry": "expires_text",
    "expires": "expires_text",
}


def _normalize_html_label(value: str) -> str:
    normalized = (value or '').strip().casefold()
    return re.sub(r'\s+', ' ', normalized)


def _parse_data_size(value: str | None) -> int | None:
    text = (value or '').strip()
    if not text:
        return None
    normalized = text.replace(' ', '').replace(',', '.').upper()
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(B|KB|KIB|MB|MIB|GB|GIB|TB|TIB|PB|PIB)?', normalized)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or 'B').upper()
    factors = {
        'B': 1,
        'KB': 1000**1, 'MB': 1000**2, 'GB': 1000**3, 'TB': 1000**4, 'PB': 1000**5,
        'KIB': 1024**1, 'MIB': 1024**2, 'GIB': 1024**3, 'TIB': 1024**4, 'PIB': 1024**5,
    }
    factor = factors.get(unit)
    if factor is None:
        return None
    return int(number * factor)


def _strip_html_fragment(value: str) -> str:
    text = re.sub(r'(?is)<br\s*/?>', '\n', value or '')
    text = re.sub(r'(?is)<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_html_text_lines(source: str) -> list[str]:
    text = re.sub(r'(?is)<(script|style|noscript).*?>.*?</\1>', ' ', source)
    text = re.sub(r'(?is)<br\s*/?>', '\n', text)
    text = re.sub(r'(?is)</(tr|td|th|div|p|section|article|li|ul|ol|table|tbody|thead|tfoot|h[1-6])>', '\n', text)
    text = re.sub(r'(?is)<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = text.replace('\xa0', ' ')
    lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r'\s+', ' ', raw).strip()
        if line:
            lines.append(line)
    return lines




class _SubscriptionHTMLExtractor(HTMLParser):
    _BLOCK_TAGS = {
        "p", "div", "section", "article", "header", "footer", "aside",
        "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr",
        "th", "td", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
        "span", "label", "small", "strong", "b", "em", "i", "a",
    }
    _CELL_TAGS = {"th", "td"}
    _SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._line_parts: list[str] = []
        self._cell_parts: list[str] = []
        self.lines: list[str] = []
        self.cells: list[str] = []

    def _flush_line(self) -> None:
        if not self._line_parts:
            return
        value = _strip_html_fragment(" ".join(self._line_parts))
        if value:
            self.lines.append(value)
        self._line_parts = []

    def _flush_cell(self) -> None:
        if not self._cell_parts:
            return
        value = _strip_html_fragment(" ".join(self._cell_parts))
        if value:
            self.cells.append(value)
        self._cell_parts = []

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = (tag or "").lower()
        if lowered in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if lowered in self._CELL_TAGS:
            self._flush_cell()
            self._flush_line()
        elif lowered in self._BLOCK_TAGS:
            self._flush_line()

    def handle_endtag(self, tag: str) -> None:
        lowered = (tag or "").lower()
        if lowered in self._SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if lowered in self._CELL_TAGS:
            self._flush_cell()
            self._flush_line()
        elif lowered in self._BLOCK_TAGS:
            self._flush_line()

    def handle_data(self, data: str) -> None:
        if self._skip_depth or not data:
            return
        value = _strip_html_fragment(data)
        if not value:
            return
        self._line_parts.append(value)
        self._cell_parts.append(value)

    def close(self) -> None:
        super().close()
        self._flush_cell()
        self._flush_line()


_HTML_FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "subscription_id": ("id подписки", "subscription id", "client id", "sub id", "email"),
    "profile_status": ("статус", "status", "state"),
    "downloaded_bytes": ("загружено", "downloaded", "downloaded bytes", "download", "down", "downloadbyte"),
    "uploaded_bytes": ("отправлено", "uploaded", "uploaded bytes", "upload", "up", "uploadbyte"),
    "used_bytes": ("использование", "usage", "used", "used traffic", "traffic used", "usedbyte"),
    "total_bytes": ("общий лимит", "total limit", "лимит", "total", "traffic total", "totalbyte"),
    "remaining_bytes": ("остаток", "remaining", "remain", "remaining traffic", "remained"),
    "last_seen_text": ("был(а) в сети", "был в сети", "last online", "last seen", "online at", "last_online", "lastonline"),
    "expires_text": ("срок действия", "expiry", "expires", "expire", "expired at"),
    "profile_title": ("информация о подписке", "subscription info", "subscription information"),
}


def _match_html_field(label: str | None) -> str | None:
    normalized = _normalize_html_label(label)
    if not normalized:
        return None
    alias = _HTML_LABEL_ALIASES.get(normalized)
    if alias:
        return alias
    for field, names in _HTML_FIELD_PATTERNS.items():
        for name in names:
            name_norm = _normalize_html_label(name)
            if normalized == name_norm or normalized.endswith(name_norm) or normalized.startswith(name_norm + " "):
                return field
    return None


def _looks_like_html_or_code(value: str) -> bool:
    lowered = (value or "").casefold()
    if not lowered:
        return True
    return any(
        token in lowered
        for token in (
            "<!doctype",
            "<html",
            "</",
            "window.",
            "document.",
            "function(",
            "const ",
            "let ",
            "var ",
            "subscription.title",
        )
    )


def _is_profile_label_value(value: str) -> bool:
    normalized = _normalize_html_label(value)
    if not normalized:
        return False
    return _match_html_field(normalized) is not None


def _apply_html_profile_value(parsed: dict[str, Any], field: str, value: str | None) -> None:
    raw_value = (value or "").strip()
    cleaned = _strip_html_fragment(raw_value)
    if not cleaned:
        return
    if len(cleaned) > 180:
        return
    if _looks_like_html_or_code(raw_value) or _looks_like_html_or_code(cleaned):
        return
    if field == "profile_title":
        if _is_profile_label_value(cleaned):
            return
        lowered = cleaned.casefold()
        if lowered in {"subscription information", "subscription info", "информация о подписке"}:
            return
    parsed[field] = cleaned


def _extract_profile_from_lines(lines: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    cleaned = [_strip_html_fragment(line) for line in lines if _strip_html_fragment(line)]
    for idx, line in enumerate(cleaned):
        field = _match_html_field(line)
        if field:
            next_value = cleaned[idx + 1] if idx + 1 < len(cleaned) else ""
            if next_value and not _match_html_field(next_value):
                _apply_html_profile_value(parsed, field, next_value)
            continue

        separator_match = re.match(r"^(.+?)\s*[:：]\s*(.+)$", line)
        if separator_match:
            field = _match_html_field(separator_match.group(1))
            if field:
                _apply_html_profile_value(parsed, field, separator_match.group(2))
    return parsed


def _extract_profile_from_cells(cells: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    cleaned = [_strip_html_fragment(cell) for cell in cells if _strip_html_fragment(cell)]
    for idx in range(len(cleaned) - 1):
        field = _match_html_field(cleaned[idx])
        if field:
            next_value = cleaned[idx + 1]
            if not _match_html_field(next_value):
                _apply_html_profile_value(parsed, field, next_value)
    return parsed


def _extract_profile_from_blob(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    normalized_blob = _normalize_html_label(text)
    if not normalized_blob:
        return parsed
    all_aliases: list[str] = []
    for names in _HTML_FIELD_PATTERNS.values():
        all_aliases.extend(_normalize_html_label(name) for name in names)
    boundary = "|".join(sorted({re.escape(alias) for alias in all_aliases if alias}, key=len, reverse=True))
    if not boundary:
        return parsed
    for field, names in _HTML_FIELD_PATTERNS.items():
        pattern = "|".join(sorted({re.escape(_normalize_html_label(name)) for name in names}, key=len, reverse=True))
        if not pattern:
            continue
        match = re.search(
            rf"(?:^|[\s|•·\[\](),;])(?:{pattern})\s*[:：-]?\s*(.+?)(?=(?:^|[\s|•·\[\](),;])(?:{boundary})\s*[:：-]?|$)",
            normalized_blob,
            re.IGNORECASE,
        )
        if match:
            _apply_html_profile_value(parsed, field, match.group(1))
    return parsed


def _search_script_value(raw: str, *aliases: str) -> str | None:
    for alias in aliases:
        escaped = re.escape(alias)
        match = re.search(
            rf'(?:["\'])?{escaped}(?:["\'])?\s*[:=]\s*(?:(["\'])(.*?)\1|([^,\n;}}{{<]+))',
            raw,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            continue
        value = match.group(2) or match.group(3)
        if value:
            return value.strip()
    return None


def _extract_profile_from_script(html_source: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    raw = html_source or ""

    field_aliases: dict[str, tuple[str, ...]] = {
        "downloaded_bytes": ("download", "down", "downloaded", "downloadByte"),
        "uploaded_bytes": ("upload", "up", "uploaded", "uploadByte"),
        "used_bytes": ("usage", "used", "usedTraffic", "trafficUsed", "usedByte"),
        "total_bytes": ("total", "totalTraffic", "limit", "trafficTotal", "totalByte"),
        "remaining_bytes": ("remaining", "remainingTraffic", "remain", "remained"),
        "expires_text": ("expire", "expiry", "expires", "expiryTime", "expireDate"),
        "profile_status": ("status", "state"),
        "subscription_id": ("email", "subscriptionId", "subId", "clientId", "sId"),
        "last_seen_text": ("lastSeen", "lastOnline", "onlineAt"),
        "profile_title": ("profileTitle",),
    }

    for field, aliases in field_aliases.items():
        value = _search_script_value(raw, *aliases)
        if value:
            _apply_html_profile_value(parsed, field, value)

    header_like = re.search(
        r'(?:subscription-userinfo|subscriptionUserinfo)\s*[:=]\s*([\'\"])([^\'\"]+)\1',
        raw,
        re.IGNORECASE,
    )
    if header_like:
        for part in header_like.group(2).split(';'):
            if '=' not in part:
                continue
            key, value = part.split('=', 1)
            key = key.strip().lower()
            value = value.strip()
            if key == 'upload':
                _apply_html_profile_value(parsed, 'uploaded_bytes', value)
            elif key == 'download':
                _apply_html_profile_value(parsed, 'downloaded_bytes', value)
            elif key == 'total':
                _apply_html_profile_value(parsed, 'total_bytes', value)
            elif key == 'expire':
                _apply_html_profile_value(parsed, 'expires_text', value)
    return parsed


def _parse_subscription_profile_from_html(source: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    raw_html = source or ""
    if not raw_html:
        return parsed

    row_pattern = re.compile(r'(?is)<tr[^>]*>\s*(.*?)\s*</tr>')
    cell_pattern = re.compile(r'(?is)<t[dh][^>]*>\s*(.*?)\s*</t[dh]>')
    for row_match in row_pattern.finditer(raw_html):
        row_html = row_match.group(1)
        cells = [_strip_html_fragment(cell) for cell in cell_pattern.findall(row_html)]
        if len(cells) < 2:
            continue
        field = _match_html_field(cells[0])
        if field:
            _apply_html_profile_value(parsed, field, cells[1])

    extractor = _SubscriptionHTMLExtractor()
    try:
        extractor.feed(raw_html)
        extractor.close()
    except Exception:
        pass

    plain_parts: list[str] = []
    if extractor.lines:
        plain_parts.extend(extractor.lines)
    if extractor.cells:
        plain_parts.extend(extractor.cells)
    plain_text = "\n".join(plain_parts) if plain_parts else "\n".join(_extract_html_text_lines(raw_html))

    for source_map in (
        _extract_profile_from_lines(extractor.lines),
        _extract_profile_from_cells(extractor.cells),
        _extract_profile_from_blob(plain_text),
        _extract_profile_from_script(raw_html),
    ):
        for key, value in source_map.items():
            if key not in parsed and value:
                parsed[key] = value

    if not parsed:
        return {}

    for key in ('downloaded_bytes', 'uploaded_bytes', 'used_bytes', 'total_bytes', 'remaining_bytes'):
        if key in parsed:
            parsed[f'{key}_text'] = str(parsed[key])
            size_value = _parse_data_size(str(parsed[key]))
            if size_value is not None:
                parsed[key] = size_value

    expires_text = str(parsed.get('expires_text') or '').strip()
    if expires_text:
        lowered = expires_text.casefold()
        if any(token in lowered for token in ('бесср', 'unlimited', 'never', '∞')):
            parsed['expires_unlimited'] = True
        else:
            parsed['expires_unlimited'] = False

    if 'used_bytes' not in parsed:
        down = parsed.get('downloaded_bytes')
        up = parsed.get('uploaded_bytes')
        if isinstance(down, int) and isinstance(up, int):
            parsed['used_bytes'] = down + up
    if 'remaining_bytes' in parsed and 'total_bytes' in parsed and 'used_bytes' not in parsed:
        total = parsed.get('total_bytes')
        remaining = parsed.get('remaining_bytes')
        if isinstance(total, int) and isinstance(remaining, int):
            parsed['used_bytes'] = max(total - remaining, 0)
    if 'total_bytes' in parsed and 'used_bytes' in parsed and 'remaining_bytes' not in parsed:
        total = parsed.get('total_bytes')
        used = parsed.get('used_bytes')
        if isinstance(total, int) and isinstance(used, int):
            parsed['remaining_bytes'] = max(total - used, 0)

    return parsed


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


def _decode_base64_subscription_candidate(value: str) -> tuple[bool, dict, str | None]:
    compact = "".join((value or "").split())
    if not compact:
        return False, {"encoding": "empty", "entries": 0}, None

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
            entry_types = sorted({line.split("://", 1)[0].lower() for line in decoded_text.splitlines() if "://" in line})
            return True, {
                "encoding": "base64",
                "entries": decoded_entries,
                "decoded_bytes": len(decoded_bytes),
                "entry_types": entry_types,
            }, None

    return False, {"encoding": "base64-invalid", "entries": 0}, None


def _extract_subscription_payload_from_html(text: str) -> tuple[bool, dict, str | None]:
    source = html.unescape(text or "").strip()
    if not source:
        return False, {"encoding": "html", "entries": 0}, "subscription html page is empty"

    variants = [source]
    decoded_once = unquote(source)
    if decoded_once != source:
        variants.append(decoded_once)

    merged_profile_details: dict[str, Any] = {}
    for variant in variants:
        profile_details = _parse_subscription_profile_from_html(variant)
        if profile_details:
            merged_profile_details.update(profile_details)

    discovered_uris: list[str] = []
    entry_types: set[str] = set()
    for variant in variants:
        for match in SUBSCRIPTION_URI_RE.finditer(variant):
            uri = match.group("uri").strip().rstrip("'\"<>)],;")
            if not uri:
                continue
            discovered_uris.append(uri)
            entry_types.add(uri.split("://", 1)[0].lower())
    unique_uris = list(dict.fromkeys(discovered_uris))
    if unique_uris:
        return True, {
            "encoding": "html-embedded",
            "entries": len(unique_uris),
            "entry_types": sorted(entry_types),
            "html_embedded": True,
            **merged_profile_details,
        }, None

    tested_blobs: set[str] = set()
    for variant in variants:
        for blob in BASE64_BLOB_RE.findall(variant):
            if blob in tested_blobs:
                continue
            tested_blobs.add(blob)
            ok_blob, blob_details, _blob_error = _decode_base64_subscription_candidate(blob)
            if ok_blob:
                details = dict(blob_details)
                details["encoding"] = "html-base64"
                details["html_embedded"] = True
                details.update({k: v for k, v in merged_profile_details.items() if k not in details})
                return True, details, None

    if merged_profile_details:
        details = {
            "encoding": "html-profile",
            "entries": 0,
            "html_embedded": True,
            **merged_profile_details,
        }
        return True, details, None

    return False, {"encoding": "html", "entries": 0}, "subscription endpoint returned HTML page without embedded share data"


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
        ok_base64, base64_details, _base64_error = _decode_base64_subscription_candidate(compact)
        if ok_base64:
            details = dict(base64_details)
            details["payload_bytes"] = len(raw_body)
            return True, details, None

    lowered = text.lower()
    if "<html" in lowered or "<!doctype html" in lowered:
        ok_html, html_details, html_error = _extract_subscription_payload_from_html(text)
        html_details["payload_bytes"] = len(raw_body)
        return ok_html, html_details, html_error
    return False, {"encoding": "unknown", "entries": 0, "payload_bytes": len(raw_body)}, "subscription payload is not a valid 3x-ui share list"


def fetch_url(url: str | None, timeout_seconds: int = 5, *, verify_tls: bool = True) -> tuple[bool, int | None, int | None, str | None, bytes, str | None, dict[str, str]]:
    url = (url or "").strip()
    if not url:
        return False, None, None, "url not configured", b"", None, {}

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
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            return status is not None and int(status) < 400, int(status) if status is not None else None, latency_ms, None, body, final_url, headers
    except urllib.error.HTTPError as exc:
        latency_ms = max(1, int(round((time.perf_counter() - started) * 1000)))
        try:
            body = exc.read()
        except Exception:
            body = b""
        headers = {str(k).lower(): str(v) for k, v in getattr(exc, "headers", {}).items()} if getattr(exc, "headers", None) else {}
        return False, exc.code, latency_ms, f"HTTP {exc.code}", body, url, headers
    except Exception as exc:
        latency_ms = max(1, int(round((time.perf_counter() - started) * 1000)))
        return False, None, latency_ms, str(exc), b"", url, {}


def run_http_check(url: str | None, timeout_seconds: int = 5, *, verify_tls: bool = True) -> dict[str, Any]:
    ok, status_code, response_ms, error, _body, _final_url, _headers = fetch_url(url, timeout_seconds=timeout_seconds, verify_tls=verify_tls)
    return {
        "ok": ok,
        "status_code": status_code,
        "response_ms": response_ms,
        "error": error,
    }


def run_3xui_subscription_check(url: str | None, timeout_seconds: int = 5) -> dict[str, Any]:
    ok, status_code, response_ms, error, body, final_url, headers = fetch_url(url, timeout_seconds=timeout_seconds, verify_tls=False)
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
    subscription_userinfo = headers.get("subscription-userinfo") or headers.get("subscription_userinfo")
    if subscription_userinfo:
        details["subscription_userinfo"] = subscription_userinfo
        parsed_userinfo = {}
        for part in subscription_userinfo.split(';'):
            if '=' not in part:
                continue
            key, value = part.split('=', 1)
            key = key.strip().lower().replace('-', '_')
            value = value.strip()
            if not key or not value:
                continue
            try:
                parsed_userinfo[key] = int(value)
            except ValueError:
                parsed_userinfo[key] = value
        if parsed_userinfo:
            details["subscription_userinfo_parsed"] = parsed_userinfo
            upload = parsed_userinfo.get("upload")
            download = parsed_userinfo.get("download")
            total = parsed_userinfo.get("total")
            expire = parsed_userinfo.get("expire")
            if isinstance(upload, int):
                details["upload_bytes"] = upload
            if isinstance(download, int):
                details["download_bytes"] = download
            if isinstance(upload, int) or isinstance(download, int):
                details["used_bytes"] = int(upload or 0) + int(download or 0)
            if isinstance(total, int):
                details["total_bytes"] = total
                if details.get("used_bytes") is not None:
                    details["remaining_bytes"] = max(total - int(details["used_bytes"]), 0)
            if isinstance(expire, int) and expire > 0:
                try:
                    expire_dt = datetime.fromtimestamp(expire, tz=timezone.utc)
                    details["expires_at"] = expire_dt.isoformat()
                    details["days_remaining"] = int((expire_dt - datetime.now(timezone.utc)).total_seconds() // 86400)
                except Exception:
                    pass
    profile_title = headers.get("profile-title") or headers.get("profile_title")
    if profile_title:
        details["profile_title"] = profile_title
    support_url = headers.get("support-url") or headers.get("support_url")
    if support_url:
        details["support_url"] = support_url
    profile_web_page_url = headers.get("profile-web-page-url") or headers.get("profile_web_page_url")
    if profile_web_page_url:
        details["profile_web_page_url"] = profile_web_page_url

    header_has_subscription_info = any(
        key in details
        for key in ("used_bytes", "total_bytes", "remaining_bytes", "expires_at", "days_remaining")
    )
    if not payload_ok and header_has_subscription_info and str(details.get("encoding") or "").startswith("html"):
        payload_ok = True
        details["payload_warning"] = payload_error
        payload_error = None
        details["encoding"] = "html+headers"

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
