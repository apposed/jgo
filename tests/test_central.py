"""
Unit tests for Maven Central search API queries.
"""

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jgo.cli._commands.info import _central_coordinates
from jgo.env import jar_sha1
from jgo.maven import coordinates_by_sha1, solr_search

SHA1 = "28e8b7771008d33637d58325c81b04729d353e17"


def mock_solr(docs):
    """Patch urlopen to answer with the given SOLR documents."""
    payload = json.dumps({"response": {"docs": docs}}).encode("utf-8")
    response = MagicMock()
    response.read.return_value = payload
    response.__enter__.return_value = response
    return patch("urllib.request.urlopen", return_value=response)


def test_solr_search_query_url():
    """The query, row count, and JSON format are all passed to the API."""
    with mock_solr([]) as mock_urlopen:
        solr_search('1:"abc"', rows=5)

    url = mock_urlopen.call_args[0][0]
    assert url.startswith("https://central.sonatype.com/solrsearch/select?")
    assert "q=1%3A%22abc%22" in url
    assert "rows=5" in url
    assert "wt=json" in url


def test_solr_search_malformed_response():
    """A response without the expected structure yields no documents."""
    response = MagicMock()
    response.read.return_value = b'{"responseHeader": {"status": 0}}'
    response.__enter__.return_value = response

    with patch("urllib.request.urlopen", return_value=response):
        assert solr_search("anything") == []


def test_solr_search_unparseable_response():
    """A non-JSON response is reported as an error rather than propagating."""
    response = MagicMock()
    response.read.return_value = b"<html>down for maintenance</html>"
    response.__enter__.return_value = response

    with (
        patch("urllib.request.urlopen", return_value=response),
        pytest.raises(RuntimeError, match="Failed to parse response"),
    ):
        solr_search("anything")


def test_coordinates_by_sha1():
    """Checksum matches are converted to coordinates."""
    docs = [
        {
            "g": "org.ahocorasick",
            "a": "ahocorasick",
            "v": "0.2.4",
            "p": "jar",
        }
    ]

    with mock_solr(docs) as mock_urlopen:
        coordinates = coordinates_by_sha1(SHA1)

    assert f"q=1%3A%22{SHA1}%22" in mock_urlopen.call_args[0][0]
    assert len(coordinates) == 1
    assert coordinates[0].groupId == "org.ahocorasick"
    assert coordinates[0].artifactId == "ahocorasick"
    assert coordinates[0].version == "0.2.4"


def test_coordinates_by_sha1_incomplete_doc():
    """Documents missing a groupId or artifactId are skipped."""
    with mock_solr([{"a": "orphan", "v": "1.0.0"}, {"g": "org.example"}]):
        assert coordinates_by_sha1(SHA1) == []


def test_jar_sha1(tmp_path):
    """The checksum is computed over the file as a whole."""
    jar_path = tmp_path / "thing.jar"
    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")

    import hashlib

    assert jar_sha1(jar_path) == hashlib.sha1(jar_path.read_bytes()).hexdigest()


class TestCentralCoordinates:
    """Identification of a local JAR by checksum lookup."""

    def make_jar(self, tmp_path: Path) -> Path:
        jar_path = tmp_path / "mystery.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr("org/example/Thing.class", b"\xca\xfe\xba\xbe")
        return jar_path

    def test_match(self, tmp_path):
        """The first match is the JAR's identity; further matches are alternates."""
        docs = [
            {"g": "antlr", "a": "antlr", "v": "2.7.7"},
            {"g": "org.antlr", "a": "antlr", "v": "2.7.7"},
        ]

        with mock_solr(docs):
            coordinates = _central_coordinates(self.make_jar(tmp_path))

        assert [str(c) for c in coordinates] == [
            "antlr:antlr:2.7.7",
            "org.antlr:antlr:2.7.7",
        ]
        assert all(c.source == "central" for c in coordinates)
        assert coordinates[0].primary
        assert not coordinates[1].primary

    def test_no_match(self, tmp_path):
        """A file Maven Central does not know yields no coordinates."""
        with mock_solr([]):
            assert _central_coordinates(self.make_jar(tmp_path)) == []

    def test_lookup_failure(self, tmp_path):
        """A failed lookup is a warning, not an error."""
        with patch(
            "jgo.maven.coordinates_by_sha1", side_effect=RuntimeError("no network")
        ):
            assert _central_coordinates(self.make_jar(tmp_path)) == []
