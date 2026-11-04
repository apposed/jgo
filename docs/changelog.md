# Changelog

## 3.3.2

### Bug fixes

- **Match Maven semantics for profile activation** -- POM profiles are now activated as Maven's `DefaultProfileSelector` does: OS name, arch and version compare case-insensitively; all of a profile's activators must match, rather than any one; negated property names (`!name`) and values (`!value`) are supported; OS families follow the rules of plexus-utils `Os.isFamily`; and `activeByDefault` profiles apply only when no other profile of the same POM is active. Previously, e.g. the OpenJFX parent POM's `<os><name>linux</name></os>` profiles never matched, so `org.openjfx:javafx-base:${javafx.platform}` and similar dependencies were left uninterpolated and failed to resolve. Also, user properties (`-D`) now take precedence over model properties during interpolation, as in Maven.

## 3.3.1

### Bug fixes

- **Interpolate properties that use legacy aliases** -- A POM property whose value used a Maven 2-era alias such as `${version}` (supported since 3.3.0) failed with `dictionary changed size during iteration`, because the alias's value was cached under a new property name while the properties were being interpolated. Under lenient resolution, the POM and its whole subtree were then silently dropped from transitive dependencies; e.g. `org.hamcrest:hamcrest-core:1.1` and several JBoss and Grizzly artifacts were affected.

## 3.3.0

### New features

- **Query a component's packaging** -- The new `Component.packaging` property reports the `<packaging>` declared in the component's POM (e.g. `jar`, `pom`, `bundle`, `maven-plugin`), defaulting to `jar` as Maven does.
- **`javainfo` analyzes a project's own classes** -- Given a project's `pom.xml` (or its directory), `jgo info javainfo` now analyzes the project's build output alongside its dependencies: `target/classes` if compiled, else the packaged `target/<artifactId>-<version>.jar`, honoring any `<build>` settings inherited from parent POMs. If the project has not been built, it warns rather than silently analyzing only the dependencies; it does not fall back to the local repository, whose copy may be a different build. Any other POM file (e.g. `foo-1.0.pom`, now also recognized by `.pom` suffix) is treated as published, and its artifact is resolved from the repository instead.

- **Remember missing artifacts** -- A remote 404 for an artifact is now recorded beside where the artifact would be cached, and the request is not repeated while the record is fresh: `MavenContext(miss_ttl=...)` seconds, a day by default. On Maven Central, whose releases are immutable, a miss is remembered for good once the artifact's version is known to exist (its POM is cached), so e.g. a missing `-javadoc` JAR is never requested again. SNAPSHOT misses are not recorded, but are requested only once per `MavenContext`. `MavenContext(update=True)`, set by the CLI's `-u`/`--update`, disregards recorded misses.
- **Pace and count requests** -- `MavenContext(min_interval=...)` spaces requests to each of its remote repositories' hosts at least that many seconds apart, across all threads, bounding the load of heavily parallel resolution. `jgo.util.http.request_counts()` reports the number of requests made per host.
- **Identify jgo in requests** -- Requests now send a `User-Agent` naming jgo and its version, rather than the generic one of `requests`. An application using jgo can prepend its own name via `jgo.util.http.set_user_agent()`.
- **Fail fast when a repository refuses access** -- With `MavenContext(fail_on_denied=True)`, an HTTP 401 or 403 raises the new `RepositoryAccessDenied`, also from lenient model building, so a block by a repository stops resolution instead of reading as many missing artifacts. By default, jgo warns once per host, quoting the server's explanation.
- **Resolve legacy project property aliases** -- Maven 2-era POMs refer to the project's coordinates as `${pom.version}`, `${pom.groupId}`, or unprefixed `${version}`, `${groupId}`, `${artifactId}`, `${parent.version}` and so on. Like Maven 3, jgo now resolves these when no property of that name exists, rather than dropping dependencies declared with them.

### Bug fixes

