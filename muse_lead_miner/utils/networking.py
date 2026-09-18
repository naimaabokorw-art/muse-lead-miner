import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse
import requests


def normalize_name(value: str) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = cleaned.replace("&amp;", "&")
    return cleaned.title()


def normalize_phone(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    return digits


def normalize_url(value: str) -> str:
    if not value:
        return ""
    candidate = value.strip()
    if not candidate:
        return ""
    if candidate.startswith("//"):
        candidate = "https:" + candidate
    if not candidate.startswith(("http://", "https://")):
        candidate = "https://" + candidate
    parsed = urlparse(candidate)
    if not parsed.netloc:
        return ""
    return parsed.geturl().rstrip("/")


def normalize_field(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def dedupe_norm_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", normalize_name(value).lower())


def safe_get(url: str, timeout: int = 15, max_retries: int = 3, session: Optional[requests.Session] = None) -> requests.Response:
    last_error = None
    for attempt in range(max_retries):
        try:
            req = session or requests
            response = req.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code < 400:
                return response
            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = RuntimeError(f"Status {response.status_code}")
                continue
            return response
        except Exception as exc:  # pragma: no cover
            last_error = exc
    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to request {url}")


def domain_from_url(url: str) -> str:
    try:
        return urlparse(normalize_url(url)).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def ensure_dir(path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
