"""Límite de intentos fallidos de login por correo y dirección IP.

El conteo vive en memoria del proceso: sirve para un solo contenedor de API.
Si se escala a varios procesos, habrá que moverlo a Redis o a la base de datos.
"""

import threading
import time
from collections import defaultdict, deque


class FailedLoginLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: defaultdict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, window: float, now: float) -> None:
        bucket = self._failures[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if not bucket:
            del self._failures[key]

    def is_blocked(self, key: str, max_failures: int, window_seconds: float) -> bool:
        with self._lock:
            now = time.monotonic()
            self._prune(key, window_seconds, now)
            return len(self._failures.get(key, ())) >= max_failures

    def record_failure(self, key: str, window_seconds: float) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, window_seconds, now)
            self._failures[key].append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = FailedLoginLimiter()
