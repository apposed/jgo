"""
Test property interpolation in Maven POMs.

This test validates that property interpolation works correctly across:
- Parent POM inheritance
- Dependency management
- Both PythonResolver (pure Python) and MvnResolver (mvn-based)

Ported from db-xml-maven/tests/test_maven.py
"""

from re import match

from jgo.maven import MavenContext, MvnResolver
from jgo.maven._model import Model


class TestPropertyInterpolation:
    """Test that ${...} property expressions are correctly interpolated."""

    def test_interpolate_syscall(self):
        """
        Test property interpolation with both PythonResolver and MvnResolver.

        Uses pom-scijava 35.1.1 as a complex real-world test case with:
        - Deep parent POM inheritance
        - Extensive dependency management
        - Property-based versioning
        """
        # Test with PythonResolver (pure Python)
        maven = MavenContext()
        component_simple = maven.project("org.scijava", "pom-scijava").at_version(
            "35.1.1"
        )
        model_simple = Model(component_simple.pom(), maven)
        self.assert_model_interpolated(model_simple)

        # Test with MvnResolver (mvn-based)
        maven_syscall = MavenContext(resolver=MvnResolver("mvn"))
        maven_syscall.resolver.mvn_flags = ["-o"] + maven_syscall.resolver.mvn_flags
        component_syscall = maven_syscall.project(
            "org.scijava", "pom-scijava"
        ).at_version("35.1.1")
        model_syscall = Model(component_syscall.pom(), maven_syscall)
        self.assert_model_interpolated(model_syscall)

        # Ensure both resolvers produce identical results
        self.assert_equal_xml(component_syscall.pom(), component_simple.pom())

    def assert_model_interpolated(self, model):
        """
        Validate that all managed dependency versions are fully interpolated.

        Good: "1.16.0"
        Bad: "${batik.version}"
        """
        assert model is not None
        # Check both deps and dep_mgmt
        all_deps = list(model.deps.values()) + list(model.dep_mgmt.values())
        assert len(all_deps) > 0, "No dependencies found in model"

        for dep in all_deps:
            # Ensure all versions are populated with actual version numbers,
            # not unresolved property references like ${foo.version}
            assert dep.version is not None, f"Dependency {dep} has no version"
            assert "${" not in dep.version, (
                f"Dependency {dep} has uninterpolated version: {dep.version}"
            )
            assert match(r"\d+($|\.\d+)", dep.version), (
                f"Dependency {dep} has invalid version format: {dep.version}"
            )

    def assert_equal_xml(self, xml1, xml2):
        """
        Compare two POM XML objects for equality.

        Ignores non-deterministic elements like timestamps.
        """
        lines1 = self.lockdown(xml1).dump().splitlines()
        lines2 = self.lockdown(xml2).dump().splitlines()
        assert len(lines1) > 100, "POM seems too small, might be invalid"
        assert lines1 == lines2, "POMs differ between PythonResolver and MvnResolver"

    def lockdown(self, xml):
        """
        Normalize non-deterministic values in XML for comparison.

        Replaces timestamp values with a constant to allow comparison.
        """
        # Ignore elements with non-deterministic values such as datestamps.
        ignored_elements = (
            "build/pluginManagement/plugins/plugin/configuration/archive/manifestEntries/Implementation-Date",
            "build/pluginManagement/plugins/plugin/executions/execution/configuration/archive/manifestEntries/Implementation-Date",
        )
        for p in ignored_elements:
            for el in xml.elements(p):
                el.text = "IGNORED"
        return xml


class TestPropertyInterpolationEdgeCases:
    """Test edge cases in property interpolation."""

    def test_project_properties(self):
        """Test that special ${project.*} properties are interpolated."""
        maven = MavenContext()
        # Use a simple POM that we know uses project properties
        pom = maven.project("org.scijava", "pom-scijava").at_version("35.1.1").pom()

        # Verify basic POM properties are accessible
        assert pom.groupId is not None
        assert pom.artifactId == "pom-scijava"
        assert pom.version == "35.1.1"

    def test_version_properties_in_dependency_management(self):
        """
        Test that version properties in <dependencyManagement> are interpolated.

        This is critical for BOMs (Bill of Materials) which use property-based
        versioning extensively.
        """
        maven = MavenContext()
        component = maven.project("org.scijava", "pom-scijava").at_version("35.1.1")
        model = Model(component.pom(), maven)

        managed_deps = list(model.dep_mgmt.values())
        assert len(managed_deps) > 0, "No managed dependencies found"

        # All managed dependency versions should be fully resolved
        for dep in managed_deps:
            if dep.version:  # Some may be None if managed by parent
                assert "${" not in dep.version, (
                    f"Uninterpolated property in {dep.groupId}:{dep.artifactId}: {dep.version}"
                )


