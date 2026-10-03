"""jgo search - Search for artifacts in Maven repositories"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from functools import cmp_to_key
from typing import TYPE_CHECKING

import rich_click as click

from ...config import GlobalSettings
from ...maven import compare_versions, solr_search
from ...parse import Coordinate
from ...styles import (
    COORD_HELP_FULL,
    COORD_HELP_SHORT,
    MAVEN_REPOSITORIES,
    secondary,
    syntax,
    tip,
)
from ...util.logging import log_exception_if_verbose
from .._args import build_parsed_args
from .._console import console_print
from .._output import print_dry_run
from ..rich import format_coordinate

if TYPE_CHECKING:
    from .._args import ParsedArgs

_log = logging.getLogger(__name__)


@click.command(
    help=f"Search for artifacts in {MAVEN_REPOSITORIES}. "
    f"Supports plain text, coordinates ({COORD_HELP_SHORT}), or field syntax ({syntax('g: a:')}).",
    epilog=tip(
        f"Try {syntax('g:groupId a:artifactId')} for field syntax, "
        f"{COORD_HELP_FULL} for coordinates, or plain text. "
        f"Use {syntax('*')} for wildcards."
    ),
)
@click.option(
    "--limit",
    type=int,
    default=20,
    metavar="N",
    help=f"Limit number of results {secondary('(default: 20)')}",
)
@click.option(
    "--repository",
    metavar="NAME",
    help=f"Search specific repository {secondary('(default: central)')}",
)
@click.option(
    "--detailed",
    is_flag=True,
    help="Show detailed metadata for each result",
)
@click.argument(
    "query",
    nargs=-1,
    required=True,
    cls=click.RichArgument,
    help=f"Search terms. Supports plain text, coordinates ({COORD_HELP_SHORT}), or field syntax (g: a:)",
)
@click.pass_context
def search(
    ctx: click.Context,
    limit: int,
    repository: str | None,
    detailed: bool,
    query: tuple[str, ...],
) -> None:
    """
    Search for artifacts in Maven repositories.

    The QUERY argument supports three input styles:

    1. **Plain Text** - Matches groupId components and artifactId prefixes:
       - jgo search apache commons
       - jgo search junit

    2. **Maven Coordinates** - Automatically converted to field query:
       - jgo search org.apache.commons:commons-lang3
       - jgo search junit:junit:4.13.2

    3. **Field Syntax** - Direct field queries:
       - jgo search g:org.apache.commons a:commons-lang3
       - jgo search a:jackson-databind v:2.15*
       - jgo search g:org.scijava a:parsington v:*
       - jgo search g:org.scijava AND NOT a:scijava*

    Field names:
      - g:groupId - Search by group ID
      - a:artifactId - Search by artifact ID
      - v:version - Search by version
      - p:packaging - Search by packaging type (jar, pom, etc.)

    Terms are combined with AND, unless the query includes explicit
    AND, OR, or NOT operators. Use * as a wildcard, e.g. a:jackson-*.

    Results list one line per project (groupId:artifactId) at its latest
    version. A query constraining the version, even v:*, lists every
    matching version instead, newest first.

    Packaging (p:) filters by the packaging declared in each version's
    POM. Classifiers are not indexed, so cannot be searched.

    Args:
        query: One or more search terms
        limit: Maximum number of results to return (default: 20)
        repository: Repository to search (currently only 'central' supported)
        detailed: Show additional metadata (version count, packaging, last updated)
    """

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, command="search")

    # Join query parts into a single string
    query_str = " ".join(query)

    exit_code = execute(
        args,
        config.to_dict(),
        query=query_str,
        limit=limit,
        repository=repository,
        detailed=detailed,
    )
    ctx.exit(exit_code)


def execute(
    args: ParsedArgs,
    config: dict,
    query: str,
    limit: int = 20,
    repository: str | None = None,
    detailed: bool = False,
) -> int:
    """
    Execute the search command.

    Args:
        args: Parsed command line arguments
        config: Global settings
        query: Search query
        limit: Maximum number of results to show
        repository: Specific repository to search (currently only 'central' supported)
        detailed: Show detailed metadata for each result

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if not query:
        _log.error("Search query is required")
        return 1

    # For now, only support Maven Central
    # Future enhancement: support custom repositories
    if repository and repository != "central":
        console_print(
            f"Error: Repository '{repository}' is not supported. Only 'central' is currently supported.",
            stderr=True,
        )
        return 1

    _log.info(f"Searching Maven Central for: {query}")

    # Dry run
    if args.dry_run:
        print_dry_run(f"Would search Maven Central for '{query}' with limit {limit}")
        return 0

    # Search Maven Central
    try:
        results, truncated = _search_maven_central(query, limit, args.timeout)

        if not results:
            console_print(f"No results found for query: {query}")
            return 0

        # Display results
        _display_results(results, detailed=detailed)
        if truncated:
            console_print(
                tip(f"Showing the first {limit} results. Use --limit for more.")
            )

        return 0

    except ValueError as e:
        _log.error(str(e))
        return 1
    except Exception as e:
        _log.error(f"Failed to search Maven Central: {e}")
        log_exception_if_verbose(args.verbose)
        return 1


_NO_CLASSIFIERS = "Maven Central search cannot filter by classifier"


