"""
Default constants for jgo.

Centralizes hardcoded paths and URLs to avoid duplication across the codebase.
"""

import logging
import os
from pathlib import Path

from .util.platform import get_user_home

_log = logging.getLogger(__name__)


def _get_version() -> str:
    """Get jgo version from package metadata."""
    try:
        # Try importlib.metadata (Python 3.8+)
        from importlib.metadata import version

        return version("jgo")
    except Exception:
        # Fallback: read from pyproject.toml
        try:
            from .util.toml import tomllib

            pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject.exists():
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "unknown")
        except Exception as e:
            _log.debug(f"Could not read version from pyproject.toml: {e}")
        return "unknown"


# Package version
VERSION = _get_version()

# Maven repository URLs
MAVEN_CENTRAL_URL = "https://repo.maven.apache.org/maven2"

# Hosts serving Maven Central, whose releases are immutable once published.
MAVEN_CENTRAL_HOSTS = frozenset({"repo.maven.apache.org", "repo1.maven.org"})

# How long a remote 404 for an artifact is cached (seconds).
DEFAULT_MISS_TTL = 24 * 60 * 60

# Config file display names (these are truly constant)
SETTINGS_FILE_DISPLAY_NAME = "jgo config file"
SETTINGS_FILE_XDG_NAME = "~/.config/jgo.conf"
SETTINGS_FILE_LEGACY_NAME = "~/.jgorc"


# Dynamic path functions (respect environment variables and HOME)
def default_maven_repo() -> Path:
    """
    Get default Maven repository path.

    Respects M2_REPO environment variable, otherwise uses ~/.m2/repository.
    """
    m2_repo = os.getenv("M2_REPO")
    if m2_repo:
        return Path(m2_repo)
    return get_user_home() / ".m2" / "repository"


def default_jgo_cache() -> Path:
    """
    Get default jgo cache directory.

    Respects JGO_CACHE_DIR environment variable, otherwise uses ~/.cache/jgo.
    """
    cache_dir = os.getenv("JGO_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return get_user_home() / ".cache" / "jgo"


def env_settings_path() -> Path | None:
    """
    Get the explicitly requested config file path, if any.

    Respects the JGO_CONFIG_FILE environment variable; returns None if unset.
    """
    config_file = os.getenv("JGO_CONFIG_FILE")
    if config_file:
        return Path(config_file).expanduser()
    return None


def xdg_settings_path() -> Path:
    """
    Get XDG config file path.

    Respects XDG_CONFIG_HOME environment variable if set, otherwise uses ~/.config/jgo.conf.
    """
    xdg_config_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "jgo.conf"
    return get_user_home() / ".config" / "jgo.conf"


def legacy_settings_path() -> Path:
    """
    Get legacy config file path (~/.jgorc).
    """
    return get_user_home() / ".jgorc"
