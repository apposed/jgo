import xml.etree.ElementTree as ET
from typing import ClassVar

from jgo.maven import MavenContext, Model, ProfileConstraints, PythonResolver

_ctx = MavenContext()


class MockPOM:
    groupId = "g"
    artifactId = "a"
    version = "v"
    name = "n"
    description = "d"
    properties: ClassVar[dict] = {}
    source = "<mock>"

    def elements(self, xpath):
        return []

    def element(self, xpath):
        return None

    def value(self, xpath):
        return None


def test_profile_activation_os_match():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "name").text = "Windows XP"

    constraints = ProfileConstraints(os_name="Windows XP")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_os_mismatch():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "name").text = "Windows XP"

    constraints = ProfileConstraints(os_name="Linux")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_os_negation_match():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "name").text = "!Windows XP"

    constraints = ProfileConstraints(os_name="Linux")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_os_negation_mismatch():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "name").text = "!Windows XP"

    constraints = ProfileConstraints(os_name="Windows XP")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_os_missing_info_mismatch():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "family").text = "Windows"

    # We provide name but not family. Should mismatch.
    constraints = ProfileConstraints(os_name="Linux")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_os_missing_info_negation_match():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "family").text = "!Windows"

    # We provide name but not family. Should match !Windows because None != Windows.
    constraints = ProfileConstraints(os_name="Linux")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_property_match():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    prop = ET.SubElement(activation, "property")
    ET.SubElement(prop, "name").text = "foo"
    ET.SubElement(prop, "value").text = "bar"

    constraints = ProfileConstraints(properties={"foo": "bar"})
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_property_mismatch():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    prop = ET.SubElement(activation, "property")
    ET.SubElement(prop, "name").text = "foo"
    ET.SubElement(prop, "value").text = "bar"

    constraints = ProfileConstraints(properties={"foo": "baz"})
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_property_exists():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    prop = ET.SubElement(activation, "property")
    ET.SubElement(prop, "name").text = "foo"
    # No value means check for existence

    constraints = ProfileConstraints(properties={"foo": "anything"})
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_property_missing():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    prop = ET.SubElement(activation, "property")
    ET.SubElement(prop, "name").text = "foo"

    constraints = ProfileConstraints(properties={"bar": "baz"})
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


# JDK activation tests


