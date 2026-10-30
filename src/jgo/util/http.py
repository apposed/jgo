"""
HTTP utility functions.

Thin wrappers around ``requests`` that retry with backoff when the remote
server returns 429 (Too Many Requests), honoring the ``Retry-After`` header.
A 403 (Forbidden) is surfaced via :func:`check_denied`, since repositories such
as Maven Central answer abusive traffic with a 403 block rather than a 429.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

_log = logging.getLogger(__name__)

_MAX_RETRIES = 3
_DEFAULT_RETRY_AFTER = 60


def request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """
    Issue an HTTP request, retrying on 429 responses.
    """
    response: requests.Response | None = None
    for attempt in range(_MAX_RETRIES + 1):
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
    from urllib.parse import urlparse

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
