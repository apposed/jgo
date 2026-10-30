"""Tests for caching remote misses and handling denied (403) responses."""

import os
import time

import pytest

from jgo.maven import MavenContext
from jgo.maven._resolver import PythonResolver
from jgo.util import http

CENTRAL = "https://repo1.maven.org/maven2"
OTHER = "https://maven.example.org/repo"


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text
        self.headers: dict[str, str] = {}

    def close(self):
        pass


@pytest.fixture
def requests_log(monkeypatch):
    """Record every requested URL; answer with the status in ``statuses``."""
    log: list[str] = []
    statuses: dict[str, FakeResponse] = {}

    def fake_request(method, url, **kwargs):
        log.append(url)
        for prefix, response in statuses.items():
            if url.startswith(prefix):
                return response
        return FakeResponse(404)

    monkeypatch.setattr("jgo.util.http.request", fake_request)
    http._denied_hosts.clear()
    return log, statuses


def _context(tmp_path, repos, **kwargs) -> MavenContext:
    return MavenContext(
        resolver=PythonResolver(),
        repo_cache=tmp_path,
        local_repos=[],
        remote_repos=repos,
        **kwargs,
    )


def _javadoc(ctx, version="1.0"):
    return (
        ctx.project("org.example", "foo")
        .at_version(version)
        .artifact(classifier="javadoc")
    )


def _cache_pom(tmp_path, version="1.0"):
    pom = tmp_path / f"org/example/foo/{version}/foo-{version}.pom"
    pom.parent.mkdir(parents=True, exist_ok=True)
    pom.write_text("<project/>")


def test_404_is_cached_per_repo(tmp_path, requests_log):
    log, _ = requests_log
    ctx = _context(tmp_path, {"other": OTHER})
    for _ in range(2):
        with pytest.raises(RuntimeError, match="not found"):
            _javadoc(ctx).resolve()
    assert len(log) == 1
    assert (tmp_path / "org/example/foo/1.0/foo-1.0-javadoc.jar-other.404").exists()


def test_cached_404_expires_after_ttl(tmp_path, requests_log):
    log, _ = requests_log
    ctx = _context(tmp_path, {"other": OTHER}, miss_ttl=60)
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    miss = tmp_path / "org/example/foo/1.0/foo-1.0-javadoc.jar-other.404"
    old = time.time() - 120
    os.utime(miss, (old, old))
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    assert len(log) == 2


def test_central_miss_is_permanent_once_version_exists(tmp_path, requests_log):
    log, _ = requests_log
    _cache_pom(tmp_path)
    ctx = _context(tmp_path, {"central": CENTRAL}, miss_ttl=60)
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    miss = tmp_path / "org/example/foo/1.0/foo-1.0-javadoc.jar-central.404"
    old = time.time() - 10 * 365 * 24 * 3600
    os.utime(miss, (old, old))
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    assert len(log) == 1


def test_central_miss_expires_without_pom(tmp_path, requests_log):
    log, _ = requests_log
    ctx = _context(tmp_path, {"central": CENTRAL}, miss_ttl=60)
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    miss = tmp_path / "org/example/foo/1.0/foo-1.0-javadoc.jar-central.404"
    old = time.time() - 120
    os.utime(miss, (old, old))
    with pytest.raises(RuntimeError):
        _javadoc(ctx).resolve()
    assert len(log) == 2


def test_update_ignores_cached_misses(tmp_path, requests_log):
    log, _ = requests_log
    _cache_pom(tmp_path)
    with pytest.raises(RuntimeError):
        _javadoc(_context(tmp_path, {"central": CENTRAL})).resolve()
    with pytest.raises(RuntimeError):
        _javadoc(_context(tmp_path, {"central": CENTRAL}, update=True)).resolve()
    assert len(log) == 2


def test_snapshot_misses_are_not_cached(tmp_path, requests_log):
    log, _ = requests_log
    ctx = _context(tmp_path, {"other": OTHER})
    artifact = _javadoc(ctx, "1.0-SNAPSHOT")
    for _ in range(2):
        with pytest.raises(RuntimeError):
            artifact.resolve()
    assert not list(tmp_path.rglob("*.404"))


def test_denied_is_not_cached_as_miss(tmp_path, requests_log, caplog):
    log, statuses = requests_log
    statuses[CENTRAL] = FakeResponse(403, "This IP has been blocked")
    ctx = _context(tmp_path, {"central": CENTRAL})
    for _ in range(2):
        with pytest.raises(RuntimeError, match="not found"):
            _javadoc(ctx).resolve()
    assert len(log) == 2
    assert not list(tmp_path.rglob("*.404"))
    # Warned once per host, with the server's explanation.
    denials = [r for r in caplog.records if "HTTP 403" in r.getMessage()]
    assert len(denials) == 1
    assert "This IP has been blocked" in denials[0].getMessage()


def test_fail_on_denied_raises(tmp_path, requests_log):
    _, statuses = requests_log
    statuses[CENTRAL] = FakeResponse(403, "blocked")
    ctx = _context(tmp_path, {"central": CENTRAL}, fail_on_denied=True)
    with pytest.raises(http.RepositoryAccessDenied, match="blocked"):
        _javadoc(ctx).resolve()


def test_metadata_sentinel_only_on_404(tmp_path, requests_log):
    _, statuses = requests_log
    statuses[CENTRAL] = FakeResponse(403, "blocked")
    project = _context(tmp_path, {"central": CENTRAL}).project("org.example", "foo")
    project.update(max_age=3600)
    assert not (tmp_path / "org/example/foo/maven-metadata-central.404").exists()
    statuses.clear()
    project.update(max_age=3600)
    assert (tmp_path / "org/example/foo/maven-metadata-central.404").exists()


def test_denied_propagates_through_lenient_model(tmp_path, requests_log):
    """A denial deep in a transitive resolve must not be swallowed as a miss."""
    from jgo.maven import Model, RepositoryAccessDenied

    _, statuses = requests_log
    statuses[CENTRAL] = FakeResponse(403, "blocked")
    _cache_pom(tmp_path)
    (tmp_path / "org/example/foo/1.0/foo-1.0.pom").write_text(
        "<project><groupId>org.example</groupId><artifactId>foo</artifactId>"
        "<version>1.0</version><dependencies><dependency>"
        "<groupId>org.example</groupId><artifactId>bar</artifactId>"
        "<version>2.0</version></dependency></dependencies></project>"
    )
    ctx = _context(tmp_path, {"central": CENTRAL}, fail_on_denied=True)
    pom = ctx.project("org.example", "foo").at_version("1.0").pom()
    with pytest.raises(RepositoryAccessDenied):
        Model(pom, ctx, lenient=True).dependencies()
