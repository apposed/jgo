"""
Core Maven data structures and configuration.

This module provides "smart" data structures and logic for Maven concepts.
Unlike the simple data structures in jgo.parse, these classes actively perform
Maven operations:
- Version resolution (RELEASE → newest release version, LATEST → latest snapshot)
- Metadata fetching and caching
- Artifact downloading from repositories
- POM parsing and interpolation
- Dependency management
- Repository configuration

The main classes form a hierarchy:
- MavenContext: Configuration (repositories, cache, resolver)
- Project [G:A]: A groupId:artifactId (G:A) pair with metadata access
- Component [G:A:V]: A Project at a specific version (V)
- Artifact [G:A:P:C:V]: One file of a Component, with classifier (C) and packaging (P)
- Dependency [G:A:P:C:V:S]: An Artifact with scope, optional flag, and exclusions

For simple/low-level data structures without Maven logic, see the jgo.parse subpackage.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cmp_to_key
from hashlib import md5, sha1
from os import environ
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from ..constants import MAVEN_CENTRAL_URL, default_maven_repo
from ..parse import Coordinate, coord2str
from ..util.io import binary, text
from ._metadata import Metadatas, MetadataXML, SnapshotMetadataXML
from ._pom import POM, parse_dependency_element_to_coordinate
from ._version import compare_versions

if TYPE_CHECKING:
    from ._metadata import Metadata

# -- Constants --

DEFAULT_LOCAL_REPOS: list[Path] = []
DEFAULT_REMOTE_REPOS = {"central": MAVEN_CENTRAL_URL}
DEFAULT_CLASSIFIER = ""
DEFAULT_PACKAGING = "jar"


class MavenContext:
    """
    Maven configuration and settings.
    * Local repo cache folder.
    * Local repository storage folders.
    * Remote repository name:URL pairs.
    * Artifact resolution mechanism.
    """

    def __init__(
        self,
        resolver: Resolver | None = None,
        repo_cache: Path | None = None,
        local_repos: list[Path] | None = None,
        remote_repos: dict[str, str] | None = None,
        timeout: int = 10,
    ):
        """
        Create a Maven context.

        Args:
            resolver:
                Mechanism to use for resolving local paths to artifacts.
                By default, the PythonResolver will be used.
            repo_cache:
                Optional path to Maven local repository cache directory, i.e. destination
                of `mvn install`. Maven typically uses ~/.m2/repository by default.
                This directory is treated as *read-write* by this library, e.g.
                the download() function will store downloaded artifacts there.
                If no local repository cache path is given, Maven defaults will be used
                (M2_REPO environment variable, or ~/.m2/repository by default).
            local_repos:
                Optional list of Maven repository storage local paths to check for artifacts.
                These are real Maven repositories, such as those managed by a Sonatype Nexus v2 instance,
                i.e. ultimate destinations of `mvn deploy`, *not* local repository caches!
                These directories are treated as *read-only* by this library.
                If no local repository paths are given, none will be inferred.
            remote_repos:
                Optional dict of remote name:URL pairs, with each URL corresponding
                to a remote Maven repository accessible via HTTP/HTTPS.
                If no remote repository paths are given, only Maven Central will be used.
            timeout:
                HTTP request timeout in seconds for downloading artifacts and metadata.
                Defaults to 10 seconds.
        """
        self.repo_cache: Path = repo_cache or Path(
            environ.get("M2_REPO", default_maven_repo())
        )
        self.local_repos: list[Path] = (
            DEFAULT_LOCAL_REPOS if local_repos is None else local_repos
        ).copy()
        self.remote_repos: dict[str, str] = (
            DEFAULT_REMOTE_REPOS if remote_repos is None else remote_repos
        ).copy()
        self.timeout: int = timeout
        # Import here to avoid circular dependency
        if resolver is None:
            from ._resolver import PythonResolver

            resolver = PythonResolver()
        self.resolver: Resolver = resolver

    def project(self, groupId: str, artifactId: str) -> Project:
        """
        Get a project (G:A) with the given groupId and artifactId.

        Args:
            groupId: The groupId of the project.
            artifactId: The artifactId of the project.

        Returns:
            The Project object.
        """
        return Project(self, groupId, artifactId)

    def parse_dependency_element(self, el) -> Dependency:
        """
        Parse a <dependency> XML element into a Dependency object.

        This delegates to pom.py for XML parsing, then uses create_dependency
        to build the Dependency object.

        Args:
            el: The XML element from which to create the dependency.

        Returns:
            The Dependency object.
        """

        # Parse XML element to Coordinate (pom.py handles ElementTree)
        coord, exclusion_tuples = parse_dependency_element_to_coordinate(el)

        # Validate required fields
        assert coord.groupId and coord.artifactId, (
            f"Invalid dependency: groupId={coord.groupId}, artifactId={coord.artifactId}"
        )

        # Convert exclusion tuples to Project objects
        exclusions = [self.project(g, a) for g, a in exclusion_tuples if g and a]

        # Use create_dependency to build the Dependency
        return self.create_dependency(coord, exclusions)

    def create_dependency(
        self,
        coordinate: Coordinate | str,
        exclusions: Iterable[Project] | None = None,
    ) -> Dependency:
        """
        Create a Dependency object from a Maven coordinate.

        Args:
            coordinate: The Maven coordinate to convert to a Dependency.
            exclusions: Optional list of Project exclusions.

        Returns:
            The Dependency object.
        """
        coord = Coordinate.parse(coordinate)
        groupId = coord.groupId
        artifactId = coord.artifactId
        version = coord.version
        classifier = coord.classifier or DEFAULT_CLASSIFIER
        packaging = coord.packaging or DEFAULT_PACKAGING
        scope = coord.scope
        optional = coord.optional or False

        project = self.project(groupId, artifactId)
        component = project.at_version(version) if version else project.at_version("")
        artifact = component.artifact(classifier, packaging)
        return Dependency(
            artifact, scope, optional, exclusions or [], raw=coord.raw or False
        )

    def pom_to_artifact(self, pom: POM) -> Artifact:
        """
        Create an Artifact object representing the given POM.

        Args:
            pom: The POM to convert to an Artifact.

        Returns:
            The Artifact object.
        """
        assert (
            pom.groupId is not None
            and pom.artifactId is not None
            and pom.version is not None
        )
        project = self.project(pom.groupId, pom.artifactId)
        return project.at_version(pom.version).artifact(packaging="pom")

    def pom_parent(self, pom: POM) -> POM | None:
        """
        Resolve and return the parent POM, or None if no parent is declared.

        Args:
            pom: The POM whose parent to resolve.

        Returns:
            The parent POM object, or None if no parent.
        """

        if pom.element("parent") is None:
            return None

        g = pom.value("parent/groupId")
        a = pom.value("parent/artifactId")
        v = pom.value("parent/version")
        assert g and a and v
        relativePath = pom.value("parent/relativePath")

        if (
            isinstance(pom.source, Path)
            and relativePath
            and (parent_path := pom.source / relativePath).exists()
        ):
            # Use locally available parent POM file.
            parent_pom = POM(parent_path)
            if (
                g == parent_pom.groupId
                and a == parent_pom.artifactId
                and v == parent_pom.version
            ):
                return parent_pom

        pom_artifact = self.project(g, a).at_version(v).artifact(packaging="pom")
        return POM(pom_artifact.resolve())

    def pom_dependencies(self, pom: POM, managed: bool = False) -> list[Dependency]:
        """
        Extract dependencies from POM as Dependency objects.

        Args:
            pom: The POM from which to extract dependencies.
            managed: If True, extract from dependencyManagement instead of dependencies.

        Returns:
            List of Dependency objects.
        """
        xpath = "dependencies/dependency"
        if managed:
            xpath = f"dependencyManagement/{xpath}"
        return [self.parse_dependency_element(el) for el in pom.elements(xpath)]


class Project:
    """
    This is a Maven project: i.e. a groupId+artifactId (G:A) pair.
    """

    def __init__(self, context: MavenContext, groupId: str, artifactId: str):
        self.context = context
        self.groupId = groupId
        self.artifactId = artifactId
        self._metadata: Metadata | None = None

    def __eq__(self, other):
        return (
            other is not None
            and self.groupId == other.groupId
            and self.artifactId == other.artifactId
        )

    def __hash__(self):
        return hash((self.groupId, self.artifactId))

    def __str__(self):
        return coord2str(self.groupId, self.artifactId)

    @property
    def path_prefix(self) -> Path:
        """
        Relative directory where artifacts of this project are organized.
        E.g. org.jruby:jruby-core -> org/jruby/jruby-core
        """
        return Path(*self.groupId.split("."), self.artifactId)

    def at_version(self, version: str) -> Component:
        """
        Fix this project (G:A) at a particular version (G:A:V).

        Args:
            version: The version of the project.

        Returns:
            Component at the given version.
        """
        return Component(self, version)

    @property
    def metadata(self) -> Metadata:
        """Maven metadata about this project, encompassing all known sources."""
        if self._metadata is None:
            # Aggregate all locally available project maven-metadata.xml sources.
            repo_cache_dir = self.context.repo_cache / self.path_prefix
            paths = [p for p in repo_cache_dir.glob("maven-metadata*.xml")] + [
                r / self.path_prefix / "maven-metadata.xml"
                for r in self.context.local_repos
            ]
            self._metadata = Metadatas([MetadataXML(p) for p in paths if p.exists()])
        return self._metadata

    def update(self) -> None:
        """Update metadata from remote sources."""
        import requests

        repo_cache_dir = self.context.repo_cache / self.path_prefix
        repo_cache_dir.mkdir(parents=True, exist_ok=True)

        # Try to fetch maven-metadata.xml from each remote repository
        for repo_name, repo_url in self.context.remote_repos.items():
            metadata_url = f"{repo_url}/{self.path_prefix}/maven-metadata.xml"
            try:
                response = requests.get(metadata_url, timeout=self.context.timeout)
                if response.status_code == 200:
                    # Save to local cache with repo name suffix
                    metadata_file = repo_cache_dir / f"maven-metadata-{repo_name}.xml"
                    with open(metadata_file, "wb") as f:
                        f.write(response.content)
            except requests.RequestException:
                # Silently ignore failures - metadata might not be available
                pass

        # Force reload of metadata
        self._metadata = None

    @property
    def release(self) -> str | None:
        """
        The newest release version of this project across all repositories.

        This is jgo's smart implementation of Maven's RELEASE version resolution.

        Algorithm:
        - For single repository: returns the <release> tag value
        - For multiple repositories:
          1. Collects all versions from all repositories
          2. Filters out SNAPSHOT versions
          3. Uses Maven version ordering to find the truly newest version

        Deviation from Maven:
        Maven returns the release from the most recently updated repository,
        which can be incorrect when newer releases exist elsewhere. jgo
        correctly compares version numbers across all repositories.

        Example:
        - Maven Central has versions up to 1.54p (updated 2025-02-18)
        - maven.scijava.org has versions up to 1.48q (updated 2025-12-22)
        - Maven returns: 1.48q (wrong - from most recently updated repo)
        - jgo returns: 1.54p (correct - truly newest version)

        See docs/version-resolution.md for full details.

        Returns:
            The newest non-SNAPSHOT version string, or None if no releases exist.
        """

        # For single metadata source, use its release tag
        if not isinstance(self.metadata, Metadatas):
            return self.metadata.release

        # For multiple repos: find newest non-SNAPSHOT version across all
        release_versions = [
            v for v in self.metadata.versions if not v.endswith("-SNAPSHOT")
        ]
        if not release_versions:
            return None

        return max(release_versions, key=cmp_to_key(compare_versions))

    @property
    def latest(self) -> str | None:
        """
        The highest version of this project across all repositories.

        This is jgo's smart implementation of Maven's LATEST version resolution.

        Algorithm:
        - For single repository: returns the <latest> tag value (or lastVersion)
        - For multiple repositories:
          1. Collects all versions from all repositories
          2. Uses Maven version ordering to find the highest version
          (Unlike release, this INCLUDES SNAPSHOT versions)

        Rationale:
        LATEST means "highest version number" not "most recently deployed".
        This handles multi-branch development correctly:
        - If you have 2.x-SNAPSHOT (main) and 1.x-SNAPSHOT (maintenance)
        - LATEST returns 2.x-SNAPSHOT even if 1.x was deployed more recently
        - This avoids ping-ponging between branches based on commit timing

        Limitation:
        Projects using unconventional SNAPSHOT naming (e.g., always reusing
        "1.x-SNAPSHOT" for current development regardless of actual version)
        may not get expected results, as version comparison cannot determine
        temporal relationships without external knowledge.

        Deviation from Maven:
        jgo correctly compares versions across repositories, while Maven uses
        the most recently updated repository (same bug as with RELEASE).

        See docs/version-resolution.md for full details.

        Returns:
            The highest version string (may be SNAPSHOT or release),
            or None if no versions exist.
        """

        # For single metadata source, use its latest tag (or fall back to lastVersion)
        if not isinstance(self.metadata, Metadatas):
            return self.metadata.latest or self.metadata.lastVersion

        # For multiple repos: find highest version (including SNAPSHOTs) across all
        all_versions = self.metadata.versions
        if not all_versions:
            return None

        return max(all_versions, key=cmp_to_key(compare_versions))

    def versions(
        self, releases: bool = True, snapshots: bool = False, locked: bool = False
    ) -> list[Component]:
        """
        Get a list of all known versions of this project.

        Args:
            releases:
                If True, include release versions (those not ending in -SNAPSHOT) in the results.
            snapshots:
                If True, include snapshot versions (those ending in -SNAPSHOT) in the results.
            locked:
                If True, returned snapshot versions will include the timestamp or "lock" flavor
                of the version strings;
                For example: 2.94.3-20230706.150124-1 rather than 2.94.3-SNAPSHOT.
                As such, there may be more entries returned than when this flag is False.

        Returns:
            List of Component objects, each of which represents a known version.
        """
        if locked:
            # Should multiple timestamped snapshots at the same snapshot
            # version be one Component, or multiple Components?
            raise RuntimeError("Locked snapshot reporting is unimplemented")
        return [
            self.at_version(v)
            for v in self.metadata.versions
            if (
                (snapshots and v.endswith("-SNAPSHOT"))
                or (releases and not v.endswith("-SNAPSHOT"))
            )
        ]


class Component:
    """
    This is a Project at a particular version -- i.e. a G:A:V.
    One POM per component.
    """

    def __init__(self, project: Project, version: str):
        self.project = project
        self.version = version
        self._resolved_version: str | None = None
        self._snapshot_metadata: SnapshotMetadataXML | None = None

    def __eq__(self, other):
        return (
            other is not None
            and self.project == other.project
            and self.version == other.version
        )

    def __hash__(self):
        return hash((self.project, self.version))

    def __str__(self):
        return coord2str(self.groupId, self.artifactId, self.resolved_version)

    @property
    def context(self) -> MavenContext:
        """The component's Maven context."""
        return self.project.context

    @property
    def groupId(self) -> str:
        """The component's groupId."""
        return self.project.groupId

    @property
    def artifactId(self) -> str:
        """The component's artifactId."""
        return self.project.artifactId

    @property
    def resolved_version(self) -> str:
        """
        Get the resolved version, converting RELEASE/LATEST tokens to actual versions.
        """
        if self._resolved_version is not None:
            return self._resolved_version

        # Check if version needs resolution
        if self.version in ("RELEASE", "LATEST"):
            # Fetch metadata from remote if needed
            if not self.project.metadata or not self.project.metadata.versions:
                self.project.update()

            # Resolve to actual version
            if self.version == "RELEASE":
                resolved = self.project.release
            else:  # LATEST
                resolved = self.project.latest

            if not resolved:
                raise RuntimeError(
                    f"Could not resolve {self.version} version for "
                    f"{self.project.groupId}:{self.project.artifactId}"
                )

            self._resolved_version = resolved
            return resolved

        # Version is already concrete
        return self.version

    @property
    def snapshot_metadata(self) -> SnapshotMetadataXML | None:
        """
        Get SNAPSHOT metadata for this component version.
        Only applicable for SNAPSHOT versions.

        Returns:
            SnapshotMetadataXML if this is a SNAPSHOT version, None otherwise.
        """
        if not self.resolved_version.endswith("-SNAPSHOT"):
            return None

        if self._snapshot_metadata is None:
            _log = logging.getLogger(__name__)

            # Load from cache if available
            cache_dir = self.context.repo_cache / self.path_prefix
            paths = (
                list(cache_dir.glob("maven-metadata*.xml"))
                if cache_dir.exists()
                else []
            )

            if paths:
                # Use most recent metadata
                newest = max(paths, key=lambda p: p.stat().st_mtime)
                _log.debug(f"Loading SNAPSHOT metadata from {newest}")
                self._snapshot_metadata = SnapshotMetadataXML(newest)
            else:
                _log.debug(f"No cached SNAPSHOT metadata found in {cache_dir}")

        return self._snapshot_metadata

    def update_snapshot_metadata(self) -> None:
        """
        Fetch SNAPSHOT metadata from remote repositories.
        Similar to Project.update() but for version-level metadata.
        """
        if not self.resolved_version.endswith("-SNAPSHOT"):
            return

        import logging

        import requests

        _log = logging.getLogger(__name__)

        cache_dir = self.context.repo_cache / self.path_prefix
        cache_dir.mkdir(parents=True, exist_ok=True)

        _log.debug(f"Fetching SNAPSHOT metadata for {self}")

        # Try to fetch maven-metadata.xml from each remote repository
        found = False
        for repo_name, repo_url in self.context.remote_repos.items():
            # Convert Path to forward-slash string for URL
            path_str = str(self.path_prefix).replace("\\", "/")
            metadata_url = f"{repo_url}/{path_str}/maven-metadata.xml"
            try:
                _log.debug(f"Trying {metadata_url}")
                response = requests.get(metadata_url, timeout=self.context.timeout)
                if response.status_code == 200:
                    # Save to local cache with repo name suffix
                    metadata_file = cache_dir / f"maven-metadata-{repo_name}.xml"
                    metadata_file.write_bytes(response.content)
                    _log.info(
                        f"Downloaded SNAPSHOT metadata for {self} from {repo_name}"
                    )
                    found = True
            except requests.RequestException as e:
                _log.debug(f"Failed to fetch SNAPSHOT metadata from {repo_name}: {e}")

        if not found:
            _log.warning(f"No SNAPSHOT metadata found for {self} in any repository")

        # Force reload of metadata
        self._snapshot_metadata = None

    @property
    def path_prefix(self) -> Path:
        """
        Relative directory where artifacts of this component are organized.
        E.g. org.jruby:jruby-core:9.3.3.0 -> org/jruby/jruby-core/9.3.3.0
        """
        return self.project.path_prefix / self.resolved_version

    def artifact(
        self, classifier: str = DEFAULT_CLASSIFIER, packaging: str = DEFAULT_PACKAGING
    ) -> Artifact:
        """
        Get an artifact (G:A:P:C:V) associated with this component.

        Args:
            classifier: Classifier of the artifact.
            packaging: Packaging/type of the artifact.

        Returns:
            The Artifact object representing this component
            with particular classifier and packaging.
        """
        return Artifact(self, classifier, packaging)

    def pom(self) -> POM:
        """
        Get a data structure with the contents of the POM.

        Returns:
            The POM content.
        """

        pom_artifact = self.artifact(packaging="pom")
        return POM(pom_artifact.resolve())


