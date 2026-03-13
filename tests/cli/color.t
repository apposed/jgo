Tests jgo --color flag.

See also wrap.t for more color tests.

Test --color=never removes ANSI color codes.

  $ jgo --color=never remove
                                                                                  
   Usage: jgo remove [OPTIONS] COORDINATES...                                     
                                                                                  
   Try 'jgo remove --help' for help                                               
  ╭─ Error ──────────────────────────────────────────────────────────────────────╮
  │ Missing argument 'COORDINATES...'.                                           │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
  [2]

Test --color=always forces ANSI color codes.

  $ jgo --color=always remove
                                                                                  
   \x1b[33mUsage:\x1b[0m \x1b[1mjgo remove\x1b[0m [\x1b[1;36mOPTIONS\x1b[0m] \x1b[1;36mCOORDINATES\x1b[0m...                                      (esc)
                                                                                  
  \x1b[2m \x1b[0m\x1b[2mTry \x1b[0m\x1b[1;2;36m'jgo remove --help'\x1b[0m\x1b[2m for help\x1b[0m\x1b[2m                                              \x1b[0m\x1b[2m \x1b[0m (esc)
  \x1b[31m╭─\x1b[0m\x1b[31m Error \x1b[0m\x1b[31m─────────────────────────────────────────────────────────────────────\x1b[0m\x1b[31m─╮\x1b[0m (esc)
  \x1b[31m│\x1b[0m Missing argument 'COORDINATES...'.                                           \x1b[31m│\x1b[0m (esc)
  \x1b[31m╰──────────────────────────────────────────────────────────────────────────────╯\x1b[0m (esc)
                                                                                  
  [2]

Test --color with different commands.

  $ jgo --color=never help
                                                                                  
   Usage: jgo [OPTIONS] COMMAND [ARGS]...                                         
                                                                                  
   Environment manager and launcher for Java programs.                            
   Launch Java applications directly from Maven coordinates, build reproducible   
   environments, manage Java versions, and resolve dependencies -- without manual 
   installation.                                                                  
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --version                                          Show jgo version and      │
  │                                                    exit.                     │
  │ --ignore-config                                    Ignore ~/.config/jgo.conf │
  │                                                    file.                     │
  │ --full-coordinates                                 Include coordinate        │
  │                                                    components with default   │
  │                                                    values (jar packaging,    │
  │                                                    compile scope).           │
  │ --module-path-only                                 Force all JARs to         │
  │                                                    module-path (treat as     │
  │                                                    modular).                 │
  │ --class-path-only                                  Force all JARs to         │
  │                                                    classpath (disable module │
  │                                                    detection).               │
  │ --lenient                                          Warn instead of failing   │
  │                                                    on unresolved             │
  │                                                    dependencies. [env var:   │
  │                                                    JGO_LENIENT]              │
  │ --links                 [hard|soft|copy|auto]      How to link JARs: hard,   │
  │                                                    soft, copy, or auto       │
  │                                                    (default: from config or  │
  │                                                    auto)                     │
  │ --property          -D  KEY=VALUE                  Set property for profile  │
  │                                                    activation.               │
  │ --os-version            VERSION                    Set OS version for        │
  │                                                    profile activation (e.g., │
  │                                                    '5.1.2600').              │
  │ --os-arch               ARCH                       Set OS architecture for   │
  │                                                    profile activation (e.g., │
  │                                                    'amd64', 'aarch64'). Use  │
  │                                                    'auto' to auto-detect.    │
  │                                                    Overrides --platform.     │
  │ --os-family             FAMILY                     Set OS family for profile │
  │                                                    activation (e.g., 'unix', │
  │                                                    'windows'). Use 'auto' to │
  │                                                    auto-detect. Overrides    │
  │                                                    --platform.               │
  │ --os-name               NAME                       Set OS name for profile   │
  │                                                    activation (e.g.,         │
  │                                                    'Linux', 'Windows'). Use  │
  │                                                    'auto' to auto-detect.    │
  │                                                    Overrides --platform.     │
  │ --platform              PLATFORM                   Target platform for       │
  │                                                    profile activation. Sets  │
  │                                                    os-name, os-family, and   │
  │                                                    os-arch together. Use     │
  │                                                    'jgo --platform x' to see │
  │                                                    list of options.          │
  │ --min-heap              SIZE                       Minimum/initial heap size │
  │                                                    (e.g., 512M, 1G).         │
  │ --max-heap              SIZE                       Maximum heap size (e.g.,  │
  │                                                    4G, 512M). Overrides      │
  │                                                    auto-detection.           │
  │ --gc                    FLAG                       GC options. Use shorthand │
  │                                                    (e.g., --gc=G1, --gc=Z)   │
  │                                                    or explicit form          │
  │                                                    (--gc=-XX:+UseZGC).       │
  │                                                    Special values: 'auto'    │
  │                                                    (smart defaults), 'none'  │
  │                                                    (disable GC flags). Can   │
  │                                                    be repeated.              │
  │ --system-java                                      Use system Java instead   │
  │                                                    of downloading Java on    │
  │                                                    demand.                   │
  │ --java-vendor           VENDOR                     Prefer specific Java      │
  │                                                    vendor (e.g., 'adoptium', │
  │                                                    'zulu').                  │
  │ --java-version          VERSION                    Force specific Java       │
  │                                                    version (e.g., 17). [env  │
  │                                                    var: JAVA_VERSION]        │
  │ --include-optional                                 Include optional          │
  │                                                    dependencies of endpoint  │
  │                                                    coordinates in the        │
  │                                                    environment. [env var:    │
  │                                                    JGO_INCLUDE_OPTIONAL]     │
  │ --repository        -r  NAME:URL                   Add remote Maven          │
  │                                                    repository.               │
  │ --resolver              [auto|python|mvn]          Dependency resolver: auto │
  │                                                    (default), python, or mvn │
  │ --repo-cache            PATH                       Override Maven repo       │
  │                                                    cache. [env var: M2_REPO] │
  │ --cache-dir             PATH                       Override cache directory. │
  │                                                    [env var: JGO_CACHE_DIR]  │
  │ --timeout               SECONDS                    HTTP timeout for artifact │
  │                                                    downloads and metadata    │
  │                                                    fetches (default: 10).    │
  │                                                    [env var: JGO_TIMEOUT]    │
  │ --no-cache                                         Skip cache entirely,      │
  │                                                    always rebuild. [env var: │
  │                                                    JGO_NO_CACHE]             │
  │ --offline                                          Work offline, don't       │
  │                                                    download. [env var:       │
  │                                                    JGO_OFFLINE]              │
  │ --update            -u                             Update cached             │
  │                                                    environment. [env var:    │
  │                                                    JGO_UPDATE]               │
  │ --dry-run                                          Show what would be done   │
  │                                                    without doing it. Note:   │
  │                                                    while this mode prevents  │
  │                                                    the primary action (e.g.  │
  │                                                    running Java, creating    │
  │                                                    files), jgo may still     │
  │                                                    download dependencies and │
  │                                                    build cached environments │
  │                                                    as needed to report       │
  │                                                    accurate information.     │
  │ --file              -f  FILE                       Use specific environment  │
  │                                                    file (default: jgo.toml). │
  │ --color                 [auto|rich|styled|plain|a  Control output            │
  │                         lways|never]               formatting: auto          │
  │                                                    (default: detect TTY),    │
  │                                                    rich (force color+style), │
  │                                                    styled (bold/italic only, │
  │                                                    no color), plain (no ANSI │
  │                                                    codes). Aliases:          │
  │                                                    always=rich, never=plain. │
  │                                                    [env var: COLOR]          │
  │ --wrap                  [auto|smart|raw]           Control line wrapping:    │
  │                                                    auto (default: smart for  │
  │                                                    TTY, raw for              │
  │                                                    pipes/files), smart       │
  │                                                    (Rich's intelligent       │
  │                                                    wrapping at word          │
  │                                                    boundaries), raw (natural │
  │                                                    terminal wrapping, no     │
  │                                                    constraints).             │
  │ --quiet             -q                             Suppress all output.      │
  │ --verbose           -v  INTEGER RANGE              Verbose output (can be    │
  │                                                    repeated: -vv, -vvv).     │
  │ --help                                             Show this message and     │
  │                                                    exit.                     │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Commands ───────────────────────────────────────────────────────────────────╮
  │ add      Add dependencies to jgo.toml.                                       │
  │ config   Manage jgo configuration.                                           │
  │ help     Show help for jgo or a specific command.                            │
  │ info     Show information about environment or artifact.                     │
  │ init     Create a new jgo.toml environment file.                             │
  │ list     List resolved dependencies (flat list).                             │
  │ lock     Update jgo.lock.toml without building environment.                  │
  │ remove   Remove dependencies from jgo.toml.                                  │
  │ run      Run a Java application from Maven coordinates or jgo.toml.          │
  │ search   Search for artifacts in Maven repositories. Supports plain text,    │
  │          coordinates (g:a:v), or field syntax (g: a:).                       │
  │ sync     Resolve dependencies and build environment.                         │
  │ tree     Show dependency tree.                                               │
  │ update   Update dependencies to latest versions.                             │
  │ version  Display jgo's version.                                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo --color=always version
  jgo [a-z0-9.]* (re)

  $ jgo --color=never version
  jgo [a-z0-9.]* (re)

Test --color respects environment variable COLOR.

  $ COLOR=always jgo remove
                                                                                  
   \x1b[33mUsage:\x1b[0m \x1b[1mjgo remove\x1b[0m [\x1b[1;36mOPTIONS\x1b[0m] \x1b[1;36mCOORDINATES\x1b[0m...                                      (esc)
                                                                                  
  \x1b[2m \x1b[0m\x1b[2mTry \x1b[0m\x1b[1;2;36m'jgo remove --help'\x1b[0m\x1b[2m for help\x1b[0m\x1b[2m                                              \x1b[0m\x1b[2m \x1b[0m (esc)
  \x1b[31m╭─\x1b[0m\x1b[31m Error \x1b[0m\x1b[31m─────────────────────────────────────────────────────────────────────\x1b[0m\x1b[31m─╮\x1b[0m (esc)
  \x1b[31m│\x1b[0m Missing argument 'COORDINATES...'.                                           \x1b[31m│\x1b[0m (esc)
  \x1b[31m╰──────────────────────────────────────────────────────────────────────────────╯\x1b[0m (esc)
                                                                                  
  [2]

Test that coordinate formatting does not erroneously substitute emojis.
Coordinates with components matching emoji names should not be converted
to emoji. Without appropriate configuration, Rich interprets such patterns
as emoji codes (e.g. :bear: becomes 🐻).

Verify that "bear" appears as text, not 🐻 emoji.

  $ jgo --color=plain info versions com.github.qydq:bear | head -n1
  Available versions for com.github.qydq:bear:

  $ jgo --color=rich --ignore-config info versions com.github.qydq:bear | head -n1
  Available versions for \x1b[36mcom.github.qydq\x1b[0m\x1b[2m:\x1b[0m\x1b[1mbear\x1b[0m: (esc)
