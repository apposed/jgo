"""Tests for Java utility functions."""

import pytest

from jgo.util.java import (
    JavaVersion,
    parse_java_version,
    parse_jdk_activation_range,
    version_matches_jdk_range,
)

# ============================================================
# SECTION 4: JAVA VERSION TESTS
# ============================================================


class TestJavaVersion:
    """Test JavaVersion NamedTuple."""

    def test_creation(self):
        v = JavaVersion(11, 0, 1)
        assert v.major == 11
        assert v.minor == 0
        assert v.patch == 1

    def test_default_values(self):
        v = JavaVersion(17)
        assert v.minor == 0
        assert v.patch == 0

    def test_string_representation(self):
        assert str(JavaVersion(8, 0, 0)) == "8.0.0"
        assert str(JavaVersion(11, 0, 1)) == "11.0.1"
        assert str(JavaVersion(17, 0, 292)) == "17.0.292"

    def test_comparison(self):
        assert JavaVersion(8, 0, 0) < JavaVersion(11, 0, 0)
        assert JavaVersion(11, 0, 0) < JavaVersion(11, 0, 1)
        assert JavaVersion(11, 0, 1) == JavaVersion(11, 0, 1)
        assert JavaVersion(17, 0, 0) > JavaVersion(11, 0, 1)


