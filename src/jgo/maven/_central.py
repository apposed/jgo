"""
Queries against the Maven Central search API.

Maven Central exposes a SOLR index of everything it hosts, which lets jgo answer
questions that a plain repository cannot: full-text artifact search, and reverse
lookup of a local file's checksum to the coordinate it was published under.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from ..parse import Coordinate

_log = logging.getLogger(__name__)

# Note: search.maven.org serves the same API, but its index is stale and
# uncached queries routinely stall for 30+ seconds.
SEARCH_URL = "https://central.sonatype.com/solrsearch/select"

DEFAULT_TIMEOUT = 10


def solr_search(
    query: str, rows: int = 20, timeout: int = DEFAULT_TIMEOUT
) -> list[dict]:
    """
    Run a SOLR query against Maven Central.

    Args:
        query: SOLR query string (e.g. ``g:org.scijava AND a:parsington``)
        rows: Maximum number of documents to return
        timeout: Socket timeout in seconds

    Returns:
        The raw SOLR documents, or an empty list if the query matched nothing.

    Raises:
        RuntimeError: if the request or response could not be processed.
    """
    params = {"q": query, "rows": str(rows), "wt": "json"}
    url = f"{SEARCH_URL}?{urllib.parse.urlencode(params)}"

    _log.debug(f"Query URL: {url}")

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"Failed to connect to Maven Central: {e}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse response: {e}") from e

    if "response" not in data or "docs" not in data["response"]:
        return []

    return data["response"]["docs"]


def coordinates_by_sha1(
    sha1: str, rows: int = 20, timeout: int = DEFAULT_TIMEOUT
) -> list[Coordinate]:
    """
    Look up the coordinates a file was published under, by SHA-1 checksum.

    This identifies JARs with no embedded Maven metadata, as long as the exact
    file was published to Maven Central. More than one coordinate can match, since
    the same bytes are sometimes republished under a different groupId.

    Args:
        sha1: Hex SHA-1 checksum of the file
        rows: Maximum number of matches to return
        timeout: Socket timeout in seconds

    Returns:
        Matching coordinates, possibly empty.

    Raises:
        RuntimeError: if the request or response could not be processed.
    """
    docs = solr_search(f'1:"{sha1}"', rows=rows, timeout=timeout)

    coordinates = []
    for doc in docs:
        groupId = doc.get("g")
        artifactId = doc.get("a")
        if not groupId or not artifactId:
            continue
        coordinates.append(
            Coordinate(
                groupId=groupId,
                artifactId=artifactId,
                version=doc.get("v"),
                classifier=doc.get("c") or None,
                packaging=doc.get("p") or None,
            )
        )
    return coordinates
