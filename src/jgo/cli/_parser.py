"""
CLI argument parser for jgo.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import rich_click as click

from ..config import GlobalSettings
from ..constants import VERSION
from ..parse import set_full_coordinates
from ..styles import JGO_TOML, STYLES, syntax, tip
from ..util.logging import setup_logging
from ._args import (
    PLATFORM_ALIASES,
    PLATFORMS,
)
from ._commands.add import add
from ._commands.config import config
from ._commands.info import (
    classpath,
    coords,
    deplist,
    deptree,
    entrypoints,
    envdir,
    jars,
    javainfo,
    mains,
    manifest,
    modulepath,
    path_cmd,
    pom,
)
from ._commands.init import init
from ._commands.list import list_cmd
from ._commands.lock import lock
from ._commands.remove import remove
from ._commands.run import run
from ._commands.search import search
from ._commands.sync import sync
from ._commands.tree import tree
from ._commands.update import update
from ._commands.versions import versions
from ._console import setup_consoles
from .rich._logging import setup_rich_logging

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

_log = logging.getLogger(__name__)


# Custom Click group that handles shorthand endpoint syntax and shortcuts
class JgoGroup(click.RichGroup):
    """Custom group that auto-detects shorthand endpoint syntax and shortcuts."""

    def invoke(self, ctx: click.Context) -> None:
        """
        Override to handle shorthand endpoint detection and bare shortcuts.

        Resolution policy:
        1. Built-in commands take precedence
        2. If first arg contains ':', treat as endpoint and inject 'run'
        3. If first arg is a configured shortcut (and not a command), inject 'run'
        4. Otherwise, fall through to normal Click behavior
        """
        if not ctx.protected_args:
            return super().invoke(ctx)

        first_arg = ctx.protected_args[0]

        # Check if it's a built-in command (takes precedence)
        if first_arg in self.commands:
            return super().invoke(ctx)

        # Check if it's an endpoint (contains ':')
        if ":" in first_arg:
            ctx.protected_args.insert(0, "run")
            return super().invoke(ctx)

        # Check if it's a configured shortcut
        try:
            settings = GlobalSettings.load()
            if first_arg in settings.shortcuts:
                # It's a shortcut - inject 'run' command
                ctx.protected_args.insert(0, "run")
                return super().invoke(ctx)
        except Exception as e:
            # If we can't load settings, just fall through
            _log.warning(f"Could not load settings to check shortcuts: {e}")

        return super().invoke(ctx)


# Global options (available to all commands)
def global_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to add global options to commands."""
    # General options
    f = click.option(
        "-v",
        "--verbose",
        count=True,
        help="Verbose output (can be repeated: -vv, -vvv).",
    )(f)
    f = click.option("-q", "--quiet", is_flag=True, help="Suppress all output.")(f)
    f = click.option(
        "--wrap",
        type=click.Choice(["auto", "smart", "raw"]),
        default="auto",
        help=f"Control line wrapping: "
        f"{syntax('auto')} (default: smart for TTY, raw for pipes/files), "
        f"{syntax('smart')} (Rich's intelligent wrapping at word boundaries), "
        f"{syntax('raw')} (natural terminal wrapping, no constraints).",
    )(f)
    f = click.option(
        "--color",
        type=click.Choice(["auto", "rich", "styled", "plain", "always", "never"]),
        default="auto",
        help=f"Control output formatting: "
        f"{syntax('auto')} (default: detect TTY), "
        f"{syntax('rich')} (force color+style), "
        f"{syntax('styled')} (bold/italic only, no color), "
        f"{syntax('plain')} (no ANSI codes). "
        f"Aliases: {syntax('always')}=rich, {syntax('never')}=plain.",
        envvar="COLOR",
        show_envvar=True,
    )(f)
    f = click.option(
        "-f",
        "--file",
        type=click.Path(path_type=Path),
        metavar="FILE",
        help=f"Use specific environment file (default: {JGO_TOML}).",
    )(f)
    f = click.option(
        "--dry-run",
        is_flag=True,
        help="Show what would be done without doing it. Note: while this mode prevents the primary action (e.g. running Java, creating files), jgo may still download dependencies and build cached environments as needed to report accurate information.",
    )(f)

    # Cache options
    f = click.option(
        "-u",
        "--update",
        is_flag=True,
        help="Update cached environment.",
        envvar="JGO_UPDATE",
        show_envvar=True,
    )(f)
    f = click.option(
        "--offline",
        is_flag=True,
        help="Work offline, don't download.",
        envvar="JGO_OFFLINE",
        show_envvar=True,
    )(f)
    f = click.option(
        "--no-cache",
        is_flag=True,
        help="Skip cache entirely, always rebuild.",
        envvar="JGO_NO_CACHE",
        show_envvar=True,
    )(f)
    f = click.option(
        "--timeout",
        type=int,
        default=10,
        metavar="SECONDS",
        help="HTTP timeout for artifact downloads and metadata fetches (default: 10).",
        envvar="JGO_TIMEOUT",
        show_envvar=True,
    )(f)
    f = click.option(
        "--cache-dir",
        type=click.Path(path_type=Path),
        metavar="PATH",
        help="Override cache directory.",
        envvar="JGO_CACHE_DIR",
        show_envvar=True,
    )(f)
    f = click.option(
        "--repo-cache",
        type=click.Path(path_type=Path),
        metavar="PATH",
        help="Override Maven repo cache.",
        envvar="M2_REPO",
        show_envvar=True,
    )(f)

    # Maven options
    f = click.option(
        "--resolver",
        type=click.Choice(["auto", "python", "mvn"]),
        default="auto",
        help="Dependency resolver: auto (default), python, or mvn",
    )(f)
    f = click.option(
        "-r",
        "--repository",
        multiple=True,
        metavar="NAME:URL",
        help="Add remote Maven repository.",
    )(f)
    f = click.option(
        "--include-optional",
        is_flag=True,
        help="Include optional dependencies of endpoint coordinates in the environment.",
        envvar="JGO_INCLUDE_OPTIONAL",
        show_envvar=True,
    )(f)
    f = click.option(
        "-m",
        "--managed",
        "managed",
        flag_value=False,
        default=False,
        hidden=True,
        help="[DEPRECATED] Enable dependency management (this is now the default and has no effect).",
    )(f)

    # Java options
    f = click.option(
        "--java-version",
        type=int,
        metavar="VERSION",
        help="Force specific Java version (e.g., 17).",
        envvar="JAVA_VERSION",
        show_envvar=True,
    )(f)
    f = click.option(
        "--java-vendor",
        metavar="VENDOR",
        help="Prefer specific Java vendor (e.g., 'adoptium', 'zulu').",
    )(f)
    f = click.option(
        "--system-java",
        "use_system_java",
        is_flag=True,
        help="Use system Java instead of downloading Java on demand.",
    )(f)

    # JVM options
    f = click.option(
        "--gc",
        "gc_options",
        multiple=True,
        metavar="FLAG",
        help="GC options. Use shorthand (e.g., --gc=G1, --gc=Z) or explicit form (--gc=-XX:+UseZGC). "
        "Special values: 'auto' (smart defaults), 'none' (disable GC flags). Can be repeated.",
    )(f)
    f = click.option(
        "--max-heap",
        metavar="SIZE",
        help="Maximum heap size (e.g., 4G, 512M). Overrides auto-detection.",
    )(f)
    f = click.option(
        "--min-heap",
        metavar="SIZE",
        help="Minimum/initial heap size (e.g., 512M, 1G).",
    )(f)

    # Profile constraints
    all_platforms = list(PLATFORMS.keys()) + list(PLATFORM_ALIASES.keys())
    f = click.option(
        "--platform",
        type=click.Choice(all_platforms),
        metavar="PLATFORM",
        help=f"Target platform for profile activation. "
        f"Sets os-name, os-family, and os-arch together. "
        f"Use '{syntax('jgo --platform x')}' to see list of options.",
    )(f)
    f = click.option(
        "--os-name",
        metavar="NAME",
        help="Set OS name for profile activation (e.g., 'Linux', 'Windows'). Use 'auto' to auto-detect. Overrides --platform.",
    )(f)
    f = click.option(
        "--os-family",
        metavar="FAMILY",
        help="Set OS family for profile activation (e.g., 'unix', 'windows'). Use 'auto' to auto-detect. Overrides --platform.",
    )(f)
    f = click.option(
        "--os-arch",
        metavar="ARCH",
        help="Set OS architecture for profile activation (e.g., 'amd64', 'aarch64'). Use 'auto' to auto-detect. Overrides --platform.",
    )(f)
    f = click.option(
        "--os-version",
        metavar="VERSION",
        help="Set OS version for profile activation (e.g., '5.1.2600').",
    )(f)
    f = click.option(
        "--property",
        "-D",
        "properties",
        multiple=True,
        metavar="KEY=VALUE",
        help="Set property for profile activation.",
    )(f)

    # Advanced options
    f = click.option(
        "--links",
        type=click.Choice(["hard", "soft", "copy", "auto"]),
        default=None,
        help="How to link JARs: hard, soft, copy, or auto (default: from config or auto)",
    )(f)
    f = click.option(
        "--lenient",
        is_flag=True,
        help="Warn instead of failing on unresolved dependencies.",
        envvar="JGO_LENIENT",
        show_envvar=True,
    )(f)

    # Module path options
    f = click.option(
        "--class-path-only",
        is_flag=True,
        help="Force all JARs to classpath (disable module detection).",
    )(f)
    f = click.option(
        "--module-path-only",
        is_flag=True,
        help="Force all JARs to module-path (treat as modular).",
    )(f)

    f = click.option(
        "--full-coordinates",
        is_flag=True,
        help="Include coordinate components with default values (jar packaging, compile scope).",
    )(f)
    f = click.option(
        "--ignore-config", is_flag=True, help="Ignore ~/.config/jgo.conf file."
    )(f)
    # Hidden alias for backward compatibility
    f = click.option("--ignore-jgorc", "ignore_config", is_flag=True, hidden=True)(f)

    # Version flag
    def _print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
        if value:
            click.echo(f"jgo {VERSION}")
            ctx.exit(0)

    f = click.option(
        "--version",
        is_flag=True,
        callback=_print_version,
        expose_value=False,
        is_eager=True,
        help="Show jgo version and exit.",
    )(f)

    return f


