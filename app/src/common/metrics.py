from __future__ import annotations

"""Lightweight in-process metrics.

Курс требует мониторинг, но у пользователя может не быть возможности
поднять Prometheus/Grafana. Поэтому делаем "встроенные" метрики:

- инкрементируются в коде (как раньше через metrics.*)
- доступны через HTTP endpoint /metrics в JSON

Интерфейс совместим с тем, как мы использовали prometheus_client:
Counter/Histogram/Gauge + .labels(...)
"""

from dataclasses import dataclass
from threading import Lock
from time import time
from typing import Any, Dict, Iterable, Tuple


_Lock = Lock


def _label_key(label_values: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(str(v) for v in label_values)


@dataclass(frozen=True)
class _MetricId:
    name: str
    label_names: Tuple[str, ...]


class _MetricBase:
    def __init__(self, name: str, description: str, label_names: Iterable[str] = ()) -> None:
        self.name = name
        self.description = description
        self.label_names = tuple(label_names)
        self._id = _MetricId(name=self.name, label_names=self.label_names)


class _LabelProxy:
    def __init__(self, metric: "_LabeledMetric", label_values: Tuple[str, ...]) -> None:
        self._metric = metric
        self._key = _label_key(label_values)

    def inc(self, amount: float = 1.0) -> None:
        self._metric._inc(self._key, amount)

    def observe(self, value: float) -> None:
        self._metric._observe(self._key, value)

    def set(self, value: float) -> None:
        self._metric._set(self._key, value)

    def dec(self, amount: float = 1.0) -> None:
        self._metric._inc(self._key, -amount)


class _LabeledMetric(_MetricBase):
    def __init__(self, name: str, description: str, label_names: Iterable[str] = ()) -> None:
        super().__init__(name, description, label_names)
        self._lock = _Lock()
        self._values: Dict[Tuple[str, ...], float] = {}
        self._obs: Dict[Tuple[str, ...], Dict[str, float]] = {} 
        self._last_updated: Dict[Tuple[str, ...], float] = {}

    def labels(self, *label_values: Any, **label_kwargs: Any) -> _LabelProxy:
        if label_kwargs:
            ordered = [label_kwargs[n] for n in self.label_names]
            label_values = tuple(ordered)
        if len(label_values) != len(self.label_names):
            raise ValueError(f"{self.name}: expected {len(self.label_names)} labels, got {len(label_values)}")
        return _LabelProxy(self, tuple(label_values))

    def _inc(self, key: Tuple[str, ...], amount: float) -> None:
        with self._lock:
            self._values[key] = float(self._values.get(key, 0.0) + amount)
            self._last_updated[key] = time()

    def _set(self, key: Tuple[str, ...], value: float) -> None:
        with self._lock:
            self._values[key] = float(value)
            self._last_updated[key] = time()

    def _observe(self, key: Tuple[str, ...], value: float) -> None:
        with self._lock:
            s = self._obs.get(key)
            if s is None:
                s = {"count": 0.0, "sum": 0.0, "min": float(value), "max": float(value)}
                self._obs[key] = s
            s["count"] += 1.0
            s["sum"] += float(value)
            s["min"] = min(s["min"], float(value))
            s["max"] = max(s["max"], float(value))
            self._last_updated[key] = time()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            items = []
            for key, val in self._values.items():
                labels = dict(zip(self.label_names, key))
                items.append({"labels": labels, "value": val, "updated_at": self._last_updated.get(key)})

            obs_items = []
            for key, s in self._obs.items():
                labels = dict(zip(self.label_names, key))
                avg = (s["sum"] / s["count"]) if s["count"] else 0.0
                obs_items.append(
                    {
                        "labels": labels,
                        "count": int(s["count"]),
                        "sum": s["sum"],
                        "avg": avg,
                        "min": s["min"],
                        "max": s["max"],
                        "updated_at": self._last_updated.get(key),
                    }
                )

        out: Dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__.lower(),
        }
        if self.label_names:
            out["labels"] = list(self.label_names)
        if items:
            out["series"] = items
        if obs_items:
            out["observations"] = obs_items
        return out


class Counter(_LabeledMetric):
    def inc(self, amount: float = 1.0) -> None:
        self._inc((), amount)


class Gauge(_LabeledMetric):
    def set(self, value: float) -> None:
        self._set((), value)

    def inc(self, amount: float = 1.0) -> None:
        self._inc((), amount)

    def dec(self, amount: float = 1.0) -> None:
        self._inc((), -amount)


class Histogram(_LabeledMetric):
    def observe(self, value: float) -> None:
        self._observe((), value)



HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

APP_ERRORS_TOTAL = Counter(
    "app_errors_total",
    "Total number of handled application errors",
    ["kind"],
)


REGISTERED_USERS_TOTAL = Counter(
    "registered_users_total",
    "Total number of registered users",
)

BILLING_TOPUPS_TOTAL = Counter(
    "billing_topups_total",
    "Total number of balance top-ups",
)

BILLING_CHARGES_TOTAL = Counter(
    "billing_charges_total",
    "Total number of balance charges (credits spent)",
    ["result"],
)

REVENUE_TOTAL = Counter(
    "revenue_total",
    "Total revenue from top-ups (credits)",
)

ML_REQUESTS_TOTAL = Counter(
    "ml_requests_total",
    "Total number of ML requests",
    ["model_name", "model_version", "mode", "status"], 
)

ML_ROWS_TOTAL = Counter(
    "ml_rows_total",
    "Total number of rows processed in ML requests",
    ["model_name", "model_version", "mode", "validity"],
)

ACTIVE_USERS = Gauge(
    "active_users",
    "Approximate number of active users in last N minutes (best-effort)",
)


def snapshot() -> Dict[str, Any]:
    """Return all known metrics in a JSON-friendly form."""

    metrics_list = [
        HTTP_REQUESTS_TOTAL,
        HTTP_REQUEST_DURATION_SECONDS,
        APP_ERRORS_TOTAL,
        REGISTERED_USERS_TOTAL,
        BILLING_TOPUPS_TOTAL,
        BILLING_CHARGES_TOTAL,
        REVENUE_TOTAL,
        ML_REQUESTS_TOTAL,
        ML_ROWS_TOTAL,
        ACTIVE_USERS,
    ]

    return {
        "ts": time(),
        "metrics": [m.snapshot() for m in metrics_list],
    }