class Artifact:
    """
    This is a Component plus classifier and packaging (G:A:P:C:V).
    One file per artifact.
    """

    def __init__(
        self,
        component: Component,
        classifier: str = DEFAULT_CLASSIFIER,
        packaging: str = DEFAULT_PACKAGING,
    ):
        self.component = component
        self.classifier = classifier
        self.packaging = packaging

    def __eq__(self, other):
        return (
            other is not None
            and self.component == other.component
            and self.classifier == other.classifier
            and self.packaging == other.packaging
        )

    def __hash__(self):
        return hash((self.component, self.classifier, self.packaging))

    def __str__(self):
        return coord2str(
            self.groupId, self.artifactId, self.version, self.classifier, self.packaging
        )

    @property
    def context(self) -> MavenContext:
        return self.component.context

    @property
    def groupId(self) -> str:
        """The artifact's groupId."""
        return self.component.groupId

    @property
    def artifactId(self) -> str:
        """The artifact's artifactId."""
        return self.component.artifactId

    @property
    def version(self) -> str:
        """The artifact's version (resolved if RELEASE/LATEST)."""
        return self.component.resolved_version

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        """
        Get the artifact's unique key for deduplication.

        Uses resolved version to ensure artifacts that resolve to the same
        concrete version are treated as duplicates (e.g., RELEASE → 2.0.0).

        Returns:
            Tuple of (groupId, artifactId, resolved_version, classifier, packaging)
        """
        return (
            self.component.groupId,
            self.component.artifactId,
            self.component.resolved_version,
            self.classifier,
            self.packaging,
        )

    @property
    def filename(self) -> str:
        """
        Filename portion of the artifact path. E.g.:
        - g=org.python a=jython v=2.7.0 -> jython-2.7.0.jar
        - g=org.lwjgl a=lwjgl v=3.3.1 c=natives-linux -> lwjgl-3.3.1-natives-linux.jar
        - g=org.scijava a=scijava-common v=2.94.2 p=pom -> scijava-common-2.94.2.pom
        - SNAPSHOT: my-lib-1.0-20230706.150124-1.jar (timestamped for download)
        """
        version = (
            self.component.resolved_version
        )  # Use resolved version (LATEST -> actual version)

        # For SNAPSHOTs, get the timestamped version
        if version.endswith("-SNAPSHOT"):
            metadata = self.component.snapshot_metadata
            if metadata:
                timestamped = metadata.get_timestamped_version(
                    packaging=self.packaging, classifier=self.classifier
                )
                if timestamped:
                    version = timestamped

        classifier_suffix = f"-{self.classifier}" if self.classifier else ""
        return f"{self.artifactId}-{version}{classifier_suffix}.{self.packaging}"

    @property
    def cached_filename(self) -> str:
        """
        Filename used in the local cache.
        For SNAPSHOTs, this uses the SNAPSHOT version, not the timestamped version.
        E.g., my-lib-1.0-SNAPSHOT.jar (not my-lib-1.0-20230706.150124-1.jar)
        """
        version = (
            self.component.resolved_version
        )  # Use resolved version (LATEST -> SNAPSHOT)
        classifier_suffix = f"-{self.classifier}" if self.classifier else ""
        return f"{self.artifactId}-{version}{classifier_suffix}.{self.packaging}"

    @property
    def cached_path(self) -> Path | None:
        """
        Path to the artifact in the linked context's local repository cache.
        Might not actually exist! This just returns where it *would be* if present.

        For SNAPSHOT versions, uses the SNAPSHOT version in the filename,
        not the timestamped version (follows Maven convention).
        """
        return (
            self.context.repo_cache / self.component.path_prefix / self.cached_filename
            if self.context.repo_cache
            else None
        )

    def resolve(self) -> Path:
        """
        Resolve a local path to the artifact, downloading it as needed:

        1. If present in the linked local repository cache, use that path.
        2. Else if present in a linked locally available repository storage directory,
           use that path.
        3. Otherwise, invoke the context's resolver to download it.
        """

        # Check Maven local repository cache first if available.
        cached_file = self.cached_path
        if cached_file and cached_file.exists():
            return cached_file

        # Check any locally available Maven repository storage directories.
        for base in self.context.local_repos:
            if self.version.endswith("-SNAPSHOT"):
                # For SNAPSHOTs in local storage, look for timestamped files
                # Pattern: artifactId-baseVersion-timestamp-buildNumber-classifier.packaging
                # Example: my-lib-1.0-20230706.150124-1.jar

                # First try with resolved timestamped filename if we have metadata
                p = base / self.component.path_prefix / self.filename
                if p.exists():
                    return p

                # Fallback: search for any timestamped version in the directory
                # This handles cases where local storage has a different timestamp
                snapshot_dir = base / self.component.path_prefix
                if snapshot_dir.exists():
                    # Extract base version (e.g., "1.0" from "1.0-SNAPSHOT")
                    base_version = self.version[:-9]  # Remove "-SNAPSHOT"
                    classifier_suffix = f"-{self.classifier}" if self.classifier else ""

                    # Pattern: artifactId-baseVersion-timestamp-buildNumber[-classifier].packaging
                    import re

                    pattern = re.compile(
                        rf"{re.escape(self.artifactId)}-"
                        rf"{re.escape(base_version)}-"
                        r"\d{8}\.\d{6}-\d+"
                        rf"{re.escape(classifier_suffix)}"
                        rf"\.{re.escape(self.packaging)}"
                    )

                    # Find matching files, use newest
                    matching_files = [
                        f
                        for f in snapshot_dir.glob(
                            f"{self.artifactId}-*.{self.packaging}"
                        )
                        if pattern.match(f.name)
                    ]

                    if matching_files:
                        # Return the most recently modified file
                        return max(matching_files, key=lambda f: f.stat().st_mtime)
            else:
                # Non-SNAPSHOT: use exact filename
                p = base / self.component.path_prefix / self.filename
                if p.exists():
                    return p

        # Artifact was not found locally; need to download it.
        result = self.context.resolver.download(self)
        if result is None:
            raise RuntimeError(f"Could not resolve artifact: {self}")
        return result

    def md5(self) -> str:
        """Compute the MD5 hash of the artifact."""
        return self._checksum("md5", md5)

    def sha1(self) -> str:
        """Compute the SHA1 hash of the artifact."""
        return self._checksum("sha1", sha1)

    def _checksum(self, suffix, func):
        p = self.resolve()
        checksum_path = p.parent / f"{p.name}.{suffix}"
        return text(checksum_path) or func(binary(p)).hexdigest()


