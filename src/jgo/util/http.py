"""
HTTP utility functions.

Thin wrappers around ``requests`` that retry with backoff when the remote
server returns 429 (Too Many Requests), honoring the ``Retry-After`` header.
A 403 (Forbidden) is surfaced via :func:`check_denied`, since repositories such
as Maven Central answer abusive traffic with a 403 block rather than a 429.

Every request is counted per host (see :func:`request_counts`), and requests to
a host can be spaced by a minimum interval (see :func:`throttle`), so a heavy
client can see and bound the load it puts on a repository.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import requests

_log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_DEFAULT_RETRY_AFTER = 60


_product: str | None = None


def set_user_agent(product: str | None) -> None:
    """
    Identify the application using jgo in the User-Agent of every request, e.g.
    ``"pombast/0.1 (+https://github.com/scijava/pombast)"``. It precedes jgo's
    own token, so repository operators can tell who is sending the traffic.
    """
    global _product
    _product = product


def user_agent() -> str:
    from ..constants import VERSION

    jgo = f"jgo/{VERSION} (+https://github.com/apposed/jgo)"
    agent = f"{jgo} python-requests/{requests.__version__}"
    return f"{_product} {agent}" if _product else agent


_lock = threading.Lock()
_counts: Counter[str] = Counter()
_intervals: dict[str, float] = {}
_host_locks: dict[str, threading.Lock] = {}
_next_allowed: dict[str, float] = {}


def throttle(host: str, interval: float) -> None:
    """
    Space requests to ``host`` at least ``interval`` seconds apart, across all
    threads. Pass 0 to remove the limit. The tightest limit set wins.
    """
    with _lock:
        if interval <= 0:
            _intervals.pop(host, None)
        else:
            _intervals[host] = max(interval, _intervals.get(host, 0))
            _host_locks.setdefault(host, threading.Lock())


def request_counts() -> dict[str, int]:
    """Number of HTTP requests issued per host (including retries)."""
    with _lock:
        return dict(_counts)


def reset_request_counts() -> None:
    with _lock:
        _counts.clear()


def _pace(host: str) -> None:
    """Count a request to ``host``, first waiting out its throttle interval."""
    with _lock:
        _counts[host] += 1
        interval = _intervals.get(host)
        host_lock = _host_locks.get(host)
    if not interval or host_lock is None:
        return
    # Held while sleeping, so concurrent callers queue up behind each other.
    with host_lock:
        wait = _next_allowed.get(host, 0) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _next_allowed[host] = time.monotonic() + interval


def request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """
    Issue an HTTP request, retrying on 429 responses.
    """
    host = urlparse(url).netloc
    kwargs["headers"] = {"User-Agent": user_agent(), **(kwargs.get("headers") or {})}
    response: requests.Response | None = None
    for attempt in range(_MAX_RETRIES + 1):
        _pace(host)
        response = requests.request(method, url, **kwargs)
        if response.status_code != 429 or attempt >= _MAX_RETRIES:
            return response
        wait = int(response.headers.get("Retry-After", _DEFAULT_RETRY_AFTER))
        _log.warning(f"Rate-limited by {url}; retrying in {wait}s")
        time.sleep(wait)
    assert response is not None
    return response


class RepositoryAccessDenied(RuntimeError):
    """A remote repository refused access (HTTP 401/403)."""


# Hosts already warned about, so a blocked repository warns once, not per request.
_denied_hosts: set[str] = set()


def check_denied(response: requests.Response, url: str, fail: bool) -> bool:
    """
    Report an access-denied (401/403) response.

    Some repositories answer 403 for content that is merely absent, so by default
    this only warns (once per host). With ``fail``, it raises
    :class:`RepositoryAccessDenied` instead, so a caller can stop at the first
    refusal rather than misreading a block as thousands of missing artifacts.

    Returns:
        True if the response was a denial (which must not be cached as a miss).
    """
    if response.status_code not in (401, 403):
        return False
    host = urlparse(url).netloc
    detail = " ".join(response.text.split())[:300] if response.text else ""
    message = f"HTTP {response.status_code} from {host} for {url}" + (
        f": {detail}" if detail else ""
    )
    if host not in _denied_hosts:
        _denied_hosts.add(host)
        _log.warning(message)
    if fail:
        raise RepositoryAccessDenied(message)
    return True


def get(url: str, **kwargs: Any) -> requests.Response:
    """GET with 429 retry/backoff. See :func:`request`."""
    return request("GET", url, **kwargs)


def head(url: str, **kwargs: Any) -> requests.Response:
    """HEAD with 429 retry/backoff. See :func:`request`."""
    return request("HEAD", url, **kwargs)