def test_profile_activation_jdk_exact_match():
    profile = ET.Element("profile")
    ET.SubElement(profile, "id").text = "java8"
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "1.8"

    constraints = ProfileConstraints(jdk="1.8.0_292")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_jdk_exact_mismatch():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "11"

    constraints = ProfileConstraints(jdk="1.8")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_range_inclusive():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "[1.8,11]"

    # Test lower bound
    constraints = ProfileConstraints(jdk="1.8")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    # Test middle
    constraints = ProfileConstraints(jdk="9")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    # Test upper bound
    constraints = ProfileConstraints(jdk="11")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    # Test outside range
    constraints = ProfileConstraints(jdk="17")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_range_exclusive():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "(1.8,11)"

    constraints = ProfileConstraints(jdk="9")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    # Boundary excluded
    constraints = ProfileConstraints(jdk="1.8")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_minimum_version():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "[11,)"

    constraints = ProfileConstraints(jdk="11")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    constraints = ProfileConstraints(jdk="17")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    constraints = ProfileConstraints(jdk="8")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_negation():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "!1.8"

    constraints = ProfileConstraints(jdk="11")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    constraints = ProfileConstraints(jdk="1.8")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_negation_range():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "![1.8,11)"

    constraints = ProfileConstraints(jdk="11")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    constraints = ProfileConstraints(jdk="9")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_missing_constraints():
    """Profile should not activate if no java_version in constraints."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "11"

    constraints = ProfileConstraints()  # No java_version
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_invalid_spec():
    """Invalid JDK spec should be logged and skipped, not crash."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "invalid[range"

    constraints = ProfileConstraints(jdk="11")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    # Should not activate and should not raise exception
    assert model._is_active_profile(profile) is False


def test_profile_activation_jdk_semantic_versioning():
    """Test that patch versions are compared correctly."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    ET.SubElement(activation, "jdk").text = "[1.8.0_191,1.8.0_292]"

    # Within range
    constraints = ProfileConstraints(jdk="1.8.0_250")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is True

    # Below range
    constraints = ProfileConstraints(jdk="1.8.0_100")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False

    # Above range
    constraints = ProfileConstraints(jdk="1.8.0_300")
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)
    assert model._is_active_profile(profile) is False


# File activation tests


def test_profile_activation_file_exists():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "exists").text = "/path/to/file.txt"

    # Mock file_exists to return True
    constraints = ProfileConstraints(
        file_exists=lambda path: path == "/path/to/file.txt"
    )
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_file_exists_false():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "exists").text = "/path/to/file.txt"

    # Mock file_exists to return False
    constraints = ProfileConstraints(file_exists=lambda path: False)
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_file_missing():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "missing").text = "/path/to/missing.txt"

    # Mock file_exists to return False (file is missing)
    constraints = ProfileConstraints(file_exists=lambda path: False)
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is True


def test_profile_activation_file_missing_false():
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "missing").text = "/path/to/file.txt"

    # Mock file_exists to return True (file is NOT missing)
    constraints = ProfileConstraints(file_exists=lambda path: True)
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    assert model._is_active_profile(profile) is False


def test_profile_activation_file_interpolation():
    """Test that file paths are interpolated with properties."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "exists").text = "${user.home}/.m2/settings.xml"

    # Create mock POM with properties
    pom = MockPOM()
    pom.properties = {"user.home": "/home/testuser"}

    # Track which path was checked
    checked_path = None

    def mock_exists(path):
        nonlocal checked_path
        checked_path = path
        return True

    constraints = ProfileConstraints(
        properties={"user.home": "/home/testuser"}, file_exists=mock_exists
    )
    model = Model(pom, _ctx, profile_constraints=constraints)

    model._is_active_profile(profile)

    # Verify path was interpolated
    assert checked_path == "/home/testuser/.m2/settings.xml"


def test_profile_activation_file_basedir_interpolation():
    """Test that ${basedir} is interpolated when provided."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "exists").text = "${basedir}/pom.xml"

    # Provide basedir in constraints
    checked_path = None

    def mock_exists(path):
        nonlocal checked_path
        checked_path = path
        return True

    constraints = ProfileConstraints(
        basedir="/home/user/project", file_exists=mock_exists
    )
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    model._is_active_profile(profile)

    # Should interpolate basedir
    assert checked_path == "/home/user/project/pom.xml"


def test_profile_activation_file_basedir_default():
    """Test that ${basedir} uses default value \".\" when not explicitly set."""
    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    file_elem = ET.SubElement(activation, "file")
    ET.SubElement(file_elem, "exists").text = "${basedir}/pom.xml"

    # Use default basedir (which is now ".")
    checked_path = None

    def mock_exists(path):
        nonlocal checked_path
        checked_path = path
        return False

    constraints = ProfileConstraints(file_exists=mock_exists)
    model = Model(MockPOM(), _ctx, profile_constraints=constraints)

    model._is_active_profile(profile)

    # Should interpolate basedir to "."
    assert checked_path == "./pom.xml"


def test_model_inherits_constraints_from_context_resolver():
    """A Model built without explicit constraints picks them up from the context's
    resolver, so directly-constructed Models still activate OS-conditional profiles."""
    constraints = ProfileConstraints(os_name="Windows XP")
    ctx = MavenContext(resolver=PythonResolver(profile_constraints=constraints))

    # No profile_constraints passed: should fall back to the resolver's.
    model = Model(MockPOM(), ctx)

    assert model.profile_constraints is ctx.resolver.profile_constraints
    assert model.profile_constraints.os_name == "Windows XP"

    profile = ET.Element("profile")
    activation = ET.SubElement(profile, "activation")
    os_elem = ET.SubElement(activation, "os")
    ET.SubElement(os_elem, "name").text = "Windows XP"
    assert model._is_active_profile(profile) is True


def test_explicit_constraints_override_context_resolver():
    """Explicitly passed constraints take precedence over the context resolver's."""
    resolver_constraints = ProfileConstraints(os_name="Linux")
    ctx = MavenContext(
        resolver=PythonResolver(profile_constraints=resolver_constraints)
    )

    explicit = ProfileConstraints(os_name="Windows XP")
    model = Model(MockPOM(), ctx, profile_constraints=explicit)

    assert model.profile_constraints is explicit
    assert model.profile_constraints.os_name == "Windows XP"


# Maven activation semantics


def _profile(*conditions, profile_id="p"):
    """Build a profile element whose activation holds the given conditions."""
    profile = ET.Element("profile")
    ET.SubElement(profile, "id").text = profile_id
    activation = ET.SubElement(profile, "activation")
    for tag, children in conditions:
        cond = ET.SubElement(activation, tag)
        if isinstance(children, str):
            cond.text = children
        else:
            for child_tag, text in children.items():
                ET.SubElement(cond, child_tag).text = text
    return profile


def _model(**constraints):
    return Model(MockPOM(), _ctx, profile_constraints=ProfileConstraints(**constraints))


def test_profile_activation_os_case_insensitive():
    """Maven compares OS values case-insensitively (e.g. OpenJFX's 'linux')."""
    profile = _profile(("os", {"name": "linux", "arch": "AMD64"}))
    assert _model(os_name="Linux", os_arch="amd64")._is_active_profile(profile)


def test_profile_activation_conditions_are_anded():
    """All present activators must match, not just one (Maven 3.2.2+)."""
    profile = _profile(
        ("os", {"name": "linux"}),
        ("property", {"name": "foo", "value": "bar"}),
    )
    assert not _model(os_name="Linux")._is_active_profile(profile)
    assert _model(os_name="Linux", properties={"foo": "bar"})._is_active_profile(
        profile
    )
    assert not _model(os_name="Windows", properties={"foo": "bar"})._is_active_profile(
        profile
    )


def test_profile_activation_property_negated_value():
    """A !value matches any other value, including an absent property."""
    profile = _profile(("property", {"name": "javafx.monocle", "value": "!true"}))
    assert _model()._is_active_profile(profile)
    assert _model(properties={"javafx.monocle": "false"})._is_active_profile(profile)
    assert not _model(properties={"javafx.monocle": "true"})._is_active_profile(profile)


def test_profile_activation_property_negated_name():
    """A !name matches when the property is absent."""
    profile = _profile(("property", {"name": "!foo"}))
    assert _model()._is_active_profile(profile)
    assert not _model(properties={"foo": "x"})._is_active_profile(profile)


def test_profile_activation_os_family_rules():
    """Family matching follows plexus-utils Os.isFamily."""
    unix = _profile(("os", {"family": "unix"}))
    mac = _profile(("os", {"family": "mac"}))
    windows = _profile(("os", {"family": "Windows"}))
    assert _model(os_name="Mac OS X", os_family="mac")._is_active_profile(unix)
    assert _model(os_name="Mac OS X", os_family="mac")._is_active_profile(mac)
    assert _model(os_name="Linux", os_family="unix")._is_active_profile(unix)
    assert not _model(os_name="Linux", os_family="unix")._is_active_profile(windows)
    assert _model(os_name="Windows 11", os_family="windows")._is_active_profile(windows)
    assert not _model(os_name="Windows 11", os_family="windows")._is_active_profile(
        unix
    )


def test_active_by_default_only_without_other_active_profiles():
    """activeByDefault profiles apply only if no other profile of the POM is active."""

    class ProfilesPOM(MockPOM):
        def __init__(self, *profiles):
            self.profiles = list(profiles)

        def elements(self, xpath):
            return self.profiles if xpath == "profiles/profile" else []

    def props_profile(conditions, key):
        profile = _profile(*conditions, profile_id=key)
        ET.SubElement(ET.SubElement(profile, "properties"), key).text = "on"
        return profile

    default = props_profile([("activeByDefault", "true")], "default")
    linux = props_profile([("os", {"name": "linux"})], "linux")

    constraints = ProfileConstraints(os_name="Linux")
    pom = ProfilesPOM(default, linux)
    model = Model(pom, _ctx, profile_constraints=constraints)
    assert model.props.get("linux") == "on"
    assert "default" not in model.props

    constraints = ProfileConstraints(os_name="Windows")
    model = Model(pom, _ctx, profile_constraints=constraints)
    assert model.props.get("default") == "on"
    assert "linux" not in model.props


def test_user_properties_override_model_properties():
    """-D properties take precedence over POM properties, as in Maven."""
    pom = MockPOM()
    pom.properties = {"javafx.platform": "linux"}
    constraints = ProfileConstraints(properties={"javafx.platform": "linux-aarch64"})
    model = Model(pom, _ctx, profile_constraints=constraints)
    assert model.props["javafx.platform"] == "linux-aarch64"


def test_later_active_profile_overrides_earlier():
    """As in Maven, a later active profile's values override an earlier one's.

    E.g. on Apple Silicon, pom-scijava-base activates both its aarch64 and macos
    profiles, and the latter must win, setting scijava.platform.arch.jogamp to
    "universal" rather than "aarch64".
    """

    def profile(profile_id, arch_jogamp, version):
        p = _profile(("property", {"name": "go"}), profile_id=profile_id)
        props = ET.SubElement(p, "properties")
        ET.SubElement(props, "arch.jogamp").text = arch_jogamp
        dep_mgmt = ET.SubElement(
            ET.SubElement(p, "dependencyManagement"), "dependencies"
        )
        dep = ET.SubElement(dep_mgmt, "dependency")
        ET.SubElement(dep, "groupId").text = "org.example"
        ET.SubElement(dep, "artifactId").text = "lib"
        ET.SubElement(dep, "version").text = version
        return p

    class ProfilesPOM(MockPOM):
        def elements(self, xpath):
            if xpath == "profiles/profile":
                return [
                    profile("aarch64", "aarch64", "1.0"),
                    profile("macos", "universal", "2.0"),
                ]
            return []

    model = Model(
        ProfilesPOM(),
        _ctx,
        profile_constraints=ProfileConstraints(properties={"go": "1"}),
    )

    assert model.props["arch.jogamp"] == "universal"
    managed = [d for d in model.dep_mgmt.values() if d.artifactId == "lib"]
    assert [d.version for d in managed] == ["2.0"]