class TestParseJavaVersion:
    """Test parse_java_version function."""

    def test_old_format_simple(self):
        assert parse_java_version("1.8") == JavaVersion(8, 0, 0)
        assert parse_java_version("1.7") == JavaVersion(7, 0, 0)
        assert parse_java_version("1.6") == JavaVersion(6, 0, 0)

    def test_old_format_with_minor(self):
        assert parse_java_version("1.8.0") == JavaVersion(8, 0, 0)
        assert parse_java_version("1.7.0") == JavaVersion(7, 0, 0)

    def test_old_format_with_patch(self):
        assert parse_java_version("1.8.0_292") == JavaVersion(8, 0, 292)
        assert parse_java_version("1.8.0_191") == JavaVersion(8, 0, 191)
        assert parse_java_version("1.7.0_80") == JavaVersion(7, 0, 80)

    def test_new_format_simple(self):
        assert parse_java_version("8") == JavaVersion(8, 0, 0)
        assert parse_java_version("11") == JavaVersion(11, 0, 0)
        assert parse_java_version("17") == JavaVersion(17, 0, 0)
        assert parse_java_version("21") == JavaVersion(21, 0, 0)

    def test_new_format_with_minor(self):
        assert parse_java_version("11.0") == JavaVersion(11, 0, 0)
        assert parse_java_version("17.0") == JavaVersion(17, 0, 0)

    def test_new_format_with_patch(self):
        assert parse_java_version("11.0.1") == JavaVersion(11, 0, 1)
        assert parse_java_version("17.0.2") == JavaVersion(17, 0, 2)
        assert parse_java_version("21.0.1") == JavaVersion(21, 0, 1)

    def test_new_format_with_pre_build_opt(self):
        assert parse_java_version("11.0.2+9") == JavaVersion(11, 0, 2)
        assert parse_java_version("11.0.9.1-internal") == JavaVersion(11, 0, 9)
        assert parse_java_version(
            "11.0.31+11-post-1ubuntu1-24.04.2-Ubuntu") == JavaVersion(11, 0, 31)
        assert parse_java_version("17.0.18-internal") == JavaVersion(17, 0, 18)
        assert parse_java_version("21+32-ea-beta") == JavaVersion(21, 0, 0)

    def test_whitespace_handling(self):
        assert parse_java_version("  11  ") == JavaVersion(11, 0, 0)
        assert parse_java_version("\t1.8\n") == JavaVersion(8, 0, 0)

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Empty version string"):
            parse_java_version("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="Empty version string"):
            parse_java_version("   ")

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            parse_java_version("abc")

    def test_invalid_old_format(self):
        with pytest.raises(ValueError):
            parse_java_version("1.")

    def test_invalid_numbers(self):
        with pytest.raises(ValueError):
            parse_java_version("1.x.0")


class TestParseJdkActivationRange:
    """Test parse_jdk_activation_range function."""

    def test_simple_version(self):
        # Simple version without patch is prefix match
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("8")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(9, 0, 0)
        assert l_inc is True
        assert u_inc is False

    def test_simple_version_old_format(self):
        # Simple version without patch is prefix match
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("1.8")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(9, 0, 0)
        assert l_inc is True
        assert u_inc is False

    def test_inclusive_range(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("[1.8,11]")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(11, 0, 0)
        assert l_inc is True
        assert u_inc is True

    def test_exclusive_range(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("(1.8,11)")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(11, 0, 0)
        assert l_inc is False
        assert u_inc is False

    def test_mixed_range_lower_inclusive(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("[1.8,11)")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(11, 0, 0)
        assert l_inc is True
        assert u_inc is False

    def test_mixed_range_upper_inclusive(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("(1.8,11]")
        assert lower == JavaVersion(8, 0, 0)
        assert upper == JavaVersion(11, 0, 0)
        assert l_inc is False
        assert u_inc is True

    def test_unbounded_lower(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("(,11]")
        assert lower is None
        assert upper == JavaVersion(11, 0, 0)
        assert l_inc is False
        assert u_inc is True

    def test_unbounded_upper(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("[11,)")
        assert lower == JavaVersion(11, 0, 0)
        assert upper is None
        assert l_inc is True
        assert u_inc is False

    def test_unbounded_both(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("(,)")
        assert lower is None
        assert upper is None
        assert l_inc is False
        assert u_inc is False

    def test_semantic_versions_in_range(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range("[1.8.0_191,1.8.0_292]")
        assert lower == JavaVersion(8, 0, 191)
        assert upper == JavaVersion(8, 0, 292)
        assert l_inc is True
        assert u_inc is True

    def test_whitespace_handling(self):
        lower, upper, l_inc, u_inc = parse_jdk_activation_range(" [ 11 , 17 ] ")
        assert lower == JavaVersion(11, 0, 0)
        assert upper == JavaVersion(17, 0, 0)
        assert l_inc is True
        assert u_inc is True

    def test_empty_string(self):
        with pytest.raises(ValueError, match="Empty range specification"):
            parse_jdk_activation_range("")

    def test_invalid_lower_greater_than_upper(self):
        with pytest.raises(ValueError, match="Lower bound.*> upper bound"):
            parse_jdk_activation_range("[17,11]")

    def test_missing_comma(self):
        with pytest.raises(ValueError, match="must contain comma"):
            parse_jdk_activation_range("[11]")

    def test_invalid_opening_bracket(self):
        with pytest.raises(ValueError):
            parse_jdk_activation_range("!11,17]")

    def test_invalid_closing_bracket(self):
        with pytest.raises(ValueError, match="Invalid closing bracket"):
            parse_jdk_activation_range("[11,17!")

    def test_too_short(self):
        with pytest.raises(ValueError, match="Invalid range syntax"):
            parse_jdk_activation_range("[,")


class TestVersionMatchesJdkRange:
    """Test version_matches_jdk_range function."""

    def test_inclusive_bounds_inside(self):
        assert version_matches_jdk_range(
            JavaVersion(9, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            True,
        )

    def test_inclusive_bounds_at_lower(self):
        assert version_matches_jdk_range(
            JavaVersion(8, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            True,
        )

    def test_inclusive_bounds_at_upper(self):
        assert version_matches_jdk_range(
            JavaVersion(11, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            True,
        )

    def test_inclusive_bounds_below(self):
        assert not version_matches_jdk_range(
            JavaVersion(7, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            True,
        )

    def test_inclusive_bounds_above(self):
        assert not version_matches_jdk_range(
            JavaVersion(12, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            True,
        )

    def test_exclusive_bounds_inside(self):
        assert version_matches_jdk_range(
            JavaVersion(9, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            False,
            False,
        )

    def test_exclusive_bounds_at_lower(self):
        assert not version_matches_jdk_range(
            JavaVersion(8, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            False,
            False,
        )

    def test_exclusive_bounds_at_upper(self):
        assert not version_matches_jdk_range(
            JavaVersion(11, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            False,
            False,
        )

    def test_mixed_bounds_lower_inclusive(self):
        assert version_matches_jdk_range(
            JavaVersion(8, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            False,
        )
        assert not version_matches_jdk_range(
            JavaVersion(11, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            True,
            False,
        )

    def test_mixed_bounds_upper_inclusive(self):
        assert not version_matches_jdk_range(
            JavaVersion(8, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            False,
            True,
        )
        assert version_matches_jdk_range(
            JavaVersion(11, 0, 0),
            JavaVersion(8, 0, 0),
            JavaVersion(11, 0, 0),
            False,
            True,
        )

    def test_unbounded_lower(self):
        assert version_matches_jdk_range(
            JavaVersion(5, 0, 0), None, JavaVersion(11, 0, 0), False, True
        )
        assert version_matches_jdk_range(
            JavaVersion(11, 0, 0), None, JavaVersion(11, 0, 0), False, True
        )
        assert not version_matches_jdk_range(
            JavaVersion(12, 0, 0), None, JavaVersion(11, 0, 0), False, True
        )

    def test_unbounded_upper(self):
        assert version_matches_jdk_range(
            JavaVersion(11, 0, 0), JavaVersion(11, 0, 0), None, True, False
        )
        assert version_matches_jdk_range(
            JavaVersion(21, 0, 0), JavaVersion(11, 0, 0), None, True, False
        )
        assert not version_matches_jdk_range(
            JavaVersion(10, 0, 0), JavaVersion(11, 0, 0), None, True, False
        )

    def test_unbounded_both(self):
        assert version_matches_jdk_range(JavaVersion(1, 0, 0), None, None, False, False)
        assert version_matches_jdk_range(
            JavaVersion(99, 0, 0), None, None, False, False
        )

    def test_semantic_version_patch_differences(self):
        # 1.8.0_292 should be greater than 1.8.0_191
        assert version_matches_jdk_range(
            JavaVersion(8, 0, 250),
            JavaVersion(8, 0, 191),
            JavaVersion(8, 0, 292),
            True,
            True,
        )
        assert not version_matches_jdk_range(
            JavaVersion(8, 0, 100),
            JavaVersion(8, 0, 191),
            JavaVersion(8, 0, 292),
            True,
            True,
        )
        assert not version_matches_jdk_range(
            JavaVersion(8, 0, 300),
            JavaVersion(8, 0, 191),
            JavaVersion(8, 0, 292),
            True,
            True,
        )

    def test_exact_match_with_patch(self):
        # Version specs with patch are exact matches
        assert version_matches_jdk_range(
            JavaVersion(8, 0, 292),
            JavaVersion(8, 0, 292),
            JavaVersion(8, 0, 292),
            True,
            True,
        )
        assert not version_matches_jdk_range(
            JavaVersion(8, 0, 291),
            JavaVersion(8, 0, 292),
            JavaVersion(8, 0, 292),
            True,
            True,
        )