- **Stop caching denials and server errors as missing metadata** -- Any non-200 response to a `maven-metadata.xml` request was recorded as a 404, so a temporary refusal or server error hid the project's metadata for as long as the record was considered fresh. Only a real 404 is recorded now.
- **Report rate limiting** -- Retries after an HTTP 429 are now logged as warnings rather than debug messages.
- **`javainfo --self` on a POM analyzed the POM file** -- `jgo info javainfo --self <pom>` resolved the project's `.pom` file rather than its JAR, so it always reported no analyzable classes.

- **Resolve non-JAR packaging types correctly** -- Packaging types whose file extension differs from the type name now resolve to the right file, following Maven's standard artifact handlers. For example, `g:a:test-jar:v` now resolves `a-v-tests.jar` rather than looking for a nonexistent `a-v.test-jar`, and `maven-plugin`, `bundle`, `ejb`, `ejb-client`, `java-source`, and `javadoc` types work too. This applies to both resolvers, SNAPSHOT lookups, and lock file checksum verification.
- **Normalize timestamps to UTC** -- `Artifact.last_modified()` now returns a UTC-aware datetime, matching `Metadata.lastUpdated`, which became UTC-aware in 3.2.0. Previously, comparing the two raised `can't subtract offset-naive and offset-aware datetimes`. Timestamps from Nexus with a non-UTC offset are now converted to UTC rather than having their offset dropped.
- **Interpolate `${project.parent.*}` properties** -- POM expressions referring to the parent's coordinates (`${project.parent.groupId}`, `${project.parent.artifactId}`, `${project.parent.version}`) were left uninterpolated, so dependencies declared with them failed to resolve. For example, `org.openmicroscopy:omero-gateway:5.11.0` failed because `sketches-core` 0.9.0 declares its `memory` dependency with version `${project.parent.version}`.

### Deprecations

- **`Artifact.packaging` is now `Artifact.type`** -- The artifact's packaging type is now `Artifact.type`, matching `Dependency.type`, and `Component.artifact()` and `Artifact()` take a `type` argument. The new `Artifact.extension` and `Artifact.effective_classifier` properties give the file extension and classifier implied by the type. The old `packaging` attribute and keyword argument, and `DEFAULT_PACKAGING`, still work, but `packaging` now emits a `DeprecationWarning`. Likewise, `get_timestamped_version()` takes `extension` rather than `packaging`. The `packaging` field of `Coordinate` and of lock files is unchanged.

## 3.2.0

### New features

- **Local POM file support** -- `jgo list` and `jgo tree` now support local POM file paths.
- **Identify local JAR files** -- The new `jgo info coords` subcommand reports the Maven coordinate(s) a JAR appears to have been built from, reading the metadata embedded under `META-INF/maven`, falling back to manifest attributes, and -- with `--remote` -- identifying otherwise unknown JARs by SHA-1 checksum via Maven Central. Uber-JARs report the coordinates they bundle as well (`--all`). Relatedly, `jgo info manifest` and `jgo info pom` now accept the path of a local JAR file wherever they accept a Maven coordinate, with `jgo info pom` dumping the JAR's embedded POM(s).
- **Get an artifact's file** -- The new `jgo info path` subcommand resolves Maven coordinates into the local repository cache, downloading as needed, and prints each artifact's file path, one per line. Any packaging or classifier works. This makes it easy to compose with shell tools, e.g. `cp "$(jgo info path g:a:v)" .` to copy a JAR into the current directory.
- **More flexible `javainfo` subcommand** -- The `jgo info javainfo` command now accepts a list of arguments, each of which can be a Maven coordinate, a POM file or directory containing such, a JAR file, a class file, or a directory to scan recursively for such files. Each argument is analyzed and reported upon, and finally a summary is issued.

### Bug fixes

