"""
Maven dependency model and resolution.
"""

from __future__ import annotations

import logging
from pathlib import Path
from re import findall
from typing import TYPE_CHECKING

from ..util.http import RepositoryAccessDenied
from ..util.java import (
    parse_java_version,
    parse_jdk_activation_range,
    version_matches_jdk_range,
)
from ._core import Dependency, DependencyNode, MavenContext, Project

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ._pom import POM
    from ._profile import ProfileConstraints

_log = logging.getLogger(__name__)

# (groupId, artifactId, classifier, type)
GACT = tuple[str, str, str, str]


class Model:
    """
    A minimal Maven metadata model, tracking only dependencies and properties.
    """

    def __init__(
        self,
        pom: POM,
        context: MavenContext,
        root_dep_mgmt: dict[GACT, Dependency] | None = None,
        profile_constraints: ProfileConstraints | None = None,
        lenient: bool = False,
    ):
        """
        Build a Maven metadata model from the given POM.

        Args:
            pom: A source POM from which to extract metadata (e.g. dependencies).
            context: Maven context for dependency resolution.
            root_dep_mgmt: Optional dependency management from the root project.
                This takes precedence over the local dependency management and is used
                to ensure consistent versions across all transitive dependencies.
            profile_constraints: Optional constraints for profile activation. When
                omitted, the context resolver's own constraints are used (the default
                PythonResolver auto-detects host OS properties).
            lenient: If True, warn instead of failing on unresolvable dependencies.
        """

        self.pom = pom
        self.context = context
        self.root_dep_mgmt = root_dep_mgmt
        # When no constraints are passed explicitly, fall back to those carried by
        # the context's resolver. The default PythonResolver auto-detects the host's
        # OS properties (os.name/os.family/os.arch), so a Model built directly against
        # a context — rather than via the resolver — still activates platform-specific
        # profiles instead of silently leaving their properties uninterpolated.
        if profile_constraints is None:
            profile_constraints = getattr(context.resolver, "profile_constraints", None)
        self.profile_constraints = profile_constraints
        self.lenient = lenient
        self.gav = f"{pom.groupId}:{pom.artifactId}:{pom.version}"
        _log.debug(f"{self.gav}: begin model initialization")

        # Transfer raw metadata from POM source to target model.
        # For now, we handle only dependencies, dependencyManagement, and properties.
        self.deps: dict[GACT, Dependency] = {}
        self.dep_mgmt: dict[GACT, Dependency] = {}
        self.props: dict[str, str] = {}

        # The following steps are adapted from the maven-model-builder:
        # https://maven.apache.org/ref/3.3.9/maven-model-builder/

        # -- PROFILE ACTIVATION AND INJECTION --

        _log.debug(f"{self.gav}: profile activation and injection")

        self._inject_profiles(pom)
        self._merge(pom)

        # -- PARENT RESOLUTION AND INHERITANCE ASSEMBLY --

        _log.debug(f"{self.gav}: parent resolution and inheritance assembly")

        # Merge values up the parent chain into the current model.
        parent = self.context.pom_parent(pom)
        while parent:
            self._inject_profiles(parent)
            self._merge(parent)
            parent = self.context.pom_parent(parent)

        # Fall back to the super POM's build layout for anything left unset.
        # https://maven.apache.org/ref/3.9.9/maven-model-builder/super-pom.html
        if isinstance(pom.source, Path):
            self._merge_props({"project.basedir": str(pom.source.parent)})
        self._merge_props(
            {
                "project.build.directory": "${project.basedir}/target",
                "project.build.outputDirectory": "${project.build.directory}/classes",
                "project.build.finalName": "${project.artifactId}-${project.version}",
            }
        )

        # -- MODEL INTERPOLATION --

        _log.debug(f"{self.gav}: model interpolation")

        # Inject OS-related properties from profile constraints.
        # These are needed for interpolating classifiers like:
        # natives-${scijava.platform.family.longest}-${os.arch}
        if self.profile_constraints:
            os_props = {}
            if self.profile_constraints.os_name:
                os_props["os.name"] = self.profile_constraints.os_name
            if self.profile_constraints.os_arch:
                os_props["os.arch"] = self.profile_constraints.os_arch
            if self.profile_constraints.os_family:
                os_props["os.family"] = self.profile_constraints.os_family
            if self.profile_constraints.os_version:
                os_props["os.version"] = self.profile_constraints.os_version
            if self.profile_constraints.basedir:
                os_props["basedir"] = self.profile_constraints.basedir
            # Merge with lowest priority (don't override existing props)
            self._merge_props(os_props)
            # Note: As in Maven, user properties (-D) take precedence over model
            # properties, so a POM cannot shadow a value the user set explicitly.
            self.props.update(self.profile_constraints.properties)

        # Replace ${...} expressions in property values.
        for k in list(self.props):
            Model._propvalue(k, self.props)

        # Replace ${...} expressions in dependency coordinate values.
        # We must rebuild the dicts because interpolation can change GACT keys.
        self.deps = self._interpolate_deps(self.deps)
        self.dep_mgmt = self._interpolate_deps(self.dep_mgmt)

        # -- DEPENDENCY MANAGEMENT IMPORT --

        _log.debug(f"{self.gav}: dependency management import")

        # NB: BOM-type dependencies imported in the <dependencyManagement> section are
        # fully interpolated before merging their dependencyManagement into this model,
        # without any consideration for differing property values set in this POM's
        # inheritance chain. Therefore, unlike with parent POMs, dependency versions
        # defined indirectly via version properties cannot be overridden by setting
        # those version properties in the consuming POM!
        # NB: We need to copy the dep_mgmt dict to avoid mutating while iterating it.
        self._import_boms(self.dep_mgmt.copy())

        # -- DEPENDENCY MANAGEMENT INJECTION --

        _log.debug(f"{self.gav}: dependency management injection")

        # Log how many managed dependencies we have (including from BOMs)
        if self.root_dep_mgmt:
            _log.debug(
                f"{self.gav}: root_dep_mgmt has {len(self.root_dep_mgmt)} entries"
            )

        _log.debug(f"{self.gav}: local dep_mgmt has {len(self.dep_mgmt)} entries")

        # Handles injection of dependency management into the model.
        # According to Maven semantics, dependency management provides default values for:
        # version, scope, type, classifier, exclusions, and optional flag.
        #
        # IMPORTANT: Root dependency management (from the wrapper/entry point) takes
        # precedence over local dependency management. This ensures that the root project's
        # version constraints are applied consistently across all transitive dependencies.
        deps_to_remove = []
        for gact, dep in self.deps.items():
            # First check root_dep_mgmt (highest priority), then local dep_mgmt
            root_managed = self.root_dep_mgmt.get(gact) if self.root_dep_mgmt else None
            local_managed = self.dep_mgmt.get(gact, None)
            managed = root_managed or local_managed

            if managed is None:
                # No managed version available
                if not dep.version or dep.version == "MANAGED":
                    if self.lenient:
                        _log.warning(f"No version available for dependency {dep}")
                        deps_to_remove.append(gact)
                        continue
                    raise ValueError(f"No version available for dependency {dep}")
                continue

            dep_ga = f"{dep.groupId}:{dep.artifactId}"
            source = (
                "root dependencyManagement" if root_managed else "dependencyManagement"
            )

            # Inject version if not set, or if root_dep_mgmt overrides it
            if not dep.version or dep.version == "MANAGED":
                _log.debug(
                    f"{self.gav}: {dep_ga}: version set to {managed.version} (from {source})"
                )
                dep.set_version(managed.version)
            elif root_managed and dep.version != root_managed.version:
                # Root dep management overrides the version even if already set
                _log.debug(
                    f"{self.gav}: {dep_ga}: version overridden {dep.version} -> {root_managed.version} (from {source})"
                )
                dep.set_version(root_managed.version)

            # Inject scope if not explicitly set
            if dep.scope is None and managed.scope is not None:
                _log.debug(
                    f"{self.gav}: {dep_ga}: scope set to {managed.scope} (from {source})"
                )
                dep.scope = managed.scope

            # Inject exclusions if managed dependency has them and current doesn't
            if managed.exclusions and not dep.exclusions:
                _log.debug(
                    f"{self.gav}: {dep_ga}: exclusions inherited from {source}: {managed.exclusions}"
                )
                dep.exclusions = managed.exclusions
            elif managed.exclusions:
                _log.debug(
                    f"{self.gav}: {dep_ga}: NOT inheriting exclusions (dep already has exclusions: {dep.exclusions})"
                )

        # Remove bad dependencies that couldn't be resolved (only in lenient mode)
        for gact in deps_to_remove:
            del self.deps[gact]

        # Any dependencies that still don't have a scope get the default
        for dep in self.deps.values():
            if dep.scope is None:
                dep.scope = "test" if dep.classifier == "tests" else "compile"

        _log.debug(f"{self.gav}: model construction complete")

    def build_outputs(self) -> tuple[Path, Path]:
        """
        Locate where a local build of this project puts its compiled output.

        Paths come from the interpolated ``<build>`` settings, inherited from parent
        POMs and defaulting to the super POM's layout. Relative paths are resolved
        against the project's base directory. Nothing is checked for existence.

        Returns:
            Tuple of (output_directory, main_jar), typically
            ``target/classes`` and ``target/<artifactId>-<version>.jar``.
        """
        basedir = Path(self.props.get("project.basedir", "."))

        def build_path(prop: str) -> Path:
            path = Path(Model._propvalue(prop, self.props) or "")
            return path if path.is_absolute() else basedir / path

        build_dir = build_path("project.build.directory")
        final_name = Model._propvalue("project.build.finalName", self.props)
        return build_path(
            "project.build.outputDirectory"
        ), build_dir / f"{final_name}.jar"

    def dependencies(
        self,
        resolved: dict[GACT, Dependency] | None = None,
        root_dep_mgmt: dict[GACT, Dependency] | None = None,
        max_depth: int | None = None,
        optional_depth: int = 0,
    ) -> tuple[list[Dependency], DependencyNode]:
        """
        Compute the component's list of dependencies, including transitive dependencies.

        Uses breadth-first traversal (nearest-wins algorithm) to match Maven's behavior.
        Dependencies at depth N are all processed before moving to depth N+1.

        The dependency tree is built during traversal, capturing the exact parent-child
        relationships as they are discovered by the resolution algorithm.

        Args:
            resolved:
                Optional dictionary of already-resolved dependency coordinates.
                Items present in this structure will be pruned from the
                returned dependency list rather than recursively explored.
            root_dep_mgmt:
                Optional dependency management from the root project.
                This will be used to override versions of transitive dependencies.
            max_depth:
                Maximum depth to recurse when resolving dependencies. None means unlimited
                (fully transitive). 1 means direct dependencies only (when called on a
                synthetic wrapper POM, this gives the direct dependencies of the wrapped
                components). 0 would mean no dependencies at all.
            optional_depth:
                Maximum depth at which to include optional dependencies.
                0 means exclude all optional transitive dependencies, matching Maven's behavior.
                1 means include optional dependencies at depth 1.

        Returns:
            A tuple of (dependency_list, dependency_tree) where:
            - dependency_list: The flat list of resolved Dependency objects
            - dependency_tree: DependencyNode representing the root with children populated
        """
        all_deps: dict[GACT, Dependency] = {}

        # Build dependency tree during traversal
        # Create root node from this model's POM
        assert (
            self.pom.groupId is not None
            and self.pom.artifactId is not None
            and self.pom.version is not None
        )
        root_artifact = (
            self.context.project(self.pom.groupId, self.pom.artifactId)
            .at_version(self.pom.version)
            .artifact(type="pom")
        )
        root_dep = Dependency(root_artifact)
        tree_root = DependencyNode(root_dep)

        # Map from GACT to DependencyNode for building parent-child relationships
        nodes: dict[GACT, DependencyNode] = {}

        # Determine whether we are currently diving into transitive dependencies.
        recursing: bool = resolved is not None
        if resolved is None:
            resolved = {}
            # At the root level, use our own dependency management for transitive deps
            root_dep_mgmt = self.dep_mgmt

        # Queue for breadth-first traversal: (model, parent_dep, parent_scope, accumulated_exclusions)
        # parent_dep is None for root level
        # parent_scope is used for scope transformation
        # accumulated_exclusions tracks all exclusions from ancestors
        queue: list[tuple[Model, Dependency | None, str | None, tuple]] = [
            (self, None, None, ())
        ]
        current_depth = 0

        while queue and (max_depth is None or current_depth <= max_depth):
            # Process all items at current depth
            next_queue: list[tuple[Model, Dependency | None, str | None, tuple]] = []

            for model, parent_dep, parent_scope, accumulated_exclusions in queue:
                for gact, dep in model.deps.items():
                    dep_ga = f"{dep.groupId}:{dep.artifactId}"

                    # Skip if already resolved (nearest-wins)
                    if gact in resolved:
                        _log.debug(f"{model.gav}: {dep_ga}: skipped (already resolved)")
                        continue

                    # Skip non-transitive scopes when recursing
                    if recursing and dep.scope not in ("compile", "runtime"):
                        _log.debug(
                            f"{model.gav}: {dep_ga}: skipped (non-transitive scope: {dep.scope})"
                        )
                        continue

                    # Skip optional dependencies based on optional_depth
                    if dep.optional and current_depth > optional_depth:
                        _log.debug(
                            f"{model.gav}: {dep_ga}: skipped (optional at depth {current_depth}, "
                            f"optional_depth={optional_depth})"
                        )
                        continue

                    # Check exclusions from all ancestors (not just immediate parent)
                    if accumulated_exclusions and Model._is_excluded(
                        dep, accumulated_exclusions
                    ):
                        ancestor_info = (
                            "ancestor"
                            if not parent_dep
                            else f"{parent_dep.groupId}:{parent_dep.artifactId} or ancestor"
                        )
                        _log.debug(
                            f"{model.gav}: {dep_ga}: excluded by {ancestor_info}"
                        )
                        continue

                    # Skip dependencies with uninterpolated properties in lenient mode
                    if model.lenient and Model._has_uninterpolated_properties(dep):
                        _log.warning(
                            f"{model.gav}: {dep_ga}: skipped (uninterpolated properties in {dep})"
                        )
                        continue

                    # Record this dependency
                    resolved[gact] = dep
                    all_deps[gact] = dep

                    # Build tree node and establish parent-child relationship
                    node = DependencyNode(dep)
                    nodes[gact] = node

                    if parent_dep is None:
                        # Root level dependency - add as child of tree root
                        tree_root.children.append(node)
                    else:
                        # Child of parent_dep - add to parent's children
                        parent_gact = (
                            parent_dep.groupId,
                            parent_dep.artifactId,
                            parent_dep.classifier,
                            parent_dep.type,
                        )
                        if parent_gact in nodes:
                            nodes[parent_gact].children.append(node)

                    # Apply scope transformation based on parent scope
                    original_scope = dep.scope
                    if parent_scope == "runtime":
                        dep.scope = "runtime"
                    elif parent_scope == "test":
                        dep.scope = "test"

                    if dep.scope != original_scope:
                        _log.debug(
                            f"{model.gav}: {dep_ga}: scope transformed {original_scope} -> {dep.scope}"
                        )

                    # Log the dependency
                    if parent_dep:
                        _log.debug(f"{model.gav}: {parent_dep} -> {dep}")
                    else:
                        _log.debug(f"{model.gav}: {dep}")

                    # Queue this dependency's model for next depth level
                    if max_depth is None or current_depth < max_depth:
                        try:
                            dep_model = Model(
                                dep.artifact.component.pom(),
                                model.context,
                                root_dep_mgmt,
                                model.profile_constraints,
                                model.lenient,
                            )
                            # Accumulate exclusions: combine ancestor exclusions with this dep's exclusions
                            new_exclusions = accumulated_exclusions + dep.exclusions
                            next_queue.append(
                                (dep_model, dep, dep.scope, new_exclusions)
                            )
                        except RepositoryAccessDenied:
                            raise
                        except (OSError, ValueError, RuntimeError, KeyError) as e:
                            _log.debug(f"Could not build model for {dep}: {e}")

            # Move to next depth level
            queue = next_queue
            current_depth += 1
            recursing = True  # After first level, we're always recursing

        return list(all_deps.values()), tree_root

    def _import_boms(self, candidates: dict[GACT, Dependency]) -> None:
        """
        Scan the candidates for dependencies of type pom with scope import.

        For each such dependency found, import its dependencyManagement section
        into ours, scanning it recursively for more BOMs to import.

        Args:
            candidates: The candidate dependencies, which might be BOMs.
        """
        for dep in candidates.values():
            if not (dep.scope == "import" and dep.type == "pom"):
                continue

            # Fail fast if BOM has MANAGED version - this indicates a bug.
            # MANAGED versions should be resolved before Model construction.
            if dep.version == "MANAGED":
                raise ValueError(
                    f"{self.gav}: BOM {dep.groupId}:{dep.artifactId} has unresolved "
                    "MANAGED version. MANAGED versions must be resolved before "
                    "creating the wrapper POM."
                )

            bom_gav = f"{dep.groupId}:{dep.artifactId}:{dep.version}"
            _log.debug(f"{self.gav}: importing BOM {bom_gav}")

            # Load the POM to import.
            bom_project = self.context.project(dep.groupId, dep.artifactId)
            bom_pom = bom_project.at_version(dep.version).pom()

            # Fully build the BOM's model, agnostic of this one.
            bom_model = Model(
                bom_pom,
                self.context,
                profile_constraints=self.profile_constraints,
                lenient=self.lenient,
            )

            # Count how many managed deps we're importing
            before_count = len(self.dep_mgmt)

            # Merge the BOM model's <dependencyManagement> into this model.
            self._merge_deps(bom_model.dep_mgmt.values(), managed=True)

            after_count = len(self.dep_mgmt)
            new_count = after_count - before_count
            _log.debug(
                f"{self.gav}: imported {new_count} managed deps from BOM {bom_gav} "
                f"(total: {after_count})"
            )

            # Scan BOM <dependencyManagement> for additional potential BOMs.
            self._import_boms(bom_model.dep_mgmt)

    def _merge_deps(self, source: Iterable[Dependency], managed: bool = False) -> None:
        target = self.dep_mgmt if managed else self.deps
        for dep in source:
            # Interpolate coordinates early using available properties
            g = Model._evaluate(dep.groupId, self.props) if dep.groupId else dep.groupId
            a = (
                Model._evaluate(dep.artifactId, self.props)
                if dep.artifactId
                else dep.artifactId
            )
            c = (
                Model._evaluate(dep.classifier, self.props)
                if dep.classifier
                else dep.classifier
            )
            t = Model._evaluate(dep.type, self.props) if dep.type else dep.type

            # Update dep coordinates if interpolation changed them
            if g != dep.groupId:
                dep.artifact.component.project.groupId = g
            if a != dep.artifactId:
                dep.artifact.component.project.artifactId = a
            if c != dep.classifier:
                dep.artifact.classifier = c
            if t != dep.type:
                dep.artifact.type = t

            k = (g, a, c, t)
            if k not in target:
                target[k] = dep

    def _merge_props(self, source: dict[str, str]) -> None:
        for k, v in source.items():
            if v is not None and k not in self.props:
                self.props[k] = v

    def _merge(self, pom: POM) -> None:
        """
        Merge metadata from the given POM source into this model.
        For now, we handle only dependencies, dependencyManagement, and properties.
        """
        # Merge special properties first, before dependencies, so that _merge_deps
        # can interpolate dependency coordinates using properties like ${project.groupId}
        self._merge_props(
            {
                k: v
                for k, v in {
                    "project.groupId": pom.groupId,
                    "project.artifactId": pom.artifactId,
                    "project.version": pom.version,
                    "project.name": pom.name,
                    "project.description": pom.description,
                    "project.parent.groupId": pom.value("parent/groupId"),
                    "project.parent.artifactId": pom.value("parent/artifactId"),
                    "project.parent.version": pom.value("parent/version"),
                    "project.build.directory": pom.value("build/directory"),
                    "project.build.outputDirectory": pom.value("build/outputDirectory"),
                    "project.build.finalName": pom.value("build/finalName"),
                }.items()
                if v is not None
            }
        )
        self._merge_props(pom.properties)

        self._merge_deps(self.context.pom_dependencies(pom))
        self._merge_deps(self.context.pom_dependencies(pom, managed=True), managed=True)

    def _inject_profiles(self, pom: POM) -> None:
        """
        Activate and inject profiles from the given POM.
        """
        # Compute active profiles. As in Maven, activeByDefault profiles apply
        # only when no other profile of the same POM is activated.
        profiles = pom.elements("profiles/profile")
        active_profiles = [p for p in profiles if self._is_active_profile(p)]
        if not active_profiles:
            active_profiles = [p for p in profiles if self._is_active_by_default(p)]

        # Merge values from the active profiles into the model.
        for profile in active_profiles:
            profile_dep_els = profile.findall("dependencies/dependency")
            profile_deps = [
                self.context.parse_dependency_element(el) for el in profile_dep_els
            ]
            self._merge_deps(profile_deps)

            profile_dep_mgmt_els = profile.findall(
                "dependencyManagement/dependencies/dependency"
            )
            profile_dep_mgmt = [
                self.context.parse_dependency_element(el) for el in profile_dep_mgmt_els
            ]
            self._merge_deps(profile_dep_mgmt, managed=True)

            profile_props_els = profile.findall("properties/*")
            profile_props = {
                el.tag: el.text for el in profile_props_els if el.text is not None
            }
            self._merge_props(profile_props)

    def _interpolate_deps(self, deps: dict[GACT, Dependency]) -> dict[GACT, Dependency]:
        """
        Interpolate ${...} expressions in dependency coordinates.

        This rebuilds the deps dict because interpolation can change GACT keys.
        For example, if a dependency has groupId="${project.groupId}", after
        interpolation the GACT key will be different.
        """
        new_deps = {}
        for old_gact, dep in deps.items():
            # Interpolate each coordinate field
            g = Model._evaluate(dep.groupId, self.props) if dep.groupId else dep.groupId
            a = (
                Model._evaluate(dep.artifactId, self.props)
                if dep.artifactId
                else dep.artifactId
            )
            c = (
                Model._evaluate(dep.classifier, self.props)
                if dep.classifier
                else dep.classifier
            )
            t = Model._evaluate(dep.type, self.props) if dep.type else dep.type
            v = Model._evaluate(dep.version, self.props) if dep.version else dep.version

            # Mutate the underlying artifact/component to match interpolated values
            # (This is what set_version() does for the version field)
            if g != dep.groupId:
                dep.artifact.component.project.groupId = g
            if a != dep.artifactId:
                dep.artifact.component.project.artifactId = a
            if c != dep.classifier:
                dep.artifact.classifier = c
            if t != dep.type:
                dep.artifact.type = t
            if v != dep.version:
                dep.set_version(v)

            # Build new GACT key with interpolated values
            new_gact = (g, a, c, t)

            # Check for collisions (rare, but possible)
            if new_gact in new_deps and new_gact != old_gact:
                _log.warning(
                    "Interpolation caused GACT key collision: "
                    f"{old_gact} -> {new_gact}. "
                    "Keeping first occurrence (nearest wins)."
                )
                continue

            new_deps[new_gact] = dep

        return new_deps

    @staticmethod
    def _has_uninterpolated_properties(dep: Dependency) -> bool:
        """Check if dependency has uninterpolated ${...} expressions in coordinates."""
        coords = [
            dep.groupId,
            dep.artifactId,
            dep.version,
            dep.classifier,
            dep.type,
        ]
        return any("${" in str(c) for c in coords if c)

    @staticmethod
    def _is_excluded(dep: Dependency, exclusions: Iterable[Project]):
        return any(
            (
                exclusion.groupId in ["*", dep.groupId]
                and exclusion.artifactId in ["*", dep.artifactId]
            )
            for exclusion in exclusions
        )

    def _is_active_profile(self, el) -> bool:
        """
        Check whether a profile's activation conditions are satisfied.

        Mirrors Maven's DefaultProfileSelector: every activator present in the
        <activation> block (jdk, os, property, file) must match, and at least one
        must be present. The activeByDefault flag is not considered here; see
        _is_active_by_default and _inject_profiles.
        """
        activation = el.find("activation")
        if activation is None:
            return False

        profile_id_el = el.find("id")
        profile_id = profile_id_el.text if profile_id_el is not None else "<unknown>"

        checks = {
            "jdk": self._jdk_matches,
            "os": self._os_matches,
            "property": self._property_matches,
            "file": self._file_matches,
        }
        present = False
        for condition in activation:
            check = checks.get(condition.tag)
            if check is None:
                continue  # activeByDefault, or an unknown activator
            present = True
            if not check(condition):
                return False

        if present:
            _log.debug(f"Profile '{profile_id}' activated")
        return present

    @staticmethod
    def _is_active_by_default(el) -> bool:
        flag = el.find("activation/activeByDefault")
        return flag is not None and (flag.text or "").strip() == "true"

    def _jdk_matches(self, condition) -> bool:
        if not self.profile_constraints or not self.profile_constraints.jdk:
            return False

        jdk_spec = (condition.text or "").strip()
        if not jdk_spec:
            return False

        negated = jdk_spec.startswith("!")
        if negated:
            jdk_spec = jdk_spec[1:]

        try:
            current_version = parse_java_version(self.profile_constraints.jdk)
            lower, upper, lower_inc, upper_inc = parse_jdk_activation_range(jdk_spec)
            matches = version_matches_jdk_range(
                current_version, lower, upper, lower_inc, upper_inc
            )
        except ValueError as e:
            _log.warning(
                f"Invalid JDK version specification '{condition.text}'"
                f" in {self.gav}: {e}"
            )
            _log.debug(f"POM source: {getattr(self.pom, 'source', '<unknown>')}")
            return False

        return not matches if negated else matches

    def _os_matches(self, condition) -> bool:
        # <name>Windows XP</name>
        # <family>Windows</family>
        # <arch>x86</arch>
        # <version>5.1.2600</version>
        constraints = self.profile_constraints
        if not constraints:
            return False

        for os_condition in condition:
            text = (os_condition.text or "").strip()
            negated = text.startswith("!")
            if negated:
                text = text[1:]
            # Note: Maven compares all OS values case-insensitively.
            text = text.lower()

            if os_condition.tag == "family":
                matches = _os_is_family(
                    text, constraints.os_name, constraints.os_family
                )
            elif os_condition.tag in ("name", "arch", "version"):
                actual = getattr(constraints, f"os_{os_condition.tag}")
                matches = actual is not None and actual.lower() == text
            else:
                continue

            if matches == negated:
                return False
        return True

    def _property_matches(self, condition) -> bool:
        # <name>sparrow-type</name>
        # <value>African</value>
        if not self.profile_constraints:
            return False

        name_el = condition.find("name")
        name = (name_el.text or "").strip() if name_el is not None else ""
        if not name:
            return False
        reverse_name = name.startswith("!")
        if reverse_name:
            name = name[1:]

        actual = self.profile_constraints.properties.get(name)

        value_el = condition.find("value")
        value = (value_el.text or "").strip() if value_el is not None else ""
        if value:
            # Note: As in Maven, a leading ! on the value means "not equal to",
            # which an absent property also satisfies.
            reverse_value = value.startswith("!")
            if reverse_value:
                value = value[1:]
            return (value == actual) != reverse_value

        exists = bool(actual)
        return exists != reverse_name

    def _file_matches(self, condition) -> bool:
        # <file>
        # <exists>${basedir}/file2.properties</exists>
        # <missing>${basedir}/file1.properties</missing>
        if not self.profile_constraints:
            return False

        # Note: As in Maven, <missing> takes precedence over <exists>.
        missing_el = condition.find("missing")
        if missing_el is not None and missing_el.text:
            file_path = Model._evaluate(missing_el.text, self.props)
            return not self.profile_constraints.file_exists(file_path)

        exists_el = condition.find("exists")
        if exists_el is not None and exists_el.text:
            file_path = Model._evaluate(exists_el.text, self.props)
            return self.profile_constraints.file_exists(file_path)

        return False

    @staticmethod
    def _evaluate(
        expression: str, props: dict[str, str], visited: set[str] | None = None
    ) -> str:
        props_referenced = set(findall(r"\${([^}]*)}", expression))
        if not props_referenced:
            return expression

        value = expression
        for prop_reference in props_referenced:
            replacement = Model._propvalue(prop_reference, props, visited)
            if replacement is None:
                # NB: Leave "${...}" expressions alone when property is absent.
                # This matches Maven behavior, but it still makes me nervous.
                if prop_reference.startswith("project.groupId"):
                    raise ValueError(f"No replacement for {prop_reference}")
                continue
            value = value.replace("${" + prop_reference + "}", replacement)
        return value

    @staticmethod
    def _propvalue(
        propname: str, props: dict[str, str], visited: set[str] | None = None
    ) -> str | None:
        if visited is None:
            visited = set()
        if propname in visited:
            raise ValueError(f"Infinite reference loop for property '{propname}'")
        visited.add(propname)

        expression = props.get(propname, None)
        if expression is None:
            # Resolve (and cache) a legacy alias under its project.* name, never
            # adding a key: callers may be iterating over props.
            alias = _legacy_project_alias(propname)
            if alias is None or alias not in props:
                return None
            return Model._propvalue(alias, props, visited)
        evaluated = Model._evaluate(expression, props, visited)
        props[propname] = evaluated
        return evaluated