def _convert_query_to_solr(query: str) -> str:
    """
    Convert a query to field syntax if needed.

    Handles three cases:
    1. Maven coordinate format (G:A or G:A:V) → convert to SOLR AND query
    2. Explicit boolean operators (AND, OR, NOT) → pass through
    3. Otherwise → join terms with AND, matching plain text terms as prefixes

    Args:
        query: The search query string

    Returns:
        SOLR-formatted query string

    Raises:
        ValueError: if the query filters by classifier, which the search API
            does not index.
    """
    # Common SOLR fields: g, a, v, p, c, l, ec, fc
    field_pattern = r"\b(g|a|v|p|c|l|ec|fc):"

    if re.search(r"\b(c|l):", query):
        raise ValueError(_NO_CLASSIFIERS)

    # Try parsing as Maven coordinate (contains : but not field syntax)
    coord = None
    if ":" in query and not re.search(field_pattern, query):
        try:
            coord = Coordinate.parse(query)
        except ValueError:
            # Not a valid coordinate, treat as plain text
            _log.debug(f"Failed to parse as coordinate, using as plain text: {query}")

    if coord:
        if coord.classifier:
            raise ValueError(_NO_CLASSIFIERS)
        parts = [f"g:{coord.groupId}", f"a:{coord.artifactId}"]
        if coord.version:
            parts.append(f"v:{coord.version}")
        if coord.packaging:
            parts.append(f"p:{coord.packaging}")
        solr_query = " AND ".join(parts)
        _log.debug(f"Converted coordinate '{query}' to SOLR: {solr_query}")
        return solr_query

    terms = query.split()
    if any(t in ("AND", "OR", "NOT") for t in terms):
        _log.debug(f"Query has explicit operators: {query}")
        return query

    # Note: Maven Central rejects terms not joined by an operator, and matches
    # a bare term only against a whole groupId component or an entire
    # artifactId, so plain text terms become prefix matches.
    terms = [
        t if re.search(field_pattern, t) or re.search(r"[*?]", t) else f"{t}*"
        for t in terms
    ]
    solr_query = " AND ".join(terms)
    _log.debug(f"Converted query '{query}' to SOLR: {solr_query}")
    return solr_query


def _search_maven_central(
    query: str, limit: int, timeout: int = 10
) -> tuple[list[dict], bool]:
    """
    Search Maven Central using the SOLR API.

    Queries constraining the version (e.g. v:1.*) yield one result per
    matching version, newest first; other queries yield one result per
    project (groupId:artifactId), at its latest matching version.

    Args:
        query: Search query
        limit: Maximum number of results
        timeout: Socket timeout in seconds

    Returns:
        Tuple of (results, whether more results were available than the limit)
    """
    # Convert query to field syntax if needed
    solr_query = _convert_query_to_solr(query)

    list_versions = bool(re.search(r"\bv:", solr_query))

    # Note: A query naming both groupId and artifactId, or a version, yields one
    # document per version, in no particular order, so fetch them all. One more
    # row than the limit reveals whether results are being cut off.
    per_version = list_versions or (
        re.search(r"\bg:", solr_query) and re.search(r"\ba:", solr_query)
    )
    rows = max(limit + 1, 1000) if per_version else limit + 1

    docs = solr_search(solr_query, rows=rows, timeout=timeout)

    # Convert to simplified format
    results = []
    by_ga: dict[tuple[str, str], dict] = {}
    for doc in docs:
        ga = (doc.get("g", ""), doc.get("a", ""))
        version = doc.get("latestVersion") or doc.get("v", "")
        if not list_versions and ga in by_ga:
            # Merge another version of the same project.
            result = by_ga[ga]
            result["version_count"] += 1
            if compare_versions(version, result["version"]) > 0:
                result["version"] = version
                if "timestamp" in doc:
                    result["last_updated"] = doc["timestamp"]
            continue

        result = {
            "group_id": ga[0],
            "artifact_id": ga[1],
            "version": version,
            "packaging": doc.get("p", "jar"),  # Packaging type (jar, pom, etc.)
        }
        if not list_versions:
            result["version_count"] = doc.get("versionCount") or 1

        # Add timestamp if available
        if "timestamp" in doc:
            result["last_updated"] = doc["timestamp"]

        by_ga[ga] = result
        results.append(result)

    if list_versions:
        results.sort(
            key=cmp_to_key(
                lambda r1, r2: compare_versions(r2["version"], r1["version"])
            )
        )

    return results[:limit], len(results) > limit


def _display_results(results: list[dict], detailed: bool = False) -> None:
    """
    Display search results.

    Args:
        results: List of project or version dictionaries
        detailed: Show detailed metadata for each result
    """
    noun = "project" if "version_count" in results[0] else "version"
    plural = "" if len(results) == 1 else "s"
    console_print(f"Found {len(results)} {noun}{plural}:")
    console_print()

    for i, result in enumerate(results, 1):
        coord = Coordinate(result["group_id"], result["artifact_id"], result["version"])
        console_print(f"{i}. {format_coordinate(coord)}")

        # Show additional details in detailed mode
        if detailed:
            version_count = result.get("version_count", 0)
            packaging = result.get("packaging", "")

            if version_count > 1:
                console_print(f"   Available versions: {version_count}")

            if packaging:
                console_print(f"   Packaging: {packaging}")

            if "last_updated" in result:
                # Convert timestamp to readable format
                timestamp = result["last_updated"]
                # Timestamp is in milliseconds
                dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                console_print(f"   Last updated: {dt.strftime('%Y-%m-%d')}")

        console_print()