@click.group(
    cls=JgoGroup,
    invoke_without_command=True,
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    },
    help=f"""[bold]Environment manager and launcher for Java programs.[/]

Launch Java applications directly from [bold {STYLES["domain"]}]Maven coordinates[/],
build reproducible environments, manage Java versions,
and resolve dependencies -- [bold]without manual installation[/].""",
)
@global_options
@click.pass_context
def cli(ctx: click.Context, **kwargs: Any) -> None:
    """
    Main CLI entry point.

    Handles both:
    - Command mode: jgo <command> [options]
    - Legacy endpoint mode: jgo <endpoint> [options]
    """
    # Configure console and logging based on CLI flags
    color = kwargs.get("color", "auto")
    quiet = kwargs.get("quiet", False)
    wrap = kwargs.get("wrap", "smart")
    verbose = kwargs.get("verbose", 0)

    # Setup console instances (for both data output and logging)
    setup_consoles(color=color, quiet=quiet, wrap=wrap)

    # Configure coordinate display
    full_coordinates = kwargs.get("full_coordinates", False)
    set_full_coordinates(full_coordinates)

    # Setup logging levels
    logger = setup_logging(verbose=verbose)

    # Setup Rich logging handler (CLI layer responsibility)
    setup_rich_logging(logger, verbose=verbose)

    # Store global options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj.update(kwargs)

    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