# Model fields that Maven 2-era POMs reference without the "project." prefix,
# e.g. ${version} or ${parent.version}.
_UNPREFIXED_PROJECT_FIELDS = (
    "groupId",
    "artifactId",
    "version",
    "name",
    "description",
    "parent.groupId",
    "parent.artifactId",
    "parent.version",
)


def _legacy_project_alias(propname: str) -> str | None:
    """
    The ``project.*`` expression a deprecated alias stands for, or None.

    Maven 3 still resolves the Maven 2 spellings ``${pom.X}`` and unprefixed
    ``${X}`` (e.g. ``${version}``) against the model, with a deprecation warning.
    It does so only when no property of that name exists, which is why this is
    consulted only as a fallback after a property lookup.
    """
    if propname.startswith("pom."):
        return "project." + propname[len("pom.") :]
    if propname in _UNPREFIXED_PROJECT_FIELDS:
        return "project." + propname
    return None


def _os_is_family(family: str, os_name: str | None, os_family: str | None) -> bool:
    """
    Check whether the OS belongs to the given (lowercase) family.

    Follows the rules of plexus-utils Os.isFamily, which Maven uses for <os>
    profile activation, falling back to comparing against the declared family.
    """
    if os_family and os_family.lower() == family:
        return True
    if not os_name:
        return False
    name = os_name.lower()
    is_windows = "windows" in name
    if family == "windows":
        return is_windows
    if family == "win9x":
        return is_windows and any(v in name for v in ("95", "98", "me", "ce"))
    if family == "winnt":
        return is_windows and not any(v in name for v in ("95", "98", "me", "ce"))
    if family == "dos":
        return is_windows or "netware" in name or "os/2" in name
    if family == "mac":
        return "mac" in name
    if family == "unix":
        return not (
            is_windows
            or any(v in name for v in ("os/2", "netware", "openvms", "z/os", "os/400"))
            or ("mac" in name and not name.endswith("x"))
        )
    if family in ("os/2", "netware", "openvms", "z/os", "os/400", "tandem"):
        return family.replace("tandem", "nonstop_kernel") in name
    return False
