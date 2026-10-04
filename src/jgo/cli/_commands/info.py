"""jgo info - Show information about environment or artifact"""

from __future__ import annotations

import logging
import xml.dom.minidom
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click
from click.exceptions import Exit as ClickExit

from ...config import GlobalSettings
from ...env import (
    EnvironmentSpec,
    JarCoordinate,
    embedded_pom_entries,
    jar_coordinates,
    jar_sha1,
    parse_manifest,
    read_embedded_pom,
    read_raw_manifest,
)
from ...parse import Coordinate, Endpoint

if TYPE_CHECKING:
    from ...env import Environment, EnvironmentBuilder
    from ...maven import MavenContext
    from .._args import ParsedArgs

from ...styles import (
    AT_MAINCLASS,
    COORD_HELP_FULL,
    JGO_TOML,
    PLUS_OPERATOR,
    header,
    tip,
)
from .._args import build_parsed_args, classify_input, resolve_pom_input
from .._console import console_print
from .._context import create_environment_builder, create_maven_context
from .._output import (
    SourceReport,
    environment_report,
    paths_report,
    print_classpath,
    print_dependencies,
    print_jar_coordinates,
    print_jars,
    print_java_info,
    print_main_classes,
    print_modulepath,
    print_pom_dependencies,
)

_log = logging.getLogger(__name__)


@click.command(help="Show classpath.")
@click.argument(
    "endpoint",
    required=False,
    cls=click.RichArgument,
    help=f"Maven coordinates (single or combined with {PLUS_OPERATOR}) "
    f"optionally followed by {AT_MAINCLASS}",
)
@click.pass_context
def classpath(ctx: click.Context, endpoint: str | None) -> None:
    """Show the classpath for the given endpoint."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Build environment
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        environment = _from_spec_or_die(ctx, builder, spec, args.update)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        environment = builder.from_endpoint(endpoint, update=args.update)

    print_classpath(environment)
    ctx.exit(0)


@click.command(help="Show environment directory path.")
@click.argument(
    "endpoint",
    required=False,
    cls=click.RichArgument,
    help=f"Maven coordinates (single or combined with {PLUS_OPERATOR}) "
    f"optionally followed by {AT_MAINCLASS}",
)
@click.pass_context
def envdir(ctx: click.Context, endpoint: str | None) -> None:
    """Show the cache/environment directory for the given endpoint or jgo project."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Build environment
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        environment = _from_spec_or_die(ctx, builder, spec, args.update)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        environment = builder.from_endpoint(endpoint, update=args.update)

    console_print(environment.path)
    ctx.exit(0)


@click.command(help="Show all JAR paths (classpath + module-path).")
@click.argument(
    "endpoint",
    required=False,
    cls=click.RichArgument,
    help=f"Maven coordinates (single or combined with {PLUS_OPERATOR}) "
    f"optionally followed by {AT_MAINCLASS}",
)
@click.pass_context
def jars(ctx: click.Context, endpoint: str | None) -> None:
    """Show all JAR paths with section headers for classpath and module-path."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Build environment
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        environment = _from_spec_or_die(ctx, builder, spec, args.update)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        environment = builder.from_endpoint(endpoint, update=args.update)

    print_jars(environment)
    ctx.exit(0)


@click.command(help="Show module-path.")
@click.argument("endpoint", required=False)
@click.pass_context
def modulepath(ctx: click.Context, endpoint: str | None) -> None:
    """Show the module-path for the given endpoint."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Build environment
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        environment = _from_spec_or_die(ctx, builder, spec, args.update)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        environment = builder.from_endpoint(endpoint, update=args.update)

    print_modulepath(environment)
    ctx.exit(0)


