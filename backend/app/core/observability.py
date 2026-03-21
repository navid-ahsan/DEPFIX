"""Lightweight runtime observability helpers.

Tracks API request latency/error stats in-memory and exposes process metrics.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from statistics import mean
from threading import Lock
from time import perf_counter
from typing import Deque, Dict, List

import psutil


@dataclass
class RequestSample:
    path: str
    method: str
    status_code: int
    latency_ms: float


_SAMPLES: Deque[RequestSample] = deque(maxlen=2000)
_LOCK = Lock()
_START_TS = perf_counter()


def record_request(path: str, method: str, status_code: int, latency_ms: float) -> None:
    """Record one request sample in a bounded in-memory buffer."""
    sample = RequestSample(
        path=path,
        method=method,
        status_code=status_code,
        latency_ms=latency_ms,
    )
    with _LOCK:
        _SAMPLES.append(sample)


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int((len(sorted_vals) - 1) * pct)
    return float(sorted_vals[idx])


def get_request_metrics_snapshot() -> Dict:
    """Return aggregate request stats for recent in-memory samples."""
    with _LOCK:
        samples = list(_SAMPLES)

    total = len(samples)
    latencies = [s.latency_ms for s in samples]
    errors = [s for s in samples if s.status_code >= 500]

    by_route: Dict[str, Dict] = defaultdict(lambda: {
        "count": 0,
        "error_count": 0,
        "latencies": [],
    })

    for s in samples:
        key = f"{s.method} {s.path}"
        route = by_route[key]
        route["count"] += 1
        route["latencies"].append(s.latency_ms)
        if s.status_code >= 500:
            route["error_count"] += 1

    route_rows = []
    for route_key, stats in by_route.items():
        route_lat = stats["latencies"]
        count = stats["count"]
        route_rows.append(
            {
                "route": route_key,
                "count": count,
                "error_count": stats["error_count"],
                "error_rate_pct": round((stats["error_count"] / count) * 100, 2) if count else 0.0,
                "avg_latency_ms": round(mean(route_lat), 2) if route_lat else 0.0,
                "p95_latency_ms": round(_percentile(route_lat, 0.95), 2) if route_lat else 0.0,
            }
        )

    route_rows.sort(key=lambda r: r["count"], reverse=True)

    return {
        "uptime_sec": round(perf_counter() - _START_TS, 2),
        "requests_total": total,
        "error_count": len(errors),
        "error_rate_pct": round((len(errors) / total) * 100, 2) if total else 0.0,
        "avg_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "p95_latency_ms": round(_percentile(latencies, 0.95), 2) if latencies else 0.0,
        "by_route": route_rows[:20],
    }


def get_process_memory_snapshot() -> Dict:
    """Return process and system memory usage snapshots."""
    process = psutil.Process()
    rss_mb = process.memory_info().rss / (1024 ** 2)
    vms_mb = process.memory_info().vms / (1024 ** 2)
    system_mem = psutil.virtual_memory()

    return {
        "process_rss_mb": round(rss_mb, 2),
        "process_vms_mb": round(vms_mb, 2),
        "system_total_gb": round(system_mem.total / (1024 ** 3), 2),
        "system_used_gb": round(system_mem.used / (1024 ** 3), 2),
        "system_usage_pct": round(system_mem.percent, 2),
    }
