Tests jgo help command.

Test main help output.

  $ jgo help
                                                                                  
   Usage: jgo [OPTIONS] [COMMAND] [ARGS]...                                       
                                                                                  
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

Test help for specific commands.

  $ jgo help run
                                                                                  
   Usage: jgo run [OPTIONS] [ENDPOINT] [REMAINING]...                             
                                                                                  
   Run a Java application from Maven coordinates or jgo.toml.                     
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT   TEXT  Maven coordinates (single or combined with +) optionally    │
  │                  followed by @MainClass                                      │
  │ REMAINING  TEXT  JVM arguments and program arguments, separated by --.       │
  │                  Example: -- -Xmx2G -- script.py                             │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --main-class     CLASS  Main class to run (supports auto-completion for      │
  │                         simple names)                                        │
  │ --entrypoint     NAME   Run specific entrypoint from jgo.toml                │
  │ --add-classpath  PATH   Append to classpath (JARs, directories, etc.)        │
  │ --global                Ignore jgo.toml and use global configuration only    │
  │                         (endpoint mode).                                     │
  │ --local                 Force jgo.toml project mode even when an             │
  │                         endpoint-like argument is present.                   │
  │ --help                  Show this message and exit.                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
   TIP: Use jgo --dry-run run to see the command without executing it.            
                                                                                  

  $ jgo help version
                                                                                  
   Usage: jgo version [OPTIONS]                                                   
                                                                                  
   Display jgo's version.                                                         
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯



  $ jgo help add
                                                                                  
   Usage: jgo add [OPTIONS] [COORDINATES]...                                      
                                                                                  
   Add dependencies to jgo.toml.                                                  
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ COORDINATES  TEXT  One or more Maven coordinates in format                   │
  │                    groupId:artifactId:[version:[classifier]                  │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --requirements  -r  FILE  Read coordinates from a requirements file (one per │
  │                           line, # for comments)                              │
  │ --no-sync                 Don't automatically sync after adding dependencies │
  │ --help                    Show this message and exit.                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help remove
                                                                                  
   Usage: jgo remove [OPTIONS] COORDINATES...                                     
                                                                                  
   Remove dependencies from jgo.toml.                                             
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ *  COORDINATES  TEXT  One or more Maven coordinates in format                │
  │                       groupId:artifactId (version optional) [required]       │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --no-sync  Don't automatically sync after removing dependencies              │
  │ --help     Show this message and exit.                                       │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help init
                                                                                  
   Usage: jgo init [OPTIONS] [ENDPOINT]                                           
                                                                                  
   Create a new jgo.toml environment file.                                        
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT  TEXT  Maven coordinates (single or combined with +) optionally     │
  │                 followed by @MainClass                                       │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --requirements  -r  FILE  Add coordinates from a requirements file (one per  │
  │                           line, # for comments)                              │
  │ --help                    Show this message and exit.                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help list
                                                                                  
   Usage: jgo list [OPTIONS] [ENDPOINT]                                           
                                                                                  
   List resolved dependencies (flat list).                                        
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT  TEXT  Maven coordinates (single or combined with +) optionally     │
  │                 followed by @MainClass, or a path to a local pom.xml         │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --direct  Show only direct dependencies (non-transitive)                     │
  │ --help    Show this message and exit.                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help tree
                                                                                  
   Usage: jgo tree [OPTIONS] [ENDPOINT]                                           
                                                                                  
   Show dependency tree.                                                          
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT  TEXT  Maven coordinates (single or combined with +) optionally     │
  │                 followed by @MainClass, or a path to a local pom.xml         │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help sync
                                                                                  
   Usage: jgo sync [OPTIONS]                                                      
                                                                                  
   Resolve dependencies and build environment.                                    
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --force  Force rebuild even if cached                                        │
  │ --help   Show this message and exit.                                         │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help lock
                                                                                  
   Usage: jgo lock [OPTIONS]                                                      
                                                                                  
   Update jgo.lock.toml without building environment.                             
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --check  Check if lock file is up to date                                    │
  │ --help   Show this message and exit.                                         │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help update
                                                                                  
   Usage: jgo update [OPTIONS]                                                    
                                                                                  
   Update dependencies to latest versions.                                        
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --force  Force rebuild even if cached                                        │
  │ --help   Show this message and exit.                                         │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help search
                                                                                  
   Usage: jgo search [OPTIONS] QUERY...                                           
                                                                                  
   Search for artifacts in Maven repositories. Supports plain text, coordinates   
   (g:a:v), or field syntax (g: a:).                                              
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ *  QUERY  TEXT  Search terms. Supports plain text, coordinates (g:a:v), or   │
  │                 field syntax (g: a:) [required]                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --limit       N     Limit number of results (default: 20)                    │
  │ --repository  NAME  Search specific repository (default: central)            │
  │ --detailed          Show detailed metadata for each result                   │
  │ --help              Show this message and exit.                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
   TIP: Try g:groupId a:artifactId for field syntax,                              
   groupId:artifactId:[version:[classifier] for coordinates, or plain text. Use * 
   for wildcards.                                                                 
                                                                                  






  $ jgo help config
                                                                                  
   Usage: jgo config [OPTIONS] [COMMAND] [ARGS]...                                
                                                                                  
   Manage jgo configuration.                                                      
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Commands ───────────────────────────────────────────────────────────────────╮
  │ get              Get a configuration value.                                  │
  │ list             List all configuration values.                              │
  │ set              Set a configuration value.                                  │
  │ shortcut         Manage global endpoint shortcuts.                           │
  │ unset            Remove a configuration value.                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help info
                                                                                  
   Usage: jgo info [OPTIONS] [COMMAND] [ARGS]...                                  
                                                                                  
   Show information about environment or artifact.                                
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Commands ───────────────────────────────────────────────────────────────────╮
  │ classpath        Show classpath.                                             │
  │ coords           Show Maven coordinates a JAR was built from.                │
  │ deplist          Show flat list of dependencies.                             │
  │ deptree          Show dependency tree.                                       │
  │ entrypoints      Show entrypoints from jgo.toml.                             │
  │ envdir           Show environment directory path.                            │
  │ jars             Show all JAR paths (classpath + module-path).               │
  │ javainfo         Show Java version requirements.                             │
  │ mains            Show classes with public main methods.                      │
  │ manifest         Show JAR manifest.                                          │
  │ modulepath       Show module-path.                                           │
  │ path             Show local file path of an artifact.                        │
  │ pom              Show POM content.                                           │
  │ versions         List available versions of an artifact.                     │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
   TIP: To see the launch command, use: jgo --dry-run run <endpoint>              
                                                                                  



Test nested help for config subcommands.

  $ jgo help config shortcut
                                                                                  
   Usage: jgo config shortcut [OPTIONS] [NAME] [ENDPOINT]                         
                                                                                  
   Manage global endpoint shortcuts.                                              
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ NAME      TEXT  Shortcut name (e.g., imagej)                                 │
  │ ENDPOINT  TEXT  Maven coordinates to associate with the shortcut             │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --remove  -r  NAME  Remove a shortcut                                        │
  │ --list    -l        List all shortcuts                                       │
  │ --help              Show this message and exit.                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯



  $ jgo help config get
                                                                                  
   Usage: jgo config get [OPTIONS] KEY                                            
                                                                                  
   Get a configuration value.                                                     
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ *  KEY  TEXT  Configuration key in dot notation (e.g., repositories.scijava) │
  │               [required]                                                     │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --global  Use global configuration (~/.config/jgo.conf)                      │
  │ --local   Use local configuration (jgo.toml)                                 │
  │ --help    Show this message and exit.                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help config set
                                                                                  
   Usage: jgo config set [OPTIONS] KEY VALUE                                      
                                                                                  
   Set a configuration value.                                                     
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ *  KEY    TEXT  Configuration key in dot notation (e.g.,                     │
  │                 repositories.scijava) [required]                             │
  │ *  VALUE  TEXT  Configuration value to set [required]                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --global  Use global configuration (~/.config/jgo.conf)                      │
  │ --local   Use local configuration (jgo.toml)                                 │
  │ --help    Show this message and exit.                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help config list
                                                                                  
   Usage: jgo config list [OPTIONS]                                               
                                                                                  
   List all configuration values.                                                 
                                                                                  
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --global  Use global configuration (~/.config/jgo.conf).                     │
  │ --local   Use local configuration (jgo.toml).                                │
  │ --help    Show this message and exit.                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

Test nested help for info subcommands.

  $ jgo help info classpath
                                                                                  
   Usage: jgo info classpath [OPTIONS] [ENDPOINT]                                 
                                                                                  
   Show classpath.                                                                
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT  TEXT  Maven coordinates (single or combined with +) optionally     │
  │                 followed by @MainClass                                       │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help info deptree
                                                                                  
   Usage: jgo info deptree [OPTIONS] [ENDPOINT]                                   
                                                                                  
   Show dependency tree.                                                          
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ ENDPOINT  TEXT                                                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help info javainfo
                                                                                  
   Usage: jgo info javainfo [OPTIONS] [INPUTS]...                                 
                                                                                  
   Show Java version requirements.                                                
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ INPUTS  TEXT                                                                 │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --direct  Analyze the named artifacts plus their direct dependencies only.   │
  │ --self    Analyze only the named artifacts themselves, with no dependencies. │
  │ --help    Show this message and exit.                                        │
  ╰──────────────────────────────────────────────────────────────────────────────╯

  $ jgo help info versions
                                                                                  
   Usage: jgo info versions [OPTIONS] COORDINATE                                  
                                                                                  
   List available versions of an artifact.                                        
                                                                                  
  ╭─ Arguments ──────────────────────────────────────────────────────────────────╮
  │ *  COORDINATE  TEXT  [required]                                              │
  ╰──────────────────────────────────────────────────────────────────────────────╯
  ╭─ Options ────────────────────────────────────────────────────────────────────╮
  │ --help  Show this message and exit.                                          │
  ╰──────────────────────────────────────────────────────────────────────────────╯

Test no-argument help (should show main help).

  $ jgo
                                                                                  
   Usage: jgo [OPTIONS] [COMMAND] [ARGS]...                                       
                                                                                  
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

Test --help flag on main command.

  $ jgo --help
                                                                                  
   Usage: jgo [OPTIONS] [COMMAND] [ARGS]...                                       
                                                                                  
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