@click.command(help="Show classes with public main methods.")
@click.argument("endpoint", required=False)
@click.pass_context
def mains(ctx: click.Context, endpoint: str | None) -> None:
    """Find and list all classes with public static void main(String[]) methods."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Build environment
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        environment = _from_spec_or_die(ctx, builder, spec, args.update)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        environment = builder.from_endpoint(endpoint, update=args.update)

    print_main_classes(environment)
    ctx.exit(0)


@click.command(help="Show dependency tree.")
@click.argument("endpoint", required=False)
@click.pass_context
def deptree(ctx: click.Context, endpoint: str | None) -> None:
    """Show the dependency tree for the given endpoint."""
    _print_deps(ctx, endpoint, list_mode=False)


@click.command(help="Show flat list of dependencies.")
@click.argument("endpoint", required=False)
@click.option(
    "--direct", is_flag=True, help="Show only direct dependencies (non-transitive)."
)
@click.pass_context
def deplist(ctx: click.Context, endpoint: str | None, direct: bool) -> None:
    """Show a flat list of all dependencies for the given endpoint."""
    _print_deps(ctx, endpoint, list_mode=True, direct=direct)


@click.command(help="Show Java version requirements.")
@click.argument("inputs", nargs=-1)
@click.option(
    "--direct",
    is_flag=True,
    help="Analyze the named artifacts plus their direct dependencies only.",
)
@click.option(
    "--self",
    "self_only",
    is_flag=True,
    help="Analyze only the named artifacts themselves, with no dependencies.",
)
@click.pass_context
def javainfo(
    ctx: click.Context, inputs: tuple[str, ...], direct: bool, self_only: bool
) -> None:
    """Show Java version requirements for endpoints, POMs, JARs, or class files.

    Accepts any mix of Maven coordinates, local POM files/directories, .jar files,
    .class files, and directories of compiled classes. Each argument is analyzed as
    an independent source.
    """

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)

    if direct and self_only:
        _log.error("--direct and --self are mutually exclusive")
        ctx.exit(1)

    args = build_parsed_args(opts, endpoint=None, command="info")
    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    reports: list[SourceReport] = []

    if inputs:
        for arg in inputs:
            reports.append(
                _javainfo_source(ctx, arg, builder, context, args, direct, self_only)
            )
    else:
        # No inputs: fall back to spec mode (jgo.toml), matching other subcommands.
        if args.is_spec_mode():
            spec_file = args.get_spec_file()
            if not spec_file.exists():
                _log.error(f"{spec_file} not found")
                ctx.exit(1)
            spec = EnvironmentSpec.load(spec_file)
            environment = _from_spec_or_die(ctx, builder, spec, args.update)
            reports.append(environment_report(environment, label=str(spec_file)))
        else:
            _log.error("No endpoint specified")
            ctx.exit(1)

    print_java_info(reports)
    ctx.exit(0)


def _javainfo_source(
    ctx: click.Context,
    arg: str,
    builder: EnvironmentBuilder,
    context: MavenContext,
    args: ParsedArgs,
    direct: bool,
    self_only: bool,
) -> SourceReport:
    """Build a SourceReport for a single javainfo argument."""

    kind, path = classify_input(arg)

    if kind == "pom":
        return _javainfo_pom_report(ctx, path, context, args, direct, self_only)

    if kind in ("jar", "class"):
        if not path.exists():
            _log.error(f"{path} not found")
            ctx.exit(1)
        return paths_report(arg, [path])

    if kind == "dir":
        local = sorted(path.rglob("*.jar")) + sorted(path.rglob("*.class"))
        if not local:
            _log.error(f"No .jar or .class files found in {path}")
            ctx.exit(1)
        return paths_report(arg, local)

    # kind == "coordinate"
    return _javainfo_coordinate_report(
        ctx, arg, builder, context, args, direct, self_only
    )


def _resolve_artifact_path(artifact) -> Path | None:
    """Resolve an artifact to a local JAR path, returning None on failure."""
    try:
        resolved = artifact.resolve()
    except Exception as e:
        _log.debug(f"Could not resolve {artifact}: {e}")
        return None
    return resolved


def _javainfo_coordinate_report(
    ctx: click.Context,
    arg: str,
    builder: EnvironmentBuilder,
    context: MavenContext,
    args: ParsedArgs,
    direct: bool,
    self_only: bool,
) -> SourceReport:
    """Build a SourceReport for a Maven coordinate / endpoint argument."""

    # Default (transitive): build the full environment, exactly as before.
    if not direct and not self_only:
        environment = builder.from_endpoint(arg, update=args.update)
        return environment_report(environment, label=arg)

    # --self / --direct: resolve the named artifacts (and direct deps) directly.
    try:
        parsed = Endpoint.parse(arg)
    except ValueError as e:
        _log.error(f"Invalid endpoint format: {e}")
        ctx.exit(1)

    paths: list[Path] = []
    for coord in parsed.coordinates:
        version = coord.version or "RELEASE"
        component = context.project(coord.groupId, coord.artifactId).at_version(version)
        artifact = component.artifact(
            classifier=coord.classifier or "",
            packaging=coord.packaging or "jar",
        )
        resolved = _resolve_artifact_path(artifact)
        if resolved is not None:
            paths.append(resolved)

        if direct:
            _root, deps = context.pom_dependency_list(
                component.pom(),
                transitive=False,
                optional_depth=args.get_effective_optional_depth(),
            )
            for node in deps:
                resolved = _resolve_artifact_path(node.dep.artifact)
                if resolved is not None:
                    paths.append(resolved)

    return paths_report(arg, _dedup_paths(paths))


def _javainfo_pom_report(
    ctx: click.Context,
    pom_path: Path,
    context: MavenContext,
    args: ParsedArgs,
    direct: bool,
    self_only: bool,
) -> SourceReport:
    """Build a SourceReport for a local project POM argument."""

    from ...maven import POM

    if not pom_path.exists():
        _log.error(f"{pom_path} not found")
        ctx.exit(1)

    pom = POM(pom_path)
    label = str(pom_path)

    try:
        if self_only:
            # Just the project's own artifact (no dependencies).
            root, _deps = context.pom_dependency_list(pom, transitive=False)
            resolved = _resolve_artifact_path(root.dep.artifact)
            paths = [resolved] if resolved is not None else []
        else:
            _root, deps = context.pom_dependency_list(
                pom,
                transitive=not direct,
                optional_depth=args.get_effective_optional_depth(),
            )
            paths = []
            for node in deps:
                resolved = _resolve_artifact_path(node.dep.artifact)
                if resolved is not None:
                    paths.append(resolved)
    except (RuntimeError, ValueError) as e:
        _log.error(f"Failed to resolve {pom_path}: {e}")
        ctx.exit(1)

    return paths_report(label, _dedup_paths(paths))


def _dedup_paths(paths: list[Path]) -> list[Path]:
    """De-duplicate paths while preserving first-seen order."""
    seen: set[Path] = set()
    result: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


@click.command(help=f"Show entrypoints from {JGO_TOML}.")
@click.pass_context
def entrypoints(ctx: click.Context) -> None:
    """Show available entrypoints defined in jgo.toml."""

    opts = ctx.obj
    args = build_parsed_args(opts, endpoint=None, command="info")

    spec_file = args.file or Path("jgo.toml")

    if not spec_file.exists():
        _log.error(f"{spec_file} not found")
        ctx.exit(1)

    spec = EnvironmentSpec.load(spec_file)

    if not spec.entrypoints:
        console_print("No entrypoints defined")
        ctx.exit(0)

    console_print("Available entrypoints:")
    for name, main_class in spec.entrypoints.items():
        marker = " (default)" if name == spec.default_entrypoint else ""
        console_print(f"  {name}: {main_class}{marker}")

    ctx.exit(0)


@click.command(help="Show Maven coordinates a JAR was built from.")
@click.argument(
    "inputs",
    nargs=-1,
    cls=click.RichArgument,
    help=f"Local JAR files, directories to scan, or coordinates in format "
    f"{COORD_HELP_FULL}",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="List bundled coordinates as well, not just each JAR's own",
)
@click.option(
    "--remote",
    is_flag=True,
    help="Identify JARs lacking Maven metadata by checksum lookup on Maven Central",
)
@click.pass_context
def coords(
    ctx: click.Context, inputs: tuple[str, ...], show_all: bool, remote: bool
) -> None:
    """Show the Maven coordinates that JAR files appear to have been built from.

    Accepts any mix of local .jar files, directories to scan for JARs, and Maven
    coordinates. Coordinates come from the Maven metadata that build tools embed
    under META-INF/maven; an uber-JAR carries the metadata of everything it
    bundles, so the coordinate that looks like the JAR's own identity is listed
    first and the rest are counted as bundled.
    """

    opts = ctx.obj
    args = build_parsed_args(opts, endpoint=None, command="info")

    if not inputs:
        _log.error("No JAR specified")
        ctx.exit(1)

    if remote and args.offline:
        _log.warning("Ignoring --remote in offline mode")
        remote = False

    results: list[tuple[Path, list[JarCoordinate]]] = []
    for arg in inputs:
        for jar_path in _coords_jars(ctx, arg):
            coordinates = jar_coordinates(jar_path)
            # Manifest-derived coordinates are guesswork, but a checksum match is
            # exact, so let Maven Central overrule them when it knows the file.
            if remote and all(c.source == "manifest" for c in coordinates):
                coordinates = _central_coordinates(jar_path) or coordinates
            results.append((jar_path, coordinates))

    print_jar_coordinates(results, show_all=show_all)

    if not remote and any(
        all(c.source == "manifest" for c in coordinates) for _, coordinates in results
    ):
        console_print(
            tip("Use --remote to identify JARs by checksum via Maven Central")
        )

    ctx.exit(0)


def _coords_jars(ctx: click.Context, arg: str) -> list[Path]:
    """Expand a single ``jgo info coords`` argument into JAR paths."""

    path = Path(arg).expanduser()
    if path.is_dir():
        jars = sorted(path.rglob("*.jar"))
        if not jars:
            _log.error(f"No .jar files found in {path}")
            ctx.exit(1)
        return jars

    return [_resolve_jar_or_die(ctx, arg)]


def _central_coordinates(jar_path: Path) -> list[JarCoordinate]:
    """Identify a JAR by SHA-1 checksum, via the Maven Central search API."""

    from ...maven import coordinates_by_sha1

    try:
        matches = coordinates_by_sha1(jar_sha1(jar_path))
    except (RuntimeError, OSError) as e:
        _log.warning(f"Maven Central lookup failed for {jar_path.name}: {e}")
        return []

    # A checksum match is exact, so the first hit is the JAR's identity; further
    # hits are the same bytes republished under another coordinate.
    return [
        JarCoordinate(
            groupId=match.groupId,
            artifactId=match.artifactId,
            version=match.version,
            classifier=match.classifier,
            source="central",
            primary=(i == 0),
        )
        for i, match in enumerate(matches)
    ]


@click.command(name="path", help="Show local file path of an artifact.")
@click.argument(
    "targets",
    nargs=-1,
    required=True,
    cls=click.RichArgument,
    help=f"Maven coordinates in format {COORD_HELP_FULL}",
)
@click.pass_context
def path_cmd(ctx: click.Context, targets: tuple[str, ...]) -> None:
    """Show the local repository path of each artifact, downloading as needed.

    Prints one path per line, in the order given, so the output composes with
    other tools, e.g. cp "$(jgo info path g:a:v)" .
    """

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=None, command="info")
    maven_context = create_maven_context(args, config.to_dict())

    # Note: Resolve everything before printing, so a failure prints no paths.
    paths = [_resolve_artifact_or_die(ctx, t, maven_context) for t in targets]
    for p in paths:
        # Note: Plain echo, so Rich never wraps or marks up a path.
        click.echo(str(p))
    ctx.exit(0)


@click.command(help="Show JAR manifest.")
@click.argument(
    "target",
    required=True,
    cls=click.RichArgument,
    help=f"Maven coordinate in format {COORD_HELP_FULL}, or path to a local JAR",
)
@click.option("--raw", is_flag=True, help="Show raw manifest contents")
@click.pass_context
def manifest(ctx: click.Context, target: str, raw: bool) -> None:
    """Show the JAR manifest for the given coordinate or local JAR file."""

    try:
        jar_path = _resolve_jar_or_die(ctx, target)

        # Read and display manifest
        if raw:
            manifest_content = read_raw_manifest(jar_path)
            if manifest_content is None:
                _log.error(f"No MANIFEST.MF found in {jar_path}")
                ctx.exit(1)
            console_print(manifest_content, end="")
        else:
            manifest_dict = parse_manifest(jar_path)
            if manifest_dict is None:
                _log.error(f"No MANIFEST.MF found in {jar_path}")
                ctx.exit(1)

            # Display parsed manifest
            for key, value in manifest_dict.items():
                console_print(f"{key}: {value}")

    except (SystemExit, ClickExit):
        # Context.exit() raises click's Exit, which is a RuntimeError.
        raise
    except Exception as e:
        _log.error(f"{e}")
        ctx.exit(1)


@click.command(help="Show POM content.")
@click.argument(
    "target",
    required=True,
    cls=click.RichArgument,
    help=f"Maven coordinate in format {COORD_HELP_FULL}, or path to a local JAR",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Dump every POM embedded in a JAR, not just its own",
)
@click.pass_context
def pom(ctx: click.Context, target: str, show_all: bool) -> None:
    """Show the POM for the given component, or embedded in a local JAR file."""

    opts = ctx.obj

    try:
        jar_path = _local_jar_or_die(ctx, target)
        if jar_path is not None:
            _print_embedded_poms(ctx, jar_path, show_all)
            return

        config = GlobalSettings.load_from_opts(opts)
        args = build_parsed_args(opts, endpoint=target, command="info")

        # Create Maven context
        maven_context = create_maven_context(args, config.to_dict())

        # Parse coordinate to get G:A:V
        coord = _parse_coord_or_die(ctx, target)
        version = coord.version or "RELEASE"

        # Get component
        component = maven_context.project(coord.groupId, coord.artifactId).at_version(
            version
        )

        # Get raw POM and pretty-print
        pom_obj = component.pom()

        if not pom_obj or not pom_obj.source:
            _log.error(f"Could not resolve POM for: {target}")
            ctx.exit(1)

        # Read POM content
        if isinstance(pom_obj.source, Path):
            pom_content = pom_obj.source.read_text()
        else:
            pom_content = str(pom_obj.source)

        console_print(_pretty_xml(pom_content))

    except (SystemExit, ClickExit):
        # Context.exit() raises click's Exit, which is a RuntimeError.
        raise
    except Exception as e:
        _log.error(f"{e}")
        ctx.exit(1)


def _print_embedded_poms(ctx: click.Context, jar_path: Path, show_all: bool) -> None:
    """Dump the POM(s) embedded in a JAR file's META-INF/maven directory."""

    entries = embedded_pom_entries(jar_path)
    if not entries:
        _log.error(f"No embedded POM found in {jar_path}")
        ctx.exit(1)

    if not show_all and len(entries) > 1:
        # Restrict to the JAR's own POM; the rest belong to bundled dependencies.
        own_entry = next(
            (
                c.pom_entry
                for c in jar_coordinates(jar_path)
                if c.primary and c.pom_entry
            ),
            None,
        )
        if own_entry is None:
            _log.error(
                f"{jar_path.name} embeds {len(entries)} POMs and none is clearly "
                f"its own; use --all to dump them all"
            )
            ctx.exit(1)
        entries = [own_entry]

    for i, entry in enumerate(entries):
        content = read_embedded_pom(jar_path, entry)
        if content is None:
            _log.error(f"Could not read {entry} from {jar_path}")
            ctx.exit(1)
        if len(entries) > 1:
            if i > 0:
                console_print()
            console_print(header(entry))
        console_print(_pretty_xml(content))


