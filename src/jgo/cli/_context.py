"""
Factory functions for creating Maven contexts, environment builders, and Java runners.

These functions encapsulate the logic for creating the core objects needed
by CLI commands, extracting common configuration from ParsedArgs and config dicts.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..constants import MAVEN_CENTRAL_URL, default_maven_repo
from ..env import EnvironmentBuilder, EnvironmentSpec, LinkStrategy
from ..exec import JavaRunner, JavaSource, JVMConfig, is_gc_flag, normalize_gc_flag
from ..maven import (
    MavenContext,
    MvnResolver,
    ProfileConstraints,
    PythonResolver,
    Resolver,
)
from ..util.logging import is_debug_enabled, is_info_enabled
from ..util.mvn import ensure_maven_available
from .rich._progress import download_progress_callback

if TYPE_CHECKING:
    from ._args import ParsedArgs

_log = logging.getLogger(__name__)


def create_maven_context(args: ParsedArgs, config: dict) -> MavenContext:
    """
    Create Maven context from parsed arguments and configuration.

    Args:
        args: Parsed command line arguments
        config: Global settings

    Returns:
        Configured MavenContext instance
    """

    # Determine resolver
    if args.resolver == "python":
        profile_constraints = ProfileConstraints(
            jdk=str(args.java_version) if args.java_version else None,
            os_name=args.os_name,
            os_family=args.os_family,
            os_arch=args.os_arch,
            os_version=args.os_version,
            properties=args.properties,
        )
        resolver: Resolver = PythonResolver(
            profile_constraints=profile_constraints,
            progress_callback=download_progress_callback,
            lenient=args.lenient,
        )
    elif args.resolver == "mvn":
        mvn_command = ensure_maven_available(offline=args.offline)
        resolver = MvnResolver(
            mvn_command,
            update=args.update,
            debug=is_debug_enabled(),
            offline=args.offline,
        )
    else:  # auto
        profile_constraints = ProfileConstraints(
            jdk=str(args.java_version) if args.java_version else None,
            os_name=args.os_name,
            os_family=args.os_family,
            os_arch=args.os_arch,
            os_version=args.os_version,
            properties=args.properties,
        )
        resolver = PythonResolver(
            profile_constraints=profile_constraints,
            progress_callback=download_progress_callback,
            lenient=args.lenient,
        )  # Default to pure Python

    # Get repo cache path
    repo_cache = args.repo_cache
    if repo_cache is None:
        # Check config, then default
        repo_cache = config.get("repo_cache", default_maven_repo())
    repo_cache = Path(repo_cache).expanduser()

    # Get remote repositories
    remote_repos = {}

    # Start with Maven Central
    remote_repos["central"] = MAVEN_CENTRAL_URL

    # Add from config
    if "repositories" in config:
        remote_repos.update(config["repositories"])

    # Add from command line (overrides config)
    if args.repositories:
        remote_repos.update(args.repositories)

    # Create context
    return MavenContext(
        resolver=resolver,
        repo_cache=repo_cache,
        remote_repos=remote_repos,
        timeout=args.timeout,
        offline=args.offline,
    )


def create_environment_builder(
    args: ParsedArgs, config: dict, context: MavenContext
) -> EnvironmentBuilder:
    """
    Create environment builder from parsed arguments and configuration.

    Args:
        args: Parsed command line arguments
        config: Global settings
        context: Maven context to use

    Returns:
        Configured EnvironmentBuilder instance
    """
    # Determine link strategy
    link_strategy_map = {
        "hard": LinkStrategy.HARD,
        "soft": LinkStrategy.SOFT,
        "copy": LinkStrategy.COPY,
        "auto": LinkStrategy.AUTO,
    }

    # Get link strategy from args, falling back to config if not specified
    links_value = args.links
    if links_value is None:
        # Check config for links setting
        links_value = config.get("links", "auto")
    link_strategy = link_strategy_map[links_value]

    # Get cache directory
    cache_dir = args.cache_dir
    if cache_dir is None:
        # Check config
        cache_dir = config.get("cache_dir")
    # If still None, EnvironmentBuilder will auto-detect

    return EnvironmentBuilder(
        context=context,
        cache_dir=cache_dir,
        link_strategy=link_strategy,
        optional_depth=args.get_effective_optional_depth(),
    )


def create_java_runner(
    args: ParsedArgs, config: dict, spec: EnvironmentSpec | None = None
) -> JavaRunner:
    """
    Create Java runner with 4-tier JVM configuration priority:
    CLI > jgo.toml > ~/.config/jgo.conf > smart defaults

    Args:
        args: Parsed command line arguments
        config: Global settings from ~/.config/jgo.conf
        spec: Optional EnvironmentSpec from jgo.toml (for project-level config)

    Returns:
        Configured JavaRunner instance
    """
    java_source = JavaSource.SYSTEM if args.use_system_java else JavaSource.AUTO

    # ========== 4-Tier Precedence for GC Options ==========
    # Priority: CLI > jgo.toml > ~/.config/jgo.conf > smart defaults
    gc_options = None

    # Tier 1: CLI override (highest priority)
    if args.gc_options:
        if len(args.gc_options) == 1 and args.gc_options[0].lower() == "none":
            gc_options = []  # Explicit disable
        elif len(args.gc_options) == 1 and args.gc_options[0].lower() == "auto":
            # Skip to smart defaults (tier 4)
            pass
        else:
            # Normalize and collect GC flags
            normalized = []
            for gc in args.gc_options:
                result = normalize_gc_flag(gc)
                if result and result != "auto":
                    normalized.append(result)
            gc_options = normalized if normalized else []

    # Tier 2: Project config (jgo.toml)
    if gc_options is None and spec and spec.gc_options:
        raw = spec.gc_options
        if len(raw) == 1 and raw[0].lower() == "none":
            gc_options = []
        elif len(raw) == 1 and raw[0].lower() == "auto":
            pass  # skip to smart defaults
        else:
            normalized = []
            for gc in raw:
                result = normalize_gc_flag(gc)
                if result and result != "auto":
                    normalized.append(result)
            gc_options = normalized if normalized else []

    # Tier 3: Global config (~/.config/jgo.conf)
    if gc_options is None and "jvm" in config:
        jvm_config_section = config["jvm"]
        if "gc" in jvm_config_section or "gc_options" in jvm_config_section:
            gc_value = jvm_config_section.get("gc") or jvm_config_section.get(
                "gc_options"
            )
            raw = [gc_value] if isinstance(gc_value, str) else gc_value
            if raw:
                if len(raw) == 1 and raw[0].lower() == "none":
                    gc_options = []
                elif len(raw) == 1 and raw[0].lower() == "auto":
                    pass  # skip to smart defaults
                else:
                    normalized = []
                    for gc in raw:
                        result = normalize_gc_flag(gc)
                        if result and result != "auto":
                            normalized.append(result)
                    gc_options = normalized if normalized else []

    # Tier 4: Smart defaults (will be applied in JVMConfig.to_jvm_args() based on java_version)
    # Leave gc_options as None to trigger smart defaults

    # ========== 4-Tier Precedence for Heap Settings ==========
    max_heap = None
    min_heap = None

    # Tier 1: CLI
    if args.max_heap:
        max_heap = args.max_heap
    # Tier 2: jgo.toml
    elif spec and spec.max_heap:
        max_heap = spec.max_heap
    # Tier 3: ~/.config/jgo.conf
    elif "jvm" in config and "max_heap" in config["jvm"]:
        max_heap = config["jvm"]["max_heap"]
    # Tier 4: Auto-detect (handled by JVMConfig)

    # Same for min_heap
    if args.min_heap:
        min_heap = args.min_heap
    elif spec and spec.min_heap:
        min_heap = spec.min_heap
    elif "jvm" in config and "min_heap" in config["jvm"]:
        min_heap = config["jvm"]["min_heap"]

    # ========== Merge Extra JVM Args (Additive + Conflict Resolution) ==========
    # Combine from all sources: CLI -- separator + jgo.toml + ~/.config/jgo.conf
    # Apply conflict resolution: structured settings win over extra args
    extra_jvm_args = []

    # Collect from global config
    if "jvm" in config and "jvm_args" in config["jvm"]:
        jvm_args_value = config["jvm"]["jvm_args"]
        if isinstance(jvm_args_value, str):
            extra_jvm_args.extend(jvm_args_value.split(","))
        elif isinstance(jvm_args_value, list):
            extra_jvm_args.extend(jvm_args_value)

    # Add from spec
    if spec and spec.jvm_args:
        extra_jvm_args.extend(spec.jvm_args)

    # Add from CLI -- separator
    if args.jvm_args:
        extra_jvm_args.extend(args.jvm_args)

    # Strip conflicting flags if structured options are set
    if max_heap:
        extra_jvm_args = [arg for arg in extra_jvm_args if not arg.startswith("-Xmx")]
    if min_heap:
        extra_jvm_args = [arg for arg in extra_jvm_args if not arg.startswith("-Xms")]
    if gc_options is not None:
        extra_jvm_args = [arg for arg in extra_jvm_args if not is_gc_flag(arg)]

    # ========== Merge System Properties (Additive) ==========
    system_properties = {}

    # Collect from global config
    if "jvm" in config and "properties" in config["jvm"]:
        system_properties.update(config["jvm"]["properties"])

    # Add from spec
    if spec and spec.properties:
        system_properties.update(spec.properties)

    # Add from CLI (already in args.properties)
    if args.properties:
        system_properties.update(args.properties)

    # ========== Create JVMConfig ==========
    jvm_config = JVMConfig(
        max_heap=max_heap,
        min_heap=min_heap,
        gc_options=gc_options,
        system_properties=system_properties,
        extra_args=extra_jvm_args,
        auto_heap=True,
    )

    verbose = is_info_enabled() and not args.quiet

    return JavaRunner(
        jvm_config=jvm_config,
        java_source=java_source,
        java_version=args.java_version,
        java_vendor=args.java_vendor,
        verbose=verbose,
    )
