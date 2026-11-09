"""Latest airport observations, cached independently of the simulator clock."""
import re
import time
from threading import Lock

import requests


_cache = {}
_locks = {}
_guard = Lock()


def _visibility(report):
    # International METAR visibility retains bounds lost in rounded statute miles.
    raw = report.get("rawOb") or ""
    if " CAVOK " in f" {raw} ":
        return "≥10 km"
    metric = re.search(r"\b(?:\d{3}|VRB)\d{2,3}(?:G\d+)?(?:KT|MPS)(?: \d{3}V\d{3})? (\d{4})\b", raw)
    if metric:
        meters = int(metric[1])
        return "≥10 km" if meters == 9999 else f"{meters / 1000:g} km"
    miles = report.get("visib")
    return f"{miles} SM" if miles is not None else None


def observation(icao):
    with _guard:
        lock = _locks.setdefault(icao, Lock())
    with lock:
        expires, previous = _cache.get(icao, (0, None))
        if time.monotonic() < expires:
            return previous
        report = previous and previous["report"]
        try:
            response = requests.get(
                "https://aviationweather.gov/api/data/metar",
                params={"ids": icao, "format": "json"},
                headers={"User-Agent": "ATC-Radar-Trainer/1.0"}, timeout=6,
            )
            response.raise_for_status()
            rows = [] if response.status_code == 204 else response.json()
            latest = max((r for r in rows if r.get("icaoId") == icao
                          and isinstance(r.get("obsTime"), (int, float))),
                         key=lambda r: r["obsTime"], default=None)
            if latest and (not report or latest["obsTime"] >= report["obsTime"]):
                report = {k: latest.get(k) for k in (
                    "obsTime", "temp", "dewp", "wdir", "wspd", "wgst", "altim",
                    "wxString", "clouds", "rawOb", "metarType")}
                report["visibility"] = _visibility(latest)
            status = "ok" if latest else "no_recent_report"
        except (requests.RequestException, ValueError, TypeError, AttributeError):
            status = "refresh_failed"
        result = {"icao": icao, "report": report, "status": status}
        _cache[icao] = (time.monotonic() + 300, result)
        return result