def _pretty_xml(content: str) -> str:
    """Pretty-print XML, falling back to the raw content if it cannot be parsed."""
    try:
        dom = xml.dom.minidom.parseString(content)
        pretty_xml = dom.toprettyxml(indent="  ")
        # Remove extra blank lines that toprettyxml adds
        lines = [line for line in pretty_xml.split("\n") if line.strip()]
        return "\n".join(lines)
    except Exception:
        return content


def _local_jar_or_die(ctx: click.Context, target: str) -> Path | None:
    """
    Interpret a CLI argument as a local JAR file.

    Returns the JAR path, or None if the argument is a Maven coordinate rather
    than a local path. Exits with an error if a local JAR file was named but is
    missing or is not actually a JAR.
    """
    kind, path = classify_input(target)
    if kind != "jar":
        return None
    if not path.exists():
        _log.error(f"{path} not found")
        ctx.exit(1)
    if not zipfile.is_zipfile(path):
        _log.error(f"Not a valid JAR file: {path}")
        ctx.exit(1)
    return path


def _resolve_jar_or_die(ctx: click.Context, target: str) -> Path:
    """
    Resolve a CLI argument to a local JAR file.

    Accepts either the path of a local JAR file, or a Maven coordinate to be
    resolved (downloading it if needed). Exits with an error if no JAR results.
    """
    jar_path = _local_jar_or_die(ctx, target)
    if jar_path is not None:
        return jar_path

    resolved = _resolve_artifact_or_die(ctx, target)
    if not zipfile.is_zipfile(resolved):
        _log.error(f"Not a valid JAR file: {resolved}")
        ctx.exit(1)
    return resolved


