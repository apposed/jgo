# Changelog

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
