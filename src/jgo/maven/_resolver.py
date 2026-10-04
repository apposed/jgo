"""
Maven artifact resolvers.
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
from subprocess import run
from typing import TYPE_CHECKING

import requests

from ..parse import Coordinate
from ..util import http
from . import Resolver
from ._core import Dependency, DependencyNode, create_pom
from ._model import Model
from ._pom import write_temp_pom
from ._profile import ProfileConstraints, detect_os_properties

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager
    from pathlib import Path

    from ._core import Artifact, Component

    # Type for progress callback:
    # Receives (filename, total_size) and returns a context manager
    # that yields an update function that accepts bytes_count
    ProgressCallback = Callable[
        [str, int], AbstractContextManager[Callable[[int], None]]
    ]


_log = logging.getLogger(__name__)


def _build_dependency_list(
    input_deps: list[Dependency], resolved_transitive: list[Dependency]
) -> tuple[DependencyNode, list[DependencyNode]]:
    """
    Common logic for building dependency list structure.

    Args:
        input_deps: List of input dependencies
        resolved_transitive: List of resolved transitive dependencies

    Returns:
        Tuple of (root_node, dependency_nodes)
    """
    root = _create_root(input_deps)

    # Add input dependencies as children of root
    for dep in input_deps:
        root.children.append(DependencyNode(dep))

    # Sort for consistent output
    resolved_transitive.sort(key=lambda d: (d.groupId, d.artifactId, d.version))

    # Convert to DependencyNode list
    dep_nodes = [DependencyNode(dep) for dep in resolved_transitive]

    return root, dep_nodes


def _compute_boms(dependencies: list[Dependency]) -> list[Component] | None:
    """
    Compute BOMs from dependencies: non-raw, non-MANAGED, deduplicated by G:A:V.

    Dependencies marked as raw are excluded from BOM management.
    MANAGED-versioned dependencies are excluded since they consume
    dependency management rather than provide it.
    """
    seen: set[tuple[str, str, str]] = set()
    boms: list[Component] = []
    for dep in dependencies:
        if not dep.raw and dep.artifact.component.version != "MANAGED":
            key = (dep.groupId, dep.artifactId, dep.version)
            if key not in seen:
                seen.add(key)
                boms.append(dep.artifact.component)
    return boms or None


def _filter_component_deps(
    deps: list[Dependency], input_deps: list[Dependency]
) -> list[Dependency]:
    """Remove input dependencies themselves from resolved dependency list."""
    input_coords = {
        (dep.groupId, dep.artifactId, dep.version)
        for dep in input_deps
        if dep.artifact.component.version != "MANAGED"
    }
    return [
        dep
        for dep in deps
        if (dep.groupId, dep.artifactId, dep.version) not in input_coords
    ]


def _create_root(dependencies: list[Dependency]) -> DependencyNode:
    """Create a synthetic root node for multi-component resolution."""
    return DependencyNode(
        Dependency(
            dependencies[0]
            .context.project("org.apposed.jgo", "INTERNAL-WRAPPER")
            .at_version("0-SNAPSHOT")
            .artifact(packaging="pom")
        )
    )


def _resolve_component_inputs(
    dependencies: list[Dependency],
    resolved_deps: list[Dependency],
) -> tuple[list[Dependency], set[tuple[str, str, str, str, str]]]:
    """
    Resolve input dependencies and build artifact key set.

    For MANAGED dependencies, finds their resolved versions in resolved_deps.
    Returns resolved inputs and a set of artifact keys to filter out
    from transitive dependencies.

    Args:
        dependencies: Original input dependencies
        resolved_deps: All resolved dependencies (inputs + transitive)

    Returns:
        Tuple of (resolved_inputs, artifact_keys) where:
        - resolved_inputs: Input deps with MANAGED versions resolved
        - artifact_keys: Set of artifact.key tuples for deduplication
    """
    resolved_inputs = []
    artifact_keys: set[tuple[str, str, str, str, str]] = set()

    for input_dep in dependencies:
        comp = input_dep.artifact.component
        if comp.version == "MANAGED":
            # Find the resolved version in resolved_deps
            for dep in resolved_deps:
                if (
                    dep.groupId == comp.groupId
                    and dep.artifactId == comp.artifactId
                    and dep.classifier == input_dep.classifier
                    and dep.type == input_dep.type
                ):
                    resolved_inputs.append(dep)
                    artifact_keys.add(dep.artifact.key)
                    break
        else:
            resolved_inputs.append(input_dep)
            artifact_keys.add(input_dep.artifact.key)

    return resolved_inputs, artifact_keys


def _verify_remote_sha1(
    artifact_url: str, actual_sha1: str, filename: str, timeout: int
) -> None:
    """
    Verify a downloaded artifact against the remote SHA1 checksum file.

    Silently skips if the checksum file is unavailable (some repos don't publish them).
    Warns if the checksum is present but does not match.
    """
    try:
        response = http.get(f"{artifact_url}.sha1", timeout=timeout)
    except requests.RequestException as e:
        _log.debug(f"Could not fetch checksum for {filename}: {e}")
        return

    if response.status_code != 200:
        _log.debug(f"No remote checksum for {filename} (HTTP {response.status_code})")
        return

    # SHA1 files are either bare hex or "hex  filename"
    expected_sha1 = response.text.strip().split()[0]
    if actual_sha1 != expected_sha1:
        _log.warning(
            f"Checksum mismatch for {filename}: "
            f"expected {expected_sha1}, got {actual_sha1}"
        )
    else:
        _log.debug(f"Checksum verified: {filename}")


class PythonResolver(Resolver):
    """
    A resolver that works by pure Python code.
    Low overhead, but less feature complete than mvn.
    """

    def __init__(
        self,
        profile_constraints: ProfileConstraints | None = None,
        progress_callback: ProgressCallback | None = None,
        lenient: bool = False,
    ):
        """
        Initialize Python resolver.

        Args:
            profile_constraints: Profile constraints for Maven model building.
                Any None platform fields (os_name, os_family, os_arch) are
                filled in from the current system, matching Maven's behavior
                of always having OS properties available during resolution.
            progress_callback: Optional callback for download progress reporting.
                Receives (filename, total_size) and returns a context manager
                that yields an update function accepting bytes_count.
            lenient: If True, warn instead of failing on unresolvable dependencies.
        """
        if profile_constraints is None:
            profile_constraints = ProfileConstraints()
        if None in (
            profile_constraints.os_name,
            profile_constraints.os_family,
            profile_constraints.os_arch,
        ):
            os_name, os_family, os_arch = detect_os_properties()
            profile_constraints = dataclasses.replace(
                profile_constraints,
                os_name=profile_constraints.os_name or os_name,
                os_family=profile_constraints.os_family or os_family,
                os_arch=profile_constraints.os_arch or os_arch,
            )
        self.profile_constraints = profile_constraints
        self.progress_callback = progress_callback
        self.lenient = lenient

    def download(self, artifact: Artifact) -> Path | None:
        # For SNAPSHOT versions, ensure we have the metadata first
        is_snapshot = artifact.version.endswith("-SNAPSHOT")
        if is_snapshot:
            # Check if we already have metadata cached
            if not artifact.component.snapshot_metadata:
                # Try to fetch metadata from remote repos
                artifact.component.update_snapshot_metadata()

            # If still no metadata, we might be dealing with a remote repo
            # that doesn't have the artifact yet
            if not artifact.component.snapshot_metadata:
                _log.warning(
                    f"No SNAPSHOT metadata found for {artifact.component}. "
                    "Attempting download with SNAPSHOT version..."
                )

        for remote_repo in artifact.context.remote_repos.values():
            # Convert Path to forward-slash string for URL
            path_str = str(artifact.component.path_prefix).replace("\\", "/")
            url = f"{remote_repo}/{path_str}/{artifact.filename}"
            _log.debug(f"Trying {url}")

            # Use streaming to enable progress bar
            response: requests.Response = http.get(
                url, stream=True, timeout=artifact.context.timeout
            )
            if response.status_code == 200:
                # Remote artifact accessed successfully
                cached_file = artifact.cached_path
                assert cached_file is not None
                assert not cached_file.exists()
                cached_file.parent.mkdir(parents=True, exist_ok=True)

                # Get total size from Content-Length header
                total_size = int(response.headers.get("content-length", 0))

                # Hash while streaming to avoid re-reading the file for checksum verification
                sha1 = hashlib.sha1()

                # Use progress callback if provided and size is known
                if self.progress_callback and total_size > 0:
                    with (
                        self.progress_callback(
                            artifact.filename, total_size
                        ) as update_progress,
                        open(cached_file, "wb") as f,
                    ):
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            sha1.update(chunk)
                            update_progress(len(chunk))
                else:
                    with open(cached_file, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            sha1.update(chunk)

                _verify_remote_sha1(
                    url, sha1.hexdigest(), artifact.filename, artifact.context.timeout
                )

                if is_snapshot:
                    _log.info(f"Downloaded SNAPSHOT {artifact} to {cached_file}")
                else:
                    _log.debug(f"Downloaded {artifact} to {cached_file}")
                return cached_file

        raise RuntimeError(
            f"Artifact {artifact} not found in remote repositories "
            f"{artifact.context.remote_repos}"
        )

    def resolve(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[list[Dependency], list[Dependency]]:
        """
        Get all dependencies for the given input dependencies.

        Args:
            dependencies: List of input dependencies
            transitive: Whether to include transitive dependencies
            optional_depth: Maximum depth at which to include optional dependencies

        Returns:
            Tuple of (resolved_inputs, resolved_transitive) where:
            - resolved_inputs: Input deps with MANAGED versions resolved
            - resolved_transitive: Transitive dependencies (excludes the inputs themselves)
        """
        if not dependencies:
            raise ValueError("At least one dependency is required")

        boms = _compute_boms(dependencies)

        pom = create_pom(dependencies, boms)
        model = Model(
            pom,
            dependencies[0].context,
            profile_constraints=self.profile_constraints,
            lenient=self.lenient,
        )
        # When transitive=False, set max_depth=1 to get one level of dependencies
        # from the synthetic wrapper (i.e., the direct dependencies of the components)
        max_depth = 1 if not transitive else None
        deps, _ = model.dependencies(max_depth=max_depth, optional_depth=optional_depth)

        # Build resolved component dependencies
        resolved_inputs, artifact_keys = _resolve_component_inputs(dependencies, deps)

        # Filter out components from transitive deps list
        resolved_transitive = [
            dep for dep in deps if dep.artifact.key not in artifact_keys
        ]

        # Filter out test scope dependencies (they're not needed for running the application)
        resolved_transitive = [
            dep for dep in resolved_transitive if dep.scope not in ("test",)
        ]

        return resolved_inputs, resolved_transitive

    def get_dependency_list(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[DependencyNode, list[DependencyNode]]:
        """
        Get the flat list of resolved dependencies as data structures.

        Args:
            dependencies: List of input dependencies
            transitive: If False, return only direct dependencies
            optional_depth: Maximum depth at which to include optional dependencies

        Returns:
            Tuple of (root_node, flat_list_of_dependencies)
        """
        if not dependencies:
            raise ValueError("At least one dependency is required")

        boms = _compute_boms(dependencies)

        pom = create_pom(dependencies, boms)
        model = Model(
            pom,
            dependencies[0].context,
            profile_constraints=self.profile_constraints,
            lenient=self.lenient,
        )

        # Create resolved input deps list using model.deps for MANAGED versions
        resolved_input_deps = []
        for input_dep in dependencies:
            comp = input_dep.artifact.component
            if comp.version == "MANAGED":
                # Find resolved version in model.deps
                resolved_version = None
                for dep in model.deps.values():
                    if (
                        dep.groupId == comp.groupId
                        and dep.artifactId == comp.artifactId
                    ):
                        resolved_version = dep.version
                        break
                if resolved_version:
                    # Create a new dependency with the resolved version
                    resolved_comp = comp.project.at_version(resolved_version)
                    resolved_dep = Dependency(
                        resolved_comp.artifact(input_dep.classifier, input_dep.type),
                        scope=input_dep.scope,
                        optional=input_dep.optional,
                        exclusions=input_dep.exclusions,
                        raw=input_dep.raw,
                    )
                    resolved_input_deps.append(resolved_dep)
                else:
                    resolved_input_deps.append(input_dep)  # fallback
            else:
                resolved_input_deps.append(input_dep)

        max_depth = 1 if not transitive else None
        deps, _ = model.dependencies(max_depth=max_depth, optional_depth=optional_depth)
        deps = _filter_component_deps(deps, resolved_input_deps)
        deps = [dep for dep in deps if dep.scope not in ("test",)]

        return _build_dependency_list(resolved_input_deps, deps)

    def get_dependency_tree(
        self,
        dependencies: list[Dependency],
        optional_depth: int = 0,
    ) -> DependencyNode:
        """
        Get the full dependency tree as a data structure.

        Args:
            dependencies: List of input dependencies
            optional_depth: Maximum depth at which to include optional dependencies

        Returns:
            Root DependencyNode with full tree structure
        """
        boms = _compute_boms(dependencies)

        # Build model and get dependency tree
        pom = create_pom(dependencies, boms)
        model = Model(
            pom,
            dependencies[0].context,
            profile_constraints=self.profile_constraints,
            lenient=self.lenient,
        )
        _, root = model.dependencies(optional_depth=optional_depth)

        return root


class MvnResolver(Resolver):
    """
    A resolver that works by shelling out to mvn.
    Requires Maven to be installed.
    """

    def __init__(
        self,
        mvn_command: Path,
        update: bool = False,
        debug: bool = False,
        offline: bool = False,
    ):
        self.mvn_command = mvn_command
        self.mvn_flags = ["-B", "-T8"]
        if offline:
            self.mvn_flags.append("-o")
        elif update:
            self.mvn_flags.append("-U")
        if debug:
            self.mvn_flags.append("-X")

    def _create_temp_pom(
        self, dependencies: list[Dependency], boms: list[Component] | None
    ) -> Path:
        """Create temporary POM file for Maven commands."""
        pom = create_pom(dependencies, boms or [])
        temp_pom = write_temp_pom(pom)
        _log.debug(
            f"Created wrapper POM at {temp_pom} with {len(dependencies)} "
            f"dependency(ies) and {len(boms or [])} BOM(s)"
        )
        return temp_pom

    def _filter_dep_scopes(
        self, deps: list[Dependency], scopes: str | list[str]
    ) -> list[Dependency]:
        """
        Filter dependencies to include only specified scopes.

        This method filters Maven dependency results to match the desired scope(s),
        compensating for Maven's quirky -Dscope behavior (which includes test-scoped
        direct dependencies even when -Dscope=runtime is specified:
        apache/maven#10874, apache/maven-dependency-tree#54).

        Args:
            deps: List of dependencies to filter
            scopes: Scope name or list of scope names to include.
                Special scope values:
                - "runtime": includes compile, runtime, provided (default for jgo)
                - "compile": includes compile, provided
                - "test": includes compile, runtime, provided, test
                Or pass an explicit list like ["compile", "runtime"]

        Returns:
            Filtered list including only dependencies with specified scopes
        """
        # Expand scope shortcuts to full scope lists
        if isinstance(scopes, str):
            if scopes == "runtime":
                scope_list = ["compile", "runtime", "provided"]
            elif scopes == "compile":
                scope_list = ["compile", "provided"]
            elif scopes == "test":
                scope_list = ["compile", "runtime", "provided", "test"]
            else:
                # Single scope name
                scope_list = [scopes]
        else:
            scope_list = scopes

        return [dep for dep in deps if dep.scope in scope_list]

    def _filter_maven_output(self, output: str, log_debug: bool = True) -> list[str]:
        """Filter Maven output to extract [INFO] lines."""
        lines = []
        for line in output.splitlines():
            line = line.strip()
            if log_debug and line.startswith(("[DEBUG]", "[WARNING]", "[ERROR]")):
                _log.debug(line)
            if not line.startswith("[INFO]"):
                continue
            # Skip download/progress messages
            if (
                "Downloading from" in line
                or "Downloaded from" in line
                or "Progress" in line
            ):
                continue
            lines.append(line)
        return lines

    def _parse_maven_coordinate(
        self, content: str, context, require_scope: bool = False
    ) -> Dependency | None:
        """Parse Maven output coordinate string into Dependency object."""
        # Strip module information added by Java 9+
        if " -- module " in content:
            content = content.split(" -- module ")[0].strip()

        try:
            coord = Coordinate.parse(content)

            # For dependency:list output, we need to validate the scope
            if require_scope and (
                not coord.scope
                or coord.scope
                not in (
                    "compile",
                    "runtime",
                    "provided",
                    "test",
                    "system",
                    "import",
                )
            ):
                return None

            return context.create_dependency(coord)
        except ValueError:
            return None

    def download(self, artifact: Artifact) -> Path | None:
        _log.info(f"Downloading artifact: {artifact}")
        assert artifact.context.repo_cache
        assert artifact.groupId
        assert artifact.artifactId
        assert artifact.version
        assert artifact.packaging
        args = [
            f"-Dmaven.repo.local={artifact.context.repo_cache}",
            f"-DgroupId={artifact.groupId}",
            f"-DartifactId={artifact.artifactId}",
            f"-Dversion={artifact.version}",
            f"-Dpackaging={artifact.packaging}",
        ]
        if artifact.classifier:
            args.append(f"-Dclassifier={artifact.classifier}")
        if artifact.context.remote_repos:
            remote_repos = ",".join(
                f"{name}::::{url}"
                for name, url in artifact.context.remote_repos.items()
            )
            args.append(f"-DremoteRepositories={remote_repos}")

        self._mvn("dependency:get", *args)

        # The file should now exist in the local repo cache.
        assert artifact.cached_path and artifact.cached_path.exists()
        return artifact.cached_path

    def resolve(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[list[Dependency], list[Dependency]]:
        """
        Get all dependencies for the given input dependencies.

        Args:
            dependencies: List of input dependencies to resolve
            transitive: Whether to include transitive dependencies
            optional_depth: Maximum depth at which to include optional dependencies.
                NOTE: MvnResolver does not support custom optional_depth - Maven always
                excludes optional transitive dependencies (equivalent to optional_depth=0).

        Returns:
            Tuple of (resolved_inputs, resolved_transitive) where:
            - resolved_inputs: Input deps with MANAGED versions resolved
            - resolved_transitive: Transitive dependencies (excludes the inputs themselves)
        """
        if optional_depth > 0:
            _log.warning(
                f"MvnResolver does not support optional_depth={optional_depth}. "
                "Maven always excludes optional transitive dependencies. "
                "Use PythonResolver (--resolver=python) for custom optional_depth."
            )

        if not dependencies:
            raise ValueError("At least one dependency is required")

        if not transitive:
            # Use get_dependency_tree and extract only direct children (depth 1)
            root = self.get_dependency_tree(dependencies)
            dep_nodes = []

            # Extract direct children of the root's children (which are the inputs)
            for component_node in root.children:
                dep_nodes.extend(component_node.children)

            # Convert DependencyNodes back to Dependency objects
            resolved_transitive = [node.dep for node in dep_nodes]

            # Build resolved components - for non-transitive, inputs are just themselves
            # (MANAGED versions would have been resolved during tree building)
            resolved_inputs = [node.dep for node in root.children]

            return resolved_inputs, resolved_transitive

        # For transitive=True, use dependency:list

        # Get context and repo cache from first dependency
        context = dependencies[0].context
        assert context.repo_cache

        boms = _compute_boms(dependencies)

        # Log what we're resolving
        _log.info(f"Resolving dependencies for {len(dependencies)} dependency(ies)")
        for dep in dependencies:
            _log.debug(
                f"  Dependency: {dep.groupId}:{dep.artifactId}:{dep.artifact.component.version}"
            )

        # Create temporary POM
        temp_pom = self._create_temp_pom(dependencies, boms)

        output = self._mvn(
            "dependency:list",
            "-f",
            str(temp_pom),
            f"-Dmaven.repo.local={context.repo_cache}",
            "-Dscope=runtime",
        )

        # Parse Maven's dependency:list output format:
        # Java 8:  [INFO]    groupId:artifactId:packaging:version:scope
        # Java 9+: [INFO]    groupId:artifactId:packaging:version:scope -- module module.name
        all_deps = []

        info_lines = self._filter_maven_output(output)

        for line in info_lines:
            # Remove [INFO] prefix and whitespace
            content = line[6:].strip()

            # Skip non-dependency lines
            if ":" not in content:
                continue

            # Parse G:A:P[:C]:V:S format using Coordinate
            parsed_dep = self._parse_maven_coordinate(
                content, context, require_scope=True
            )
            if not parsed_dep:
                # Not a valid coordinate format
                continue

            # Create dependency object from coordinate
            all_deps.append(parsed_dep)

        # Build resolved component dependencies
        resolved_inputs, artifact_keys = _resolve_component_inputs(
            dependencies, all_deps
        )

        # Filter out components from transitive deps list
        resolved_transitive = [
            dep for dep in all_deps if dep.artifact.key not in artifact_keys
        ]

        # Filter to runtime scopes only (compensate for Maven's -Dscope quirk)
        resolved_transitive = self._filter_dep_scopes(resolved_transitive, "runtime")

        return resolved_inputs, resolved_transitive

    def get_dependency_list(
        self,
        dependencies: list[Dependency],
        transitive: bool = True,
        optional_depth: int = 0,
    ) -> tuple[DependencyNode, list[DependencyNode]]:
        """
        Get the flat list of resolved dependencies as data structures.

        Args:
            dependencies: List of input dependencies
            transitive: If False, return only direct dependencies
            optional_depth: Maximum depth at which to include optional dependencies
                NOTE: Not supported by MvnResolver - use PythonResolver instead

        Returns:
            Tuple of (root_node, flat_list_of_dependencies)
        """
        _resolved_inputs, resolved_transitive = self.resolve(
            dependencies,
            transitive=transitive,
            optional_depth=optional_depth,
        )
        return _build_dependency_list(dependencies, resolved_transitive)

    def get_dependency_tree(
        self,
        dependencies: list[Dependency],
        optional_depth: int = 0,
    ) -> DependencyNode:
        """
        Get the full dependency tree as a data structure.

        Args:
            dependencies: List of input dependencies
            optional_depth: Maximum depth at which to include optional dependencies
                NOTE: Not supported by MvnResolver - use PythonResolver instead

        Returns:
            Root DependencyNode with full tree structure
        """
        if optional_depth > 0:
            _log.warning(
                f"MvnResolver does not support optional_depth={optional_depth}. "
                "Maven always excludes optional transitive dependencies. "
                "Use PythonResolver (--resolver=python) for custom optional_depth."
            )

        if not dependencies:
            raise ValueError("At least one dependency is required")

        context = dependencies[0].context
        assert context.repo_cache

        boms = _compute_boms(dependencies)

        # Create temporary POM
        temp_pom = self._create_temp_pom(dependencies, boms)

        output = self._mvn(
            "dependency:tree",
            "-f",
            str(temp_pom),
            f"-Dmaven.repo.local={context.repo_cache}",
            "-Dscope=runtime",
        )

        # Parse the tree output
        # Format: [INFO] org.apposed.jgo:INTERNAL-WRAPPER:jar:0-SNAPSHOT
        #         [INFO] \- org.example:my-component:pom:1.2.3:compile
        #         [INFO]    +- dep1:jar:1.0:scope
        #         [INFO]    |  \- dep2:jar:2.0:scope
        #         [INFO]    \- dep3:jar:3.0:scope

        info_lines = self._filter_maven_output(output, log_debug=False)
        root = None
        stack = []  # Stack of (indent_level, node)

        for line in info_lines:
            # Remove [INFO] prefix
            content = line[6:]  # Skip "[INFO] "

            # Skip lines that don't look like dependencies
            # (e.g., "Building ...", "Finished at:", etc.)
            if ":" not in content:
                continue

            # Skip lines that contain common Maven status messages
            skip_patterns = [
                "Finished at:",
                "Total time:",
                "Building ",
                "from ",
                "---",
                "Scanning",
            ]
            if any(pattern in content for pattern in skip_patterns):
                continue

            # Determine indentation level by counting tree characters
            indent = 0
            for char in content:
                if char in " |+\\-":
                    indent += 1
                else:
                    break

            # Clean up tree characters to get just the coordinate
            clean_content = content.lstrip(" |+\\-")

            if not clean_content or ":" not in clean_content:
                continue

            # Parse G:A:P[:C]:V[:S] format using Coordinate
            dep = self._parse_maven_coordinate(clean_content, context)
            if not dep:
                continue

            # Filter out test-scoped dependencies to match PythonResolver behavior
            # (compensates for Maven's -Dscope quirk)
            if dep.scope == "test":
                continue

            node = DependencyNode(dep)

            # Handle root node (no indent)
            if indent == 0 or root is None:
                root = node
                stack = [(0, root)]
            else:
                # Find parent by popping stack until we find correct indent level
                while stack and stack[-1][0] >= indent:
                    stack.pop()

                if stack:
                    _parent_indent, parent_node = stack[-1]
                    parent_node.children.append(node)

                stack.append((indent, node))

        return root if root else DependencyNode(dependencies[0])

    def _mvn(self, *args) -> str:
        return MvnResolver._run(self.mvn_command, *self.mvn_flags, *args)

    @staticmethod
    def _run(command, *args) -> str:
        command_and_args = (command,) + args
        _log.debug(f"Executing: {command_and_args}")
        result = run(command_and_args, capture_output=True, check=False)
        if result.returncode == 0:
            return result.stdout.decode()

        error_message = (
            f"Command failed with exit code {result.returncode}:\n{command_and_args}"
        )
        if result.stdout:
            error_message += f"\n\n[stdout]\n{result.stdout.decode()}"
        if result.stderr:
            error_message += f"\n\n[stderr]\n{result.stderr.decode()}"
        raise RuntimeError(error_message)