- **Make `--offline` actually work** -- The `--offline` flag was parsed but never passed along, so jgo kept downloading artifacts and metadata. Now artifacts must already be present locally, remote metadata is not refreshed, the `mvn` resolver runs with `-o`, Maven itself is never downloaded, and `jgo search` fails fast.
- **Make `deplist --direct` actually work** -- The `--direct` flag was being ignored for the `deplist` command. Now it's passed through to the interior logic to handle it properly.
- **Honor `--wrap raw` with log messages** -- Previously, commands `jgo --wrap raw info javainfo /really/long/path/to/nonexistentfile.xml` would still use Rich's smart wrapping if the ERROR output was longer than the TTY width.
- **Sort `info versions` output** -- The reported versions list is now ordered according to Maven's versioning semantics.
- **Add missing type hints** -- The CLI layer's click-related functions now have full type hints.
- **Stop treating clean exits as errors** -- The `jgo info manifest` and `jgo info pom` commands logged a spurious `ERROR 1` line alongside their real error message, because click's `Context.exit` raises an exception that their catch-all handler swallowed.
- **Stop turning coordinates into emoji** -- Text in table cells is no longer scanned for emoji codes, so e.g. `org.apache.ant:ant:1.10.15` renders as itself rather than sprouting an ant.

## 3.1.0

### New features

- **`jar_java_version(artifact)`** -- Public helper in `jgo.env` returning the minimum Java version required by a resolved artifact's JAR. Results are memoized in-process and cached on disk (keyed by SHA-256) in a dedicated cache, separate from the JPMS metadata cache, so callers that only need a Java version can reuse jgo's bytecode analysis without re-scanning JARs or affecting environment-building classification.

### Bug fixes

- **`Model` inherits profile constraints from its context's resolver** -- A `Model` constructed directly (rather than via the resolver) with no explicit `profile_constraints` now falls back to those carried by `context.resolver`. The default `PythonResolver` auto-detects the host's OS properties, so directly-built models once again activate OS-conditional profiles. Previously such models left `profile_constraints` as `None`, skipping OS-property injection entirely -- platform-specific profiles never activated and their properties (e.g. `${scijava.natives.classifier.javacpp}`) stayed uninterpolated, producing GACT key collision warnings.

---

## 3.0.0

### Breaking changes

- **CLI is now an optional extra** -- The command-line tool's dependencies (rich, click, rich-click) are no longer installed by default. Use `pip install jgo[cli]` to include them. Plain `pip install jgo` gives you the Python library only.

- **Removed deprecated jgo 1.x API** -- The following, deprecated since 2.0.0, are gone:
  - `jgo.main()`, `jgo.main_from_endpoint()`, `jgo.resolve_dependencies()` -- use `jgo.run()`, `jgo.build()`, `jgo.resolve()` instead
  - `jgo/jgo.py` compatibility shim and `jgo.util.compat` module
  - Deprecated CLI flags (`-U`/`--force-update`, `-a`/`--additional-jars`, `--additional-endpoints`, `--link-type`, `--log-level`)

### New features

- **Maven metadata TTL cache** -- `Project.update(max_age=N)` skips HTTP fetches for metadata files younger than N seconds, reducing unnecessary network traffic.

- **Rate-limit handling** -- HTTP 429 and 529 responses are retried automatically, honoring `Retry-After` headers.

- **`Artifact.last_modified()`** -- Returns the deployment timestamp from the remote repository. Handles Nexus v3 correctly by using its REST API when the standard `Last-Modified` header would give the wrong value.

- **PEP 561 compliance** -- Added `py.typed` marker so downstream type checkers recognize jgo's inline type annotations.

---

## 2.2.0

### New features

- **`JavaSource.DOWNLOAD` mode** -- Forces a fresh JDK download via cjdk, bypassing any cached or system Java. Useful for reproducible CI environments.

---

## 2.1.3

### Bug fixes

- **Maven `relativePath` handling removed** -- Resolving POMs with `<relativePath>` entries caused incorrect resolution in some cases; the field is now ignored during resolution, matching Maven's behavior for remote artifacts.

---

## 2.1.2

### Improvements

