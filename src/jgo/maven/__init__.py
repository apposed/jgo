"""
Maven dependency resolution for Python.

This module provides pure-Python Maven functionality including:
- Dependency resolution (transitive dependencies, scopes, exclusions)
- POM parsing and property interpolation
- Metadata querying (available versions, release/snapshot)
- Artifact downloading from Maven repositories

Class Hierarchy
---------------
Maven concepts are represented as a hierarchy of "smart" objects that
actively perform Maven operations (resolution, downloading, POM parsing).
Each level adds more specificity:

    MavenContext          — repositories + resolver configuration
      └── Project [G:A]   — groupId:artifactId pair; metadata access
            └── Component [G:A:V]  — a Project at a specific version; owns the POM
                  └── Artifact [G:A:P:C:V]  — one file (JAR, POM, sources, …)
                        └── Dependency [G:A:P:C:V:S]  — Artifact + scope/optional/exclusions

For lightweight coordinate data structures without Maven logic, see jgo.parse.

Key Classes
-----------
MavenContext
    Entry point for all Maven operations.  Holds repository configuration
    (local cache path, additional local repo storage paths, remote repo
    name→URL map) and the Resolver implementation to use.

    >>> from jgo.maven import MavenContext
    >>> ctx = MavenContext()  # defaults (Maven Central)
    >>> ctx = MavenContext(remote_repos={
    ...     "central": "https://repo1.maven.org/maven2",
    ...     "scijava": "https://maven.scijava.org/content/groups/public",
    ... })
    >>> dep = ctx.create_dependency("org.python:jython-standalone:2.7.3")
    >>> dep.artifact.resolve()  # Path to local JAR (downloads if needed)

Project
    A groupId:artifactId (G:A) pair with access to project-level Maven
    metadata (available versions, release/latest version).

    >>> project = ctx.project("org.python", "jython-standalone")
    >>> project.release     # Newest non-SNAPSHOT version string
    >>> project.latest      # Highest version (may be SNAPSHOT)
    >>> project.versions()  # List of Component objects for all known versions

Component
    A Project pinned to a specific version (G:A:V).  Resolves special tokens
    ``RELEASE`` and ``LATEST`` to concrete version strings by consulting
    project metadata.

    >>> component = project.at_version("2.7.3")
    >>> component.pom()       # POM data structure
    >>> component.artifact()  # Default JAR artifact

Artifact
    A Component with a classifier and packaging type (G:A:P:C:V).  Knows how
    to locate itself locally (checking cache and local repos) or download from
    a remote repository.

    >>> artifact = component.artifact(classifier="sources", type="jar")
    >>> path = artifact.resolve()  # Downloads if not cached

Dependency
    An Artifact enriched with Maven dependency metadata: scope (compile,
    runtime, test, …), optional flag, and exclusion list.

    >>> dep = ctx.create_dependency("org.python:jython-standalone:2.7.3")
    >>> dep.scope     # e.g. "compile"
    >>> dep.optional  # bool

Resolvers
---------
PythonResolver (default)
    Pure-Python resolver that parses POMs, handles BOMs/imports, and
    downloads JARs directly via HTTP — no ``mvn`` binary required.

MvnResolver
    Shells out to the ``mvn`` command line tool.  Useful when precise
    Maven behaviour is required or for complex multi-module builds.

Both implement the abstract ``Resolver`` interface, which exposes:
- ``download(artifact)`` — fetch one artifact file
- ``resolve(dependencies)`` — resolve full transitive dependency graph
- ``get_dependency_list(dependencies)`` — flat list of resolved deps
- ``get_dependency_tree(dependencies)`` — full dependency tree

Version Utilities
-----------------
MavenVersion, VersionRange, parse_version_range, version_in_range
    Maven version comparison and range support (e.g., ``[1.0,2.0)``).

compare_versions(v1, v2)
    Return negative/zero/positive (like ``cmp``) using Maven ordering rules.

POM / Metadata Classes
-----------------------
POM
    Parsed project object model with property interpolation and XPath-style
    element access.

Model
    Fully-built effective POM after parent inheritance and property
    resolution. Used internally by PythonResolver.

Metadata / MetadataXML / Metadatas
    Maven ``maven-metadata.xml`` data — available versions, release/latest
    markers, and snapshot timestamp resolution.

Example — Resolve Dependencies
-------------------------------
>>> from jgo.maven import MavenContext
>>> ctx = MavenContext()
>>> dep = ctx.create_dependency("org.python:jython-standalone:2.7.3")
>>> resolved_inputs, transitive = ctx.resolver.resolve([dep])
>>> for d in transitive:
...     print(d.groupId, d.artifactId, d.version, d.scope)

Example — Inspect Available Versions
--------------------------------------
>>> project = ctx.project("org.scijava", "scijava-common")
>>> project.release    # e.g. '2.99.3'
>>> [c.version for c in project.versions()]
"""

from ..util.http import RepositoryAccessDenied
from ._central import coordinates_by_sha1, solr_search
from ._core import (
    Artifact,
    Component,
    Dependency,
    DependencyNode,
    MavenContext,
    Project,
    Resolver,
)
from ._handlers import artifact_handler
from ._metadata import Metadata, Metadatas, MetadataXML
from ._model import Model
from ._pom import POM, XML
from ._profile import ProfileConstraints, detect_os_properties
from ._resolver import MvnResolver, PythonResolver
from ._version import (
    MavenVersion,
    VersionRange,
    compare_semver,
    compare_versions,
    is_semver_1x,
    parse_version_range,
    version_in_range,
)

__all__ = [
    # central
    "coordinates_by_sha1",
    "solr_search",
    # core
    "Artifact",
    "Component",
    "Dependency",
    "DependencyNode",
    "MavenContext",
    "Project",
    # handlers
    "artifact_handler",
    # metadata
    "Metadata",
    "Metadatas",
    "MetadataXML",
    # model
    "Model",
    # pom
    "POM",
    "XML",
    # profile
    "ProfileConstraints",
    "detect_os_properties",
    # resolver
    "MvnResolver",
    "PythonResolver",
    "RepositoryAccessDenied",
    "Resolver",
    # version
    "MavenVersion",
    "VersionRange",
    "compare_semver",
    "compare_versions",
    "is_semver_1x",
    "parse_version_range",
    "version_in_range",
]
