"""
Java-related utility functions for jgo.

1. Java Location Handling
   - JavaSource - Strategy for locating Java executable.
   - JavaLocator - Locates or downloads Java executables based on requirements.

2. Java Version Handling
   - JavaVersion - NamedTuple for JVM versions
   - parse_java_version() - Handle old-style "1.8" format
   - parse_jdk_activation_range() - JDK profile activation ranges
   - version_matches_jdk_range() - Check JDK activation

"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import cjdk

_log = logging.getLogger(__name__)


# ============================================================
# SECTION 1: JAVA LOCATION HANDLING
#
# Handles finding or downloading the appropriate Java executable.
# ============================================================


class JavaSource(Enum):
    """
    Strategy for locating Java executable.
    """

    AUTO = "auto"  # Use system Java if suitable; download via cjdk only if needed
    SYSTEM = "system"  # Always use system Java (from PATH or JAVA_HOME); never download
    DOWNLOAD = "download"  # Always download/use cached Java via cjdk; no system Java


class JavaLocator:
    """
    Locates or downloads Java executables based on requirements.

    Integrates with cjdk for automatic Java version management.
    """

    def __init__(
        self,
        java_source: JavaSource = JavaSource.AUTO,
        java_version: str | int | None = None,
        java_vendor: str | None = None,
        verbose: bool = False,
    ):
        """
        Initialize Java locator.

        Args:
            java_source: Strategy for locating Java
            java_version: Desired Java version (e.g., 17, "17", "11+")
                         Supports int major versions and str cjdk constraints (e.g., "11+")
            java_vendor: Desired Java vendor (e.g., "adoptium", "zulu")
            verbose: Enable verbose output
        """
        self.java_source = java_source
        self.java_version = java_version
        # Default to "zulu" vendor for auto mode since it has the widest Java version support
        # (including Java 8 which adoptium lacks)
        self.java_vendor = java_vendor or "zulu"
        self.verbose = verbose

    def locate(self, min_version: int | None = None) -> Path:
        """
        Locate or download appropriate Java executable.

        Args:
            min_version: Minimum required Java version (from bytecode detection)

        Returns:
            Path to java executable

        Raises:
            RuntimeError: If Java cannot be located or version requirement cannot be met
        """
        # Determine effective version requirement
        required_version = self.java_version or min_version

        # Select strategy
        if self.java_source == JavaSource.AUTO:
            return self._locate_auto_java(required_version)
        elif self.java_source == JavaSource.SYSTEM:
            # For system Java, parse string constraints to a comparable JavaVersion
            system_version: JavaVersion | int | None
            if isinstance(required_version, str):
                system_version = self._extract_min_version(required_version)
            else:
                system_version = required_version
            return self._locate_system_java(system_version)
        elif self.java_source == JavaSource.DOWNLOAD:
            return self._locate_download_java(required_version)
        else:
            raise ValueError(f"Unknown JavaSource: {self.java_source}")

    def _locate_system_java(
        self, required_version: JavaVersion | int | None = None
    ) -> Path:
        """
        Locate system Java executable.

        Args:
            required_version: Minimum required Java version (JavaVersion or int major version)

        Returns:
            Path to java executable

        Raises:
            RuntimeError: If java not found or version too old
        """
        # Try to find java executable
        java_path = self._find_java_in_path()
        if java_path is None:
            raise RuntimeError(
                "Java not found. Please install Java or use auto mode for automatic Java management."
            )

        # Check version if required
        if required_version is not None:
            actual_version = self._get_java_version(java_path)
            # Normalize int to JavaVersion for comparison
            if isinstance(required_version, int):
                required_version = JavaVersion(required_version)
            if actual_version < required_version:
                raise RuntimeError(
                    f"Java {required_version} or higher required, but system Java is version {actual_version}. "
                    "Please upgrade Java or use auto mode for automatic Java management."
                )
            else:
                self._maybe_log(f"Using system Java {actual_version} at {java_path}")

        return java_path

    def _locate_auto_java(self, required_version: str | int | None = None) -> Path:
        """
        Locate Java using automatic management.

        First checks whether a suitable Java already exists on the system
        (via JAVA_HOME or PATH). "Suitable" means the version meets
        ``required_version`` when specified, or any version when it is None.
        Only if no suitable system Java is found does this method download
        and cache a JDK via cjdk.

        Args:
            required_version: Minimum required Java version (str or int).
                Supports cjdk version strings like "11", "17", "11+", "17+".
                Treated as a *minimum* for system Java comparisons (i.e. "11"
                accepts any Java >= 11 that is already installed).  When cjdk
                is invoked as a fallback, the string is passed through verbatim
                so cjdk's own semantics apply.

        Returns:
            Path to java executable

        Raises:
            RuntimeError: If no suitable Java can be found or downloaded
        """
        # Determine the minimum version needed for the system-Java check.
        min_version: JavaVersion | None = None
        if isinstance(required_version, int):
            min_version = JavaVersion(required_version)
        elif isinstance(required_version, str):
            min_version = self._extract_min_version(required_version)

        # First: try to use an existing system Java (JAVA_HOME or PATH).
        # This avoids unnecessary downloads when a suitable Java is available.
        system_java = self._find_java_in_path()
        if system_java is not None:
            try:
                actual = self._get_java_version(system_java)
                if min_version is None or actual >= min_version:
                    self._maybe_log(f"Using system Java {actual} at {system_java}")
                    return system_java
                self._maybe_log(
                    f"System Java {actual} at {system_java} does not meet "
                    f"requirement {min_version}; using cjdk instead"
                )
            except RuntimeError:
                self._maybe_log(
                    "Could not determine system Java version; using cjdk instead"
                )

        # Fallback: use cjdk to download/cache a suitable Java.
        # Convert to string for cjdk (it accepts str | None).
        if required_version is None:
            version_str = "21"
        elif isinstance(required_version, int):
            version_str = str(required_version)
        else:
            version_str = required_version

        # Note: cjdk downloads only if the JDK is not already cached, and then
        # shows its own progress bar, so log outcomes rather than intentions.
        _log.debug(f"Requesting Java {self._jdk_spec(version_str)} from cjdk")

        try:
            # cjdk accepts version strings like "11", "17", "11+", "17+", etc.
            java_home = cjdk.java_home(version=version_str, vendor=self.java_vendor)
            # On Windows, the executable is java.exe; on Unix it's java
            java_exe = "java.exe" if sys.platform == "win32" else "java"
            java_path = Path(java_home) / "bin" / java_exe

            if not java_path.exists():
                raise RuntimeError(f"Failed to obtain Java path: {java_path}")

            actual_version = self._get_java_version(java_path)
            vendor_info = f" ({self.java_vendor})" if self.java_vendor else ""
            self._maybe_log(
                f"Using Java {actual_version}{vendor_info} via cjdk at {java_path}"
            )

            return java_path

        except (RuntimeError, OSError) as e:
            raise RuntimeError(f"Failed to obtain Java automatically: {e}")

    def _locate_download_java(self, required_version: str | int | None = None) -> Path:
        """
        Locate Java by always downloading/using a cjdk-cached version.

        Bypasses any system Java installation entirely; always uses cjdk.
        This is the behaviour requested by scyjava's ``fetch="always"`` mode.

        Args:
            required_version: Desired Java version (str or int).
                Supports cjdk version strings like "11", "17", "11+", "17+".

        Returns:
            Path to java executable

        Raises:
            RuntimeError: If no suitable Java can be downloaded
        """
        if required_version is None:
            version_str = "21"
        elif isinstance(required_version, int):
            version_str = str(required_version)
        else:
            version_str = required_version

        _log.debug(
            f"Requesting Java {self._jdk_spec(version_str)} from cjdk (download mode)"
        )

        try:
            java_home = cjdk.java_home(version=version_str, vendor=self.java_vendor)
            java_exe = "java.exe" if sys.platform == "win32" else "java"
            java_path = Path(java_home) / "bin" / java_exe

            if not java_path.exists():
                raise RuntimeError(f"Failed to obtain Java path: {java_path}")

            actual_version = self._get_java_version(java_path)
            vendor_info = f" ({self.java_vendor})" if self.java_vendor else ""
            self._maybe_log(
                f"Using Java {actual_version}{vendor_info} via cjdk at {java_path}"
            )

            return java_path

        except (RuntimeError, OSError) as e:
            raise RuntimeError(f"Failed to download Java via cjdk: {e}")

    def _extract_min_version(self, version_constraint: str) -> JavaVersion | None:
        """
        Extract minimum version from a version constraint string.

        Handles cjdk-style constraints by stripping the suffix operator
        and parsing the remaining version string:
        - "11"      -> JavaVersion(11, 0, 0)
        - "11+"     -> JavaVersion(11, 0, 0)
        - "11.0.2"  -> JavaVersion(11, 0, 2)
        - "11.0.2+" -> JavaVersion(11, 0, 2)

        Note: This is used only for SYSTEM Java checking.
        For AUTO mode, the version string is passed directly to cjdk.

        Args:
            version_constraint: Version constraint string

        Returns:
            JavaVersion with full semantic version, or None if parsing fails
        """
        if not version_constraint:
            return None
        try:
            return parse_java_version(version_constraint.rstrip("+"))
        except (ValueError, AttributeError):
            _log.warning(
                f"Could not parse version constraint '{version_constraint}', "
                "system Java version check may not work correctly"
            )
            return None

    def _jdk_spec(self, version_str: str) -> str:
        return f"{self.java_vendor}:{version_str}" if self.java_vendor else version_str

    def _maybe_log(self, message) -> None:
        if self.verbose:
            _log.info(message)

    def _find_java_in_path(self) -> Path | None:
        """
        Find java executable in PATH or JAVA_HOME.

        Returns:
            Path to java executable, or None if not found
        """
        import os
        import shutil

        # Check JAVA_HOME first
        java_home = os.environ.get("JAVA_HOME")
        if java_home:
            java_path = Path(java_home) / "bin" / "java"
            if java_path.exists():
                return java_path

        # Check PATH
        java_cmd = shutil.which("java")
        if java_cmd:
            return Path(java_cmd)

        return None

    def _get_java_version(self, java_path: Path) -> JavaVersion:
        """
        Get Java version from executable.

        Args:
            java_path: Path to java executable

        Returns:
            Java major version (e.g., 17)

        Raises:
            RuntimeError: If version cannot be determined
        """
        try:
            result = subprocess.run(
                [str(java_path), "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            # Java version output goes to stderr
            version_output = result.stderr

            # Parse version string from output
            # Examples:
            #   "java version "1.8.0_292""
            #   "openjdk version "11.0.11" 2021-04-20"
            #   "openjdk version "17.0.1" 2021-10-19"
            match = re.search(r'version "([^"]+)"', version_output)
            if not match:
                raise RuntimeError(
                    f"Could not parse Java version from: {version_output}"
                )

            version_str = match.group(1)

            java_version = parse_java_version(version_str)
            return java_version

        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timeout while checking Java version at {java_path}")
        except (OSError, ValueError, RuntimeError) as e:
            raise RuntimeError(f"Failed to determine Java version: {e}")


# ============================================================
# SECTION 2: JAVA VERSION HANDLING
#
# Handling for Java/JVM version strings and JDK profile activation ranges.
# - Old-style "1.8" format maps to Java 8
# - JDK activation uses PREFIX matching for simple versions
# ============================================================


class JavaVersion(NamedTuple):
    """
    Semantic representation for Java runtime versions.

    This is specifically for JVM version detection, NOT for
    Maven artifact versions.

    Attributes:
        major: Major version (e.g., 8, 11, 17)
        minor: Minor version (default 0)
        patch: Patch version (default 0)
    """

    major: int
    minor: int = 0
    patch: int = 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __eq__(self, other) -> bool:
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __lt__(self, other) -> bool:
        if isinstance(other, int):
            other = JavaVersion(other)
        self_tuple = (self.major, self.minor, self.patch)
        other_tuple = (other.major, other.minor, other.patch)
        return self_tuple < other_tuple


def parse_java_version(version: str) -> JavaVersion:
    """
    Parse Java runtime version string.

    Handles JVM-specific formats:
    - Old: "1.8.0_292" -> JavaVersion(8, 0, 292)
    - New: "17.0.2" -> JavaVersion(17, 0, 2)

    Args:
        version: Java version string

    Returns:
        JavaVersion with major, minor, patch components

    Raises:
        ValueError: If version string is invalid or cannot be parsed
    """
    version = version.strip()
    if not version:
        raise ValueError("Empty version string")

    try:
        # Check if old format (1.x.y_z)
        if version.startswith("1."):
            parts = version.split(".")
            if len(parts) < 2:
                raise ValueError(f"Invalid old-format version: {version}")

            # Extract major version from second component
            major = int(parts[1].split("_")[0])

            # Extract patch/minor from remaining parts
            minor = 0
            patch = 0

            if len(parts) >= 3:
                # Handle third component (could have underscore for patch)
                third_parts = parts[2].split("_")
                minor = int(third_parts[0]) if third_parts[0] else 0
                patch = int(third_parts[1]) if len(third_parts) > 1 else 0
            elif "_" in parts[1]:
                # Handle 1.8_292 format
                _, patch_str = parts[1].split("_", 1)
                patch = int(patch_str)

            return JavaVersion(major, minor, patch)
        else:
            # New format (x.y.z)
            parts = version.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0

            return JavaVersion(major, minor, patch)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid version string '{version}': {e}")


def parse_jdk_activation_range(
    range_spec: str,
) -> tuple[JavaVersion | None, JavaVersion | None, bool, bool]:
    """
    Parse JDK profile activation range specification.

    This implements Maven's JDK profile activation semantics, which
    differ from general version ranges:

    - Simple versions use PREFIX MATCHING: "11" matches 11.x.x
    - Range syntax follows Maven conventions: "[1.8,11)"

    NOTE: This is NOT the same as dependency version ranges.

    Supports various range formats:
        - Simple version: "8" or "1.8" -> prefix match (e.g., 1.8 matches 1.8.x)
        - Inclusive range: "[1.8,11]" -> both bounds inclusive
        - Exclusive range: "(1.8,11)" -> both bounds exclusive
        - Mixed range: "[1.8,11)" -> lower inclusive, upper exclusive
        - Unbounded lower: "(,8]" -> no lower bound
        - Unbounded upper: "[11,)" -> no upper bound

    Args:
        range_spec: Maven-style version range string

    Returns:
        Tuple of (lower_bound, upper_bound, lower_inclusive, upper_inclusive)
        where bounds are JavaVersion or None for unbounded ranges

    Raises:
        ValueError: If range syntax is invalid or lower > upper
    """
    range_spec = range_spec.strip()
    if not range_spec:
        raise ValueError("Empty range specification")

    # Check if this is a range syntax (starts with bracket)
    if not range_spec.startswith(("[", "(")):
        # Simple version - check if patch version was specified
        # If no patch (e.g., "1.8", "11"), treat as prefix match
        # If patch specified (e.g., "1.8.0_292"), treat as exact match
        orig_spec = range_spec.strip()
        version = parse_java_version(range_spec)

        # Check if original spec had patch component
        # For old format: "1.8.0_292" has patch, "1.8" doesn't
        # For new format: "11.0.1" has patch, "11" doesn't
        has_patch = False
        if orig_spec.startswith("1."):
            # Old format: check for third dot or underscore
            parts = orig_spec.split(".")
            if len(parts) >= 3 or (len(parts) >= 2 and "_" in parts[1]):
                has_patch = True
        else:
            # New format: check for two dots
            if orig_spec.count(".") >= 2:
                has_patch = True

        if has_patch:
            # Exact match
            return (version, version, True, True)
        else:
            # Prefix match: match all versions with same major version
            # e.g., "1.8" matches [8.0.0, 9.0.0) - all Java 8 versions
            # e.g., "11" matches [11.0.0, 12.0.0) - all Java 11 versions
            lower = version
            upper = JavaVersion(version.major + 1, 0, 0)
            return (lower, upper, True, False)

    # Parse range syntax
    if len(range_spec) < 3:
        raise ValueError(f"Invalid range syntax: {range_spec}")

    # Extract opening bracket
    if range_spec[0] == "[":
        lower_inclusive = True
    elif range_spec[0] == "(":
        lower_inclusive = False
    else:
        raise ValueError(f"Invalid opening bracket: {range_spec[0]}")

    # Extract closing bracket
    if range_spec[-1] == "]":
        upper_inclusive = True
    elif range_spec[-1] == ")":
        upper_inclusive = False
    else:
        raise ValueError(f"Invalid closing bracket: {range_spec[-1]}")

    # Extract bounds (strip brackets)
    bounds_str = range_spec[1:-1]
    if "," not in bounds_str:
        raise ValueError(f"Range must contain comma: {range_spec}")

    # Split on comma
    parts = bounds_str.split(",", 1)
    lower_str = parts[0].strip()
    upper_str = parts[1].strip()

    # Parse bounds (empty string means unbounded)
    lower_bound = parse_java_version(lower_str) if lower_str else None
    upper_bound = parse_java_version(upper_str) if upper_str else None

    # Validate: if both bounds present, lower must be <= upper
    if (
        lower_bound is not None
        and upper_bound is not None
        and lower_bound > upper_bound
    ):
        raise ValueError(
            f"Lower bound {lower_bound} > upper bound {upper_bound} in {range_spec}"
        )

    return (lower_bound, upper_bound, lower_inclusive, upper_inclusive)


def version_matches_jdk_range(
    version: JavaVersion,
    lower: JavaVersion | None,
    upper: JavaVersion | None,
    lower_inclusive: bool,
    upper_inclusive: bool,
) -> bool:
    """
    Check if Java version matches JDK activation range.

    Uses lexicographic tuple comparison for semantic versioning.

    Args:
        version: The Java version to check
        lower: Lower bound or None for unbounded
        upper: Upper bound or None for unbounded
        lower_inclusive: Whether lower bound is inclusive
        upper_inclusive: Whether upper bound is inclusive

    Returns:
        True if version is in range, False otherwise
    """
    # Check lower bound
    if lower is not None:
        if lower_inclusive:
            if version < lower:
                return False
        else:
            if version <= lower:
                return False

    # Check upper bound
    if upper is not None:
        if upper_inclusive:
            if version > upper:
                return False
        else:
            if version >= upper:
                return False

    return True