class Dependency:
    """
    This is an Artifact with scope, optional flag, and exclusions list.
    """

    def __init__(
        self,
        artifact: Artifact,
        scope: str | None = None,
        optional: bool = False,
        exclusions: Iterable[Project] | None = None,
        raw: bool = False,
    ):
        # NB: scope can be None here - it will be set by dependency management injection
        # or default to "compile" later in the model building process
        self.artifact = artifact
        self.scope = scope
        self.optional = optional
        self.exclusions: tuple[Project, ...] = (
            tuple() if exclusions is None else tuple(exclusions)
        )
        self.raw = raw

    def __str__(self):
        return coord2str(
            self.groupId,
            self.artifactId,
            self.version,
            self.classifier,
            self.type,
            self.scope,
            self.optional,
        )

    @property
    def context(self) -> MavenContext:
        """The dependency's Maven context."""
        return self.artifact.context

    @property
    def groupId(self) -> str:
        """The dependency's groupId."""
        return self.artifact.groupId

    @property
    def artifactId(self) -> str:
        """The dependency's artifactId."""
        return self.artifact.artifactId

    @property
    def version(self) -> str:
        """The dependency's version."""
        return self.artifact.version

    @property
    def classifier(self) -> str:
        """The dependency's classifier."""
        return self.artifact.classifier

    @property
    def type(self) -> str:
        """The dependency's packaging/type."""
        return self.artifact.packaging

    def set_version(self, version: str) -> None:
        """
        Alter the dependency's version.

        Args:
            version: The new version to use.
        """
        assert isinstance(version, str)
        self.artifact.component.version = version
        self.artifact.component._resolved_version = None