# Register top-level commands
cli.add_command(add)
cli.add_command(config)
cli.add_command(init)
cli.add_command(list_cmd)
cli.add_command(lock)
cli.add_command(remove)
cli.add_command(run)
cli.add_command(search)
cli.add_command(sync)
cli.add_command(tree)
cli.add_command(update)


@cli.group(
    help="Show information about environment or artifact.",
    epilog=tip(
        f"To see the launch command, use: {syntax('jgo --dry-run run <endpoint>')}"
    ),
    invoke_without_command=True,
)
@click.pass_context
def info(ctx: click.Context) -> None:
    """
    Show information about a jgo environment or Maven artifact.

    Use subcommands to specify what information to display:
      classpath     - Show classpath (all JARs)
      coords        - Show Maven coordinates a JAR was built from
      modulepath    - Show module-path (modular JARs only)
      jars          - Show all JARs with section headers
      mains         - Show classes with public main methods
      deptree       - Show dependency tree
      deplist       - Show flat list of dependencies
      envdir        - Show environment directory path
      path          - Show local file path of an artifact
      javainfo      - Show Java version requirements
      entrypoints   - Show entrypoints from jgo.toml
      versions      - List available versions of an artifact

    Examples:
      jgo info classpath org.python:jython-standalone
      jgo info coords /path/to/some.jar
      jgo info jars org.scijava:scijava-common
      jgo info mains org.scijava:scijava-common
      jgo info modulepath org.scijava:scijava-common
      jgo info envdir org.scijava:scijava-common
      jgo info path org.scijava:scijava-common:2.99.0
      jgo info javainfo org.scijava:scijava-common
      jgo info deptree org.scijava:scijava-common
      jgo info versions org.python:jython-standalone
      jgo info entrypoints

    Related:
      To see the launch command: jgo --dry-run run <endpoint>
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(2)


# Register info subcommands
info.add_command(classpath)
info.add_command(coords)
info.add_command(deplist)
info.add_command(deptree)
info.add_command(entrypoints)
info.add_command(envdir)
info.add_command(jars)
info.add_command(javainfo)
info.add_command(mains)
info.add_command(manifest)
info.add_command(modulepath)
info.add_command(path_cmd)
info.add_command(pom)
info.add_command(versions)


@cli.command(help="Display jgo's version.")
def version() -> None:
    """Display jgo's version."""
    click.echo(f"jgo {VERSION}")


