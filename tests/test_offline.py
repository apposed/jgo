"""Tests for offline mode: no remote repository may be contacted."""

from pathlib import Path

import pytest

from jgo.maven import MavenContext
from jgo.maven._resolver import MvnResolver, PythonResolver
from jgo.util import mvn


class NoDownloadResolver(PythonResolver):
    def download(self, artifact):
        raise AssertionError(f"Attempted to download {artifact} while offline")


@pytest.fixture
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Attempted network access while offline")

    monkeypatch.setattr("jgo.util.http.request", fail)


def _context(repo_cache: Path) -> MavenContext:
    return MavenContext(
        resolver=NoDownloadResolver(),
        repo_cache=repo_cache,
        local_repos=[],
        offline=True,
    )


def test_offline_resolves_cached_artifact(tmp_path, no_network):
    jar = tmp_path / "org/example/foo/1.0/foo-1.0.jar"
    jar.parent.mkdir(parents=True)
    jar.write_bytes(b"cached")

    artifact = _context(tmp_path).project("org.example", "foo").at_version("1.0")
    assert artifact.artifact().resolve() == jar


def test_offline_refuses_to_download(tmp_path, no_network):
    artifact = _context(tmp_path).project("org.example", "foo").at_version("1.0")
    with pytest.raises(RuntimeError, match="offline mode"):
        artifact.artifact().resolve()


def test_offline_skips_metadata_update(tmp_path, no_network):
    project = _context(tmp_path).project("org.example", "foo")
    project.update()
    project.at_version("1.0-SNAPSHOT").update_snapshot_metadata()


def test_offline_skips_last_modified(tmp_path, no_network):
    artifact = _context(tmp_path).project("org.example", "foo").at_version("1.0")
    assert artifact.artifact().last_modified() is None


def test_mvn_resolver_offline_flag():
    resolver = MvnResolver(Path("mvn"), update=True, offline=True)
    assert "-o" in resolver.mvn_flags
    assert "-U" not in resolver.mvn_flags


def test_offline_does_not_fetch_maven(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr(mvn, "fetch_maven", pytest.fail)
    with pytest.raises(RuntimeError, match="offline mode"):
        mvn.ensure_maven_available(offline=True)