- **Auto Java mode tuning** -- Improved heuristics for selecting a system Java vs. downloading one via cjdk, with clearer logging when the decision is made.

---

## 2.1.1

### Bug fixes

- **Windows path normalization** -- Metadata URL paths were constructed with backslashes on Windows, causing HTTP 404s. Now normalized to forward slashes.

- **`RELEASE` version resolution** -- Fixed incorrect resolution of the `RELEASE` pseudo-version in some repository configurations.

### Other changes

- Require Python 3.10+.

---

## 2.1.0

### New features

- **Custom resolver injection** -- `jgo.build()` now accepts a `resolver=` argument, letting callers supply their own `Resolver` instance instead of constructing one internally.

### Bug fixes

- **Platform auto-detection** -- `None` platform values are now resolved to the current platform rather than propagated as null, fixing profile activation on some systems.

---

## 2.0.1

### Bug fixes

- **Exclusions not applied** -- Exclusions declared in `jgo.toml` were parsed but silently ignored during resolution. They are now correctly applied.

- **`jgo.toml` validation** -- Basic structure validation is now performed when loading a spec file, giving a clear error on malformed input instead of a confusing traceback.

---

## 2.0.0

jgo 2 is a major rewrite with a new architecture, new CLI, and new Python API. It tries to maintain backward compatibility with jgo 1.x -- existing scripts and code should continue to work with deprecation warnings.

### New features

- **Command-based CLI** -- Modern subcommand interface (`jgo run`, `jgo init`, `jgo add`, `jgo list`, `jgo tree`, `jgo info`, `jgo search`, `jgo config`, etc.) following conventions from tools like `uv`, `cargo`, and `npm`. The `jgo <endpoint>` shorthand syntax still works.

- **jgo.toml project files** -- Reproducible environments with lock files, similar to `package.json` + `package-lock.json`. Create with `jgo init`, manage with `jgo add`/`jgo remove`, sync with `jgo sync`.

- **Pure Python dependency resolver** -- Resolve Maven dependencies without a Maven installation. Handles transitive dependencies, property interpolation, dependency management (BOMs), exclusions, and scopes.

- **Automatic Java management** -- Zero-configuration execution: jgo detects the minimum Java version from bytecode and downloads it on demand via [cjdk](https://github.com/cachedjdk/cjdk).

- **Three-layer architecture** -- Independently useful layers for Maven resolution (`jgo.maven`), environment materialization (`jgo.env`), and Java execution (`jgo.exec`).

- **High-level Python API** -- `jgo.run()`, `jgo.build()`, `jgo.resolve()` for simple programmatic usage.

- **Artifact search** -- `jgo search` queries Maven Central (and configured repositories) for artifacts.

- **Rich terminal output** -- Color, progress bars, and formatted tables via [Rich](https://github.com/Textualize/rich).

- **JVM tuning flags** -- `--max-heap`, `--min-heap`, `--gc` for convenient JVM configuration.

- **Platform-aware profile activation** -- `--platform`, `--os-name`, `--os-arch` flags for Maven profile activation.

- **XDG config support** -- Settings file at `~/.config/jgo.conf` (XDG standard), with `~/.jgorc` still supported for backward compatibility.

### Breaking changes

- **Default cache directory** changed from `~/.jgo` to `~/.cache/jgo`. Override with `--cache-dir` or `JGO_CACHE_DIR`.
- **`-u` flag behavior** -- Now checks remote repositories (the old `-U` behavior). For the old `-u` behavior (local rebuild only), use `-u --offline`.

### Deprecated

- `jgo.main()`, `jgo.main_from_endpoint()`, `jgo.resolve_dependencies()` -- use `jgo.run()`, `jgo.build()`, `jgo.resolve()` instead.
- `-U`/`--force-update`, `-a`/`--additional-jars`, `--additional-endpoints`, `--link-type`, `--log-level` flags -- see {doc}`migration` for replacements.

Deprecated APIs were removed in jgo 3.0.