@dataclass
class DependencyNode:
    """
    Represents a dependency in a dependency tree.

    This data structure is built during dependency resolution and captures
    the parent-child relationships discovered by the breadth-first traversal.
    It's also used for formatting dependency lists and trees.
    """

    dep: Dependency
    children: list[DependencyNode] = field(default_factory=list)

    def __str__(self):
        return str(self.dep)


def create_pom(dependencies: list[Dependency], boms: list[Component] | None) -> POM:
    """
    Create a synthetic wrapper POM for multi-component resolution.

    Args:
        dependencies: List of dependencies to add
        boms: Optional list of components to import in dependencyManagement

    Returns:
        POM object created from synthetic XML string
    """

    # Generate the POM XML content
    pom_xml = generate_pom_xml(dependencies, boms)

    # Create POM object from XML string
    return POM(pom_xml)


def generate_pom_xml(
    dependencies: list[Dependency], boms: list[Component] | None = None
) -> str:
    """
    Generate a wrapper POM XML string for multi-component resolution.

    This POM includes:
    - All dependencies as direct dependencies (with classifier/type/scope)
    - BOMs in dependencyManagement section (if provided)
    - Repository configuration from the first dependency's context

    Args:
        dependencies: List of dependencies to add
        boms: Optional list of components to import in dependencyManagement

    Returns:
        Complete POM XML as a string
    """
    if not dependencies:
        raise ValueError("At least one dependency is required")

    if boms is None:
        boms = []

    # Generate dependencyManagement section
    dep_mgmt_entries = []
    for bom in boms:
        dep_mgmt_entries.append(
            f"""        <dependency>
            <groupId>{bom.groupId}</groupId>
            <artifactId>{bom.artifactId}</artifactId>
            <version>{bom.resolved_version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>"""
        )

    dep_mgmt_section = "\n".join(dep_mgmt_entries) if dep_mgmt_entries else ""
    dep_mgmt_block = (
        f"""
    <dependencyManagement>
        <dependencies>
{dep_mgmt_section}
        </dependencies>
    </dependencyManagement>
"""
        if dep_mgmt_section
        else ""
    )

    # Generate dependencies section
    dep_entries = []
    for dep in dependencies:
        # For MANAGED versions, omit the <version> tag entirely.
        # The Model will resolve the version from imported BOMs' dependencyManagement.
        lines = [
            f"            <groupId>{dep.groupId}</groupId>",
            f"            <artifactId>{dep.artifactId}</artifactId>",
        ]
        if dep.artifact.component.version != "MANAGED":
            lines.append(f"            <version>{dep.version}</version>")
        if dep.classifier:
            lines.append(f"            <classifier>{dep.classifier}</classifier>")
        if dep.type and dep.type != "jar":
            lines.append(f"            <type>{dep.type}</type>")
        if dep.scope and dep.scope not in (None, "compile"):
            lines.append(f"            <scope>{dep.scope}</scope>")
        if dep.exclusions:
            excl_lines = ["            <exclusions>"]
            for excl in dep.exclusions:
                excl_lines += [
                    "                <exclusion>",
                    f"                    <groupId>{excl.groupId}</groupId>",
                    f"                    <artifactId>{excl.artifactId}</artifactId>",
                    "                </exclusion>",
                ]
            excl_lines.append("            </exclusions>")
            lines.extend(excl_lines)

        dep_entries.append(
            "        <dependency>\n" + "\n".join(lines) + "\n        </dependency>"
        )

    deps_section = "\n".join(dep_entries)

    # Generate repositories section
    repos_entries = []
    for repo_id, repo_url in dependencies[0].context.remote_repos.items():
        repos_entries.append(
            f"""        <repository>
            <id>{repo_id}</id>
            <url>{repo_url}</url>
        </repository>"""
        )

    repos_section = "\n".join(repos_entries) if repos_entries else ""
    repositories_block = (
        f"""
    <repositories>
{repos_section}
    </repositories>
"""
        if repos_section
        else ""
    )

    # Generate complete POM XML
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <groupId>org.apposed.jgo</groupId>
    <artifactId>INTERNAL-WRAPPER</artifactId>
    <version>0-SNAPSHOT</version>
{dep_mgmt_block}
    <dependencies>
{deps_section}
    </dependencies>
{repositories_block}</project>
"""


class Resolver(ABC):
    """
    Logic for doing non-trivial Maven-related things, including:
    * downloading and caching an artifact from a remote repository; and
    * determining the dependencies of a particular Maven component.
    """

    @abstractmethod
    def download(self, artifact: Artifact) -> Path | None:
        """
        Download an artifact file from a remote repository.

        Args:
            artifact: The artifact for which a local path should be resolved.

        Returns:
            Local path to the saved artifact, or None if the artifact cannot be resolved.
        """
        ...

    @abstractmethod
    def resolve(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[list[Dependency], list[Dependency]]:
        """
        Resolve dependencies for the given Maven dependencies.

        BOMs are computed internally from dependencies marked as non-raw.

        Args:
            dependencies: The dependencies for which to resolve transitive deps.
            transitive: Whether to include transitive dependencies.
            optional_depth: Maximum depth at which to include optional dependencies.

        Returns:
            Tuple of (resolved_inputs, resolved_transitive) where:
            - resolved_inputs: Input deps with MANAGED versions resolved
            - resolved_transitive: Transitive dependencies (excludes the inputs themselves)
        """
        ...

    @abstractmethod
    def get_dependency_list(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[DependencyNode, list[DependencyNode]]:
        """
        Get the flat list of resolved dependencies as data structures.

        This returns the dependency data in a common format that can be used by
        the dependency printing logic to ensure consistent output across resolvers.

        Args:
            dependencies: The dependencies for which to get the list.
            transitive: If False, return only direct dependencies.
            optional_depth: Maximum depth at which to include optional dependencies.

        Returns:
            Tuple of (root_node, dependencies_list) where root_node is the
            root and dependencies_list is the sorted list of all
            resolved transitive dependencies.
        """
        ...

    @abstractmethod
    def get_dependency_tree(
        self, dependencies: list[Dependency], optional_depth: int = 0
    ) -> DependencyNode:
        """
        Get the full dependency tree as a data structure.

        This returns the dependency data in a common format that can be used by
        the dependency printing logic to ensure consistent output across resolvers.

        Args:
            dependencies: The dependencies for which to get the tree.
            optional_depth: Maximum depth at which to include optional dependencies.
                Defaults to 0, matching Maven's behavior.

        Returns:
            DependencyNode representing the root with children populated
            recursively to form the complete dependency tree.
        """
        ...