def _require_group(cmd: click.Command | None, name: str) -> click.Group:
    """Ensure command is a Group, or raise ClickException."""
    if cmd is None:
        raise click.ClickException(f"Unknown command '{name}'")
    if not isinstance(cmd, click.Group):
        raise click.ClickException(f"'{name}' is not a command group")
    return cmd


def _build_prog_name(ctx: click.Context, cmd_name: str) -> str:
    """Build full command path (e.g., 'jgo config shortcut')."""
    path_parts: list[str] = []
    temp_ctx = ctx
    while temp_ctx and temp_ctx.parent is not None:
        if temp_ctx.info_name:
            path_parts.insert(0, temp_ctx.info_name)
        temp_ctx = temp_ctx.parent

    root_name = ctx.find_root().info_name or ""
    if "python" in root_name:
        root_name = "jgo"
    if root_name:
        path_parts.insert(0, root_name)

    return " ".join(path_parts + [cmd_name])


@cli.command(
    context_settings={
        "ignore_unknown_options": True,
        "allow_interspersed_args": False,
    }
)
@click.argument("commands", nargs=-1, required=False)
@click.pass_context
def help(ctx: click.Context, commands: tuple[str, ...]) -> None:
    """Show help for jgo or a specific command.

    Examples:
      jgo help              - Show main help
      jgo help version      - Show help for 'version' command
      jgo help run          - Show help for 'run' command
      jgo help config shortcut  - Show help for nested 'config shortcut' command
    """
    parent: click.Context = ctx.parent or ctx

    if not commands:
        # No command specified - show main help
        click.echo(parent.get_help())
        return

    current_group = _require_group(parent.command, parent.info_name or "")
    current_ctx = parent

    for i, cmd_name in enumerate(commands):
        cmd = current_group.commands.get(cmd_name)

        if i == len(commands) - 1:
            # Final command - show help (doesn't need to be a group)
            if cmd is None:
                raise click.ClickException(f"Unknown command '{cmd_name}'")
            prog_name = _build_prog_name(current_ctx, cmd_name)
            cmd.main(["--help"], prog_name=prog_name, standalone_mode=False)
            return

        # Intermediate command - must be a group
        current_group = _require_group(cmd, cmd_name)
        current_ctx = click.Context(
            current_group, info_name=cmd_name, parent=current_ctx
        )


if __name__ == "__main__":
    cli()