def _write_pom(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project xmlns="http://maven.apache.org/POM/4.0.0">\n'
        "  <modelVersion>4.0.0</modelVersion>\n"
        f"{body}\n"
        "</project>\n"
    )
    return path


def test_project_parent_properties(tmp_path):
    """
    ${project.parent.*} expressions resolve to the modeled POM's parent coordinates,
    including when the expression is inherited from the parent POM itself.
    """
    from jgo.maven import POM

    repo = tmp_path / "repo"
    _write_pom(
        repo / "org" / "example" / "parent" / "7" / "parent-7.pom",
        "  <groupId>org.example</groupId>\n"
        "  <artifactId>parent</artifactId>\n"
        "  <version>7</version>\n"
        "  <packaging>pom</packaging>\n"
        "  <dependencies>\n"
        "    <dependency>\n"
        "      <groupId>${project.parent.groupId}</groupId>\n"
        "      <artifactId>inherited</artifactId>\n"
        "      <version>${project.parent.version}</version>\n"
        "    </dependency>\n"
        "  </dependencies>",
    )
    pom_path = _write_pom(
        tmp_path / "proj" / "pom.xml",
        "  <parent>\n"
        "    <groupId>org.example</groupId>\n"
        "    <artifactId>parent</artifactId>\n"
        "    <version>7</version>\n"
        "  </parent>\n"
        "  <artifactId>child</artifactId>\n"
        "  <version>1.0.0</version>\n"
        "  <dependencies>\n"
        "    <dependency>\n"
        "      <groupId>org.example</groupId>\n"
        "      <artifactId>${project.parent.artifactId}-memory</artifactId>\n"
        "      <version>${project.parent.version}</version>\n"
        "    </dependency>\n"
        "  </dependencies>",
    )
    model = Model(POM(pom_path), MavenContext(repo_cache=repo))

    deps = {(d.groupId, d.artifactId): d.version for d in model.deps.values()}
    assert deps[("org.example", "parent-memory")] == "7"
    assert deps[("org.example", "inherited")] == "7"


def test_legacy_project_aliases(tmp_path):
    """
    Maven 2-era ${pom.*} and unprefixed ${version}-style expressions resolve to the
    project's coordinates, as in Maven 3 -- but a real property of the same name wins.
    """
    from jgo.maven import POM

    pom_path = _write_pom(
        tmp_path / "proj" / "pom.xml",
        "  <groupId>org.example</groupId>\n"
        "  <artifactId>legacy</artifactId>\n"
        "  <version>2.1</version>\n"
        "  <properties><name>from-property</name></properties>\n"
        "  <dependencies>\n"
        "    <dependency>\n"
        "      <groupId>${pom.groupId}</groupId>\n"
        "      <artifactId>a</artifactId>\n"
        "      <version>${pom.version}</version>\n"
        "    </dependency>\n"
        "    <dependency>\n"
        "      <groupId>${groupId}</groupId>\n"
        "      <artifactId>b-${artifactId}</artifactId>\n"
        "      <version>${version}</version>\n"
        "    </dependency>\n"
        "    <dependency>\n"
        "      <groupId>org.example</groupId>\n"
        "      <artifactId>${name}</artifactId>\n"
        "      <version>1</version>\n"
        "    </dependency>\n"
        "  </dependencies>",
    )
    model = Model(POM(pom_path), MavenContext(repo_cache=tmp_path / "repo"))

    deps = {(d.groupId, d.artifactId): d.version for d in model.deps.values()}
    assert deps[("org.example", "a")] == "2.1"
    assert deps[("org.example", "b-legacy")] == "2.1"
    assert ("org.example", "from-property") in deps