def _resolve_artifact_or_die(
    ctx: click.Context, target: str, maven_context: MavenContext | None = None
) -> Path:
    """
    Resolve a Maven coordinate to a file in the local repository cache.

    Downloads the artifact if needed. Any packaging is accepted, not only JARs.
    Exits with an error if the artifact cannot be resolved.
    """
    if maven_context is None:
        opts = ctx.obj
        config = GlobalSettings.load_from_opts(opts)
        args = build_parsed_args(opts, endpoint=target, command="info")
        maven_context = create_maven_context(args, config.to_dict())

    coord = _parse_coord_or_die(ctx, target)
    component = maven_context.project(coord.groupId, coord.artifactId).at_version(
        coord.version or "RELEASE"
    )
    artifact = component.artifact(
        classifier=coord.classifier or "",
        packaging=coord.packaging or "jar",
    )
    try:
        resolved = artifact.resolve()
    except Exception as e:
        _log.error(f"Could not resolve artifact: {target}: {e}")
        ctx.exit(1)

    if not resolved or not resolved.exists():
        _log.error(f"Could not resolve artifact: {target}")
        ctx.exit(1)
    return resolved


def _from_spec_or_die(
    ctx: click.Context, builder: EnvironmentBuilder, spec: EnvironmentSpec, update: bool
) -> Environment:
    """Call builder.from_spec(), printing a clean error and exiting on ValueError."""
    try:
        return builder.from_spec(spec, update=update)
    except ValueError as e:
        _log.error(f"{e} Use 'jgo add <coordinate>' to add dependencies.")
        ctx.exit(1)


