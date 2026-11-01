"""Tests for per-host request counting and throttling."""

import itertools
import threading
import time
from collections.abc import Iterator
from typing import Any, ClassVar

import pytest

from jgo.maven import MavenContext
from jgo.util import http


class FakeResponse:
    status_code = 200
    headers: ClassVar[dict[str, str]] = {}


@pytest.fixture
def fake_requests(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[float, str]]]:
    sent: list[tuple[float, str]] = []

    def fake(method: str, url: str, **kwargs: Any) -> FakeResponse:
        sent.append((time.monotonic(), url))
        return FakeResponse()

    monkeypatch.setattr(http.requests, "request", fake)
    http.reset_request_counts()
    yield sent
    http.reset_request_counts()
    http._intervals.clear()
    http._next_allowed.clear()


def test_requests_counted_per_host(fake_requests):
    http.get("https://a.example/x")
    http.get("https://a.example/y")
    http.head("https://b.example/z")
    assert http.request_counts() == {"a.example": 2, "b.example": 1}
    http.reset_request_counts()
    assert http.request_counts() == {}


def test_throttle_spaces_requests_across_threads(fake_requests):
    http.throttle("slow.example", 0.05)
    threads = [
        threading.Thread(target=http.get, args=(f"https://slow.example/{i}",))
        for i in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    times = sorted(t for t, _ in fake_requests)
    gaps = [b - a for a, b in itertools.pairwise(times)]
    assert len(gaps) == 3
    assert min(gaps) >= 0.045


def test_throttle_is_per_host(fake_requests):
    http.throttle("slow.example", 10)
    start = time.monotonic()
    http.get("https://slow.example/a")  # first request is not delayed
    for i in range(5):
        http.get(f"https://fast.example/{i}")
    assert time.monotonic() - start < 1


def test_context_min_interval_throttles_its_repos(fake_requests):
    MavenContext(remote_repos={"r": "https://repo.example/maven2"}, min_interval=0.5)
    assert http._intervals == {"repo.example": 0.5}
    http.throttle("repo.example", 0)
    assert http._intervals == {}


def test_user_agent_identifies_jgo_and_application(monkeypatch):
    seen = {}

    def fake(method, url, **kwargs):
        seen.update(kwargs["headers"])
        return FakeResponse()

    monkeypatch.setattr(http.requests, "request", fake)
    http.get("https://a.example/x")
    assert seen["User-Agent"].startswith("jgo/")
    http.set_user_agent("pombast/0.1")
    try:
        http.get("https://a.example/x")
    finally:
        http.set_user_agent(None)
    assert seen["User-Agent"].startswith("pombast/0.1 jgo/")
    # An explicit header from the caller wins.
    http.get("https://a.example/x", headers={"User-Agent": "custom"})
    assert seen["User-Agent"] == "custom"
