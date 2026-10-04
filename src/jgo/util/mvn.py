"""
Utility functions for Maven execution.

This module provides functions to automatically download
and cache Maven when it's not available on the system.
Maven distributions are managed with cjdk's caching mechanism.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

import cjdk

_log = logging.getLogger(__name__)


def ensure_maven_available(offline: bool = False) -> Path:
    """
    Ensure that Maven is available, downloading it if necessary.

    Args:
        offline: If True, never download Maven; it must already be on the PATH.

    Returns:
        Path to the mvn command

    Raises:
        RuntimeError: If Maven cannot be found or fetched
    """
    # First try to find mvn on the system PATH
    mvn_path = shutil.which("mvn")
    if mvn_path:
        _log.debug(f"Found Maven on PATH: {mvn_path}")
        return Path(mvn_path)

    if offline:
        raise RuntimeError("Maven (mvn) is not on the PATH, and offline mode is on")

    # Maven not found, fetch it from the remote server
    return fetch_maven()


def fetch_maven(url: str = "", sha: str = "") -> Path:
    """
    Fetch Maven and add it to the PATH.

    Args:
        url: URL to download Maven from (optional, uses default if not provided)
        sha: SHA hash to verify download (optional)

    Returns:
        Path to the mvn command

    Raises:
        RuntimeError: If Maven download or setup fails
    """

    # Use default Maven URL if not provided
    # Maven 3.9.9 is a stable LTS version
    if not url:
        url = "https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz"
        sha = "a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b"

    # Fix URLs to have proper prefix for cjdk
    if url.startswith("http"):
        if url.endswith(".tar.gz"):
            url = url.replace("http", "tgz+http")
        elif url.endswith(".zip"):
            url = url.replace("http", "zip+http")

    # Determine SHA type based on length (cjdk requires specifying sha type)
    # Assuming hex-encoded SHA, length should be 40, 64, or 128
    kwargs = {}
    if sha_len := len(sha):  # empty sha is fine... we just don't pass it
        sha_lengths = {40: "sha1", 64: "sha256", 128: "sha512"}
        if sha_len not in sha_lengths:
            raise ValueError(
                "SHA must be a valid sha1, sha256, or sha512 hash. "
                f"Got invalid SHA length: {sha_len}."
            )
        kwargs = {sha_lengths[sha_len]: sha}

    _log.info("Fetching Maven from remote server...")
    maven_dir = cjdk.cache_package("Maven", url, **kwargs)  # type: ignore[arg-type]
    _log.debug(f"maven_dir -> {maven_dir}")

    # Find the mvn executable in the cached directory
    # Look for apache-maven-*/**/mvn pattern
    if maven_bin := next(maven_dir.rglob("apache-maven-*/bin/mvn"), None):
        _add_to_path(maven_bin.parent, front=True)
        _log.info(f"Maven downloaded and cached at: {maven_bin}")
        return maven_bin
    else:
        raise RuntimeError(
            "Failed to find Maven executable in downloaded package. "
            f"Maven was cached to {maven_dir} but mvn binary not found."
        )


def _add_to_path(path: Path | str, front: bool = False) -> None:
    """
    Add a path to the PATH environment variable.

    If front is True, the path is added to the front of the PATH.
    By default, the path is added to the end of the PATH.
    If the path is already in the PATH, it is not added again.
    """
    current_path = os.environ.get("PATH", "")
    if (path := str(path)) in current_path:
        return
    new_path = [path, current_path] if front else [current_path, path]
    os.environ["PATH"] = os.pathsep.join(new_path)