def _parse_coord_or_die(ctx: click.Context, coord_str: str) -> Coordinate:
    """Parses a string to a Coordinate, guaranteeing non-None."""
    try:
        return Coordinate.parse(coord_str)
    except ValueError:
        _log.exception(f"Invalid coordinate string: {coord_str}")
        ctx.exit(1)


def _print_deps(
    ctx: click.Context, endpoint: str | None, list_mode: bool, direct: bool = False
) -> None:
    """Common logic for deptree and deplist."""

    opts = ctx.obj
    config = GlobalSettings.load_from_opts(opts)
    args = build_parsed_args(opts, endpoint=endpoint, command="info")

    context = create_maven_context(args, config.to_dict())
    builder = create_environment_builder(args, config.to_dict(), context)

    # Local POM file mode: resolve the real project POM directly.
    try:
        pom_path = resolve_pom_input(endpoint)
    except ValueError as e:
        _log.error(str(e))
        ctx.exit(1)
    if pom_path is not None:
        if not pom_path.exists():
            _log.error(f"{pom_path} not found")
            ctx.exit(1)
        try:
            print_pom_dependencies(
                pom_path,
                context,
                list_mode=list_mode,
                direct_only=direct,
                optional_depth=args.get_effective_optional_depth(),
            )
        except (RuntimeError, ValueError) as e:
            _log.error(f"Failed to resolve {pom_path}: {e}")
            ctx.exit(1)
        ctx.exit(0)

    # Parse coordinates into dependencies
    if args.is_spec_mode():
        spec_file = args.get_spec_file()
        if not spec_file.exists():
            _log.error(f"{spec_file} not found")
            ctx.exit(1)
        spec = EnvironmentSpec.load(spec_file)
        try:
            dependencies = builder.spec_to_dependencies(spec)
        except ValueError as e:
            _log.error(f"Invalid coordinate format: {e}")
            ctx.exit(1)
    else:
        if not endpoint:
            _log.error("No endpoint specified")
            ctx.exit(1)
        try:
            parsed = Endpoint.parse(endpoint)
        except ValueError as e:
            _log.error(f"Invalid endpoint format: {e}")
            ctx.exit(1)
        dependencies = builder._coordinates_to_dependencies(parsed.coordinates)

    print_dependencies(dependencies, context, list_mode=list_mode, direct_only=direct)
    ctx.exit(0)
