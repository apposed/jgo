Tests jgo info command.

Test info with no subcommand shows help.

  $ jgo info
                                                                                  
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
                                                                                  
  [2]

Test info classpath with no endpoint.

  $ jgo info classpath
  ERROR    No endpoint specified
  [1]

Test info classpath with endpoint.

  $ jgo info classpath com.google.guava:guava:33.0.0-jre
  No JARs on classpath
  TIP: Use 'jgo info modulepath' to see module-path JARs

Test info modulepath with endpoint.

  $ jgo info modulepath com.google.guava:guava:33.0.0-jre
  */modules/checker-qual-3.41.0.jar (glob)
  */modules/error_prone_annotations-2.23.0.jar (glob)
  */modules/failureaccess-1.0.2.jar (glob)
  */modules/guava-33.0.0-jre.jar (glob)
  */modules/j2objc-annotations-2.8.jar (glob)
  */modules/jsr305-3.0.2.jar (glob)
  */modules/listenablefuture-9999.0-empty-to-avoid-conflict-with-guava.jar (glob)

Test info jars with endpoint.

  $ jgo info jars com.google.guava:guava:33.0.0-jre
  No classpath JARs
  Module-path:
  */modules/checker-qual-3.41.0.jar (glob)
  */modules/error_prone_annotations-2.23.0.jar (glob)
  */modules/failureaccess-1.0.2.jar (glob)
  */modules/guava-33.0.0-jre.jar (glob)
  */modules/j2objc-annotations-2.8.jar (glob)
  */modules/jsr305-3.0.2.jar (glob)
  */modules/listenablefuture-9999.0-empty-to-avoid-conflict-with-guava.jar (glob)

Test info deptree with no endpoint.

  $ jgo info deptree
  ERROR    No endpoint specified
  [1]

Test info deptree with endpoint.

  $ jgo info deptree com.google.guava:guava:33.0.0-jre
  
  └── com.google.guava:guava:33.0.0-jre
      ├── com.google.guava:failureaccess:1.0.2
      ├── com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava
      ├── com.google.code.findbugs:jsr305:3.0.2
      ├── org.checkerframework:checker-qual:3.41.0
      ├── com.google.errorprone:error_prone_annotations:2.23.0
      └── com.google.j2objc:j2objc-annotations:2.8


Test info deptree with a local POM file.

  $ cat > "$TMPDIR/info-demo-pom.xml" <<'POM'
  > <?xml version="1.0" encoding="UTF-8"?>
  > <project xmlns="http://maven.apache.org/POM/4.0.0">
  >   <modelVersion>4.0.0</modelVersion>
  >   <parent>
  >     <groupId>org.scijava</groupId>
  >     <artifactId>pom-scijava</artifactId>
  >     <version>37.0.0</version>
  >     <relativePath/>
  >   </parent>
  >   <groupId>org.example</groupId>
  >   <artifactId>pom-demo</artifactId>
  >   <version>1.0.0</version>
  >   <dependencies>
  >     <dependency>
  >       <groupId>org.scijava</groupId>
  >       <artifactId>parsington</artifactId>
  >     </dependency>
  >   </dependencies>
  > </project>
  > POM

  $ jgo info deptree "$TMPDIR/info-demo-pom.xml"
  org.example:pom-demo:pom:1.0.0
  └── org.scijava:parsington:3.1.0

Test info deplist with a local POM file.

  $ jgo info deplist "$TMPDIR/info-demo-pom.xml"
  org.example:pom-demo:pom:1.0.0
     org.scijava:parsington:3.1.0

Test info deplist with no endpoint.

  $ jgo info deplist
  ERROR    No endpoint specified
  [1]

Test info deplist with endpoint.

  $ jgo info deplist com.google.guava:guava:33.0.0-jre
  com.google.guava:guava:33.0.0-jre
     com.google.code.findbugs:jsr305:3.0.2
     com.google.errorprone:error_prone_annotations:2.23.0
     com.google.guava:failureaccess:1.0.2
     com.google.guava:listenablefuture:9999.0-empty-to-avoid-conflict-with-guava
     com.google.j2objc:j2objc-annotations:2.8
     org.checkerframework:checker-qual:3.41.0

Test info deplist --direct flag. Use an artifact whose direct dependencies are a
strict subset of its transitive closure, so the flag's effect is observable
(guava's direct deps happen to equal its transitive set, which would not catch a
regression where --direct is ignored).

  $ jgo info deplist org.junit.jupiter:junit-jupiter:5.10.0
  org.junit.jupiter:junit-jupiter:5.10.0
     org.apiguardian:apiguardian-api:1.1.2
     org.junit.jupiter:junit-jupiter-api:5.10.0
     org.junit.jupiter:junit-jupiter-engine:5.10.0:runtime
     org.junit.jupiter:junit-jupiter-params:5.10.0
     org.junit.platform:junit-platform-commons:1.10.0
     org.junit.platform:junit-platform-engine:1.10.0:runtime
     org.opentest4j:opentest4j:1.3.0

  $ jgo info deplist --direct org.junit.jupiter:junit-jupiter:5.10.0
  org.junit.jupiter:junit-jupiter:5.10.0
     org.junit.jupiter:junit-jupiter-api:5.10.0
     org.junit.jupiter:junit-jupiter-engine:5.10.0:runtime
     org.junit.jupiter:junit-jupiter-params:5.10.0

Test info javainfo with no endpoint.

  $ jgo info javainfo
  ERROR    No endpoint specified
  [1]

Test info javainfo with endpoint.

  $ jgo info javainfo com.google.guava:guava:33.0.0-jre
  
  Environment: */.cache/jgo/envs/com/google/guava/guava/* (glob)
  Module-path JARs: 7
  Total JARs: 7
  
  ╭───────────────────────── Java Version Requirements ──────────────────────────╮
  │ Minimum Java version: 8                                                      │
  │ (already an LTS version)                                                     │
  ╰──────────────────────────────────────────────────────────────────────────────╯
   *Per-JAR Analysis * (re)
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
  ┃ JAR                                ┃ Java Version ┃ Max Bytecode ┃ Class Count ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
  │ checker-qual-3.41.0.jar            │            8 │           52 │         366 │
  │ error_prone_annotations-2.23.0.jar │            8 │           52 │          27 │
  │ guava-33.0.0-jre.jar               │            8 │           52 │        2003 │
  │ failureaccess-1.0.2.jar            │            7 │           51 │           2 │
  │ j2objc-annotations-2.8.jar         │            7 │           51 │          13 │
  │ jsr305-3.0.2.jar                   │            5 │           49 │          35 │
  └────────────────────────────────────┴──────────────┴──────────────┴─────────────┘

Test info manifest requires endpoint.

  $ jgo info manifest
                                                                                  
   Usage: jgo info manifest [OPTIONS] TARGET                                      
                                                                                  
   Try 'jgo info manifest --help' for help                                        
  ╭─ Error ──────────────────────────────────────────────────────────────────────╮
  │ Missing argument 'TARGET'.                                                   │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
  [2]

Test info manifest with endpoint.

  $ jgo info manifest com.google.guava:guava:33.0.0-jre
  Manifest-Version: 1.0
  Automatic-Module-Name: com.google.common
  Build-Jdk-Spec: 11
  Bundle-Description: Guava is a suite of core and expanded libraries that include    utility classes, Google's collections, I/O classes, and    much more.
  Bundle-DocURL: https://github.com/google/guava/
  Bundle-License: http://www.apache.org/licenses/LICENSE-2.0.txt
  Bundle-ManifestVersion: 2
  Bundle-Name: Guava: Google Core Libraries for Java
  Bundle-SymbolicName: com.google.guava
  Bundle-Version: 33.0.0.jre
  Created-By: Apache Maven Bundle Plugin 5.1.8
  Export-Package: com.google.common.annotations;version="33.0.0",com.google.common.base;version="33.0.0";uses:="javax.annotation",com.google.common.cache;version="33.0.0";uses:="com.google.common.base,com.google.common.collect,com.google.common.util.concurrent,javax.annotation",com.google.common.collect;version="33.0.0";uses:="com.google.common.base,javax.annotation",com.google.common.escape;version="33.0.0";uses:="com.google.common.base,javax.annotation",com.google.common.eventbus;version="33.0.0",com.google.common.graph;version="33.0.0";uses:="com.google.common.collect,javax.annotation",com.google.common.hash;version="33.0.0";uses:="com.google.common.base,javax.annotation",com.google.common.html;version="33.0.0";uses:="com.google.common.escape",com.google.common.io;version="33.0.0";uses:="com.google.common.base,com.google.common.collect,com.google.common.graph,com.google.common.hash,javax.annotation",com.google.common.math;version="33.0.0";uses:="javax.annotation",com.google.common.net;version="33.0.0";uses:="com.google.common.base,com.google.common.collect,com.google.common.escape,javax.annotation",com.google.common.primitives;version="33.0.0";uses:="com.google.common.base,javax.annotation",com.google.common.reflect;version="33.0.0";uses:="com.google.common.collect,com.google.common.io,javax.annotation",com.google.common.util.concurrent;version="33.0.0";uses:="com.google.common.base,com.google.common.collect,com.google.common.util.concurrent.internal,javax.annotation",com.google.common.xml;version="33.0.0";uses:="com.google.common.escape"
  Import-Package: com.google.common.util.concurrent.internal;version="[1.0,2)",javax.annotation;resolution:=optional;version="[3.0,4)",javax.crypto;resolution:=optional,javax.crypto.spec;resolution:=optional,sun.misc;resolution:=optional
  Require-Capability: osgi.ee;filter:="(&(osgi.ee=JavaSE)(version=1.8))"
  Tool: Bnd-6.3.1.202206071316

Test info manifest --raw flag.

  $ jgo info manifest --raw com.google.guava:guava:33.0.0-jre
  Manifest-Version: 1.0
  Automatic-Module-Name: com.google.common
  Build-Jdk-Spec: 11
  Bundle-Description: Guava is a suite of core and expanded libraries th
   at include    utility classes, Google's collections, I/O classes, and
       much more.
  Bundle-DocURL: https://github.com/google/guava/
  Bundle-License: http://www.apache.org/licenses/LICENSE-2.0.txt
  Bundle-ManifestVersion: 2
  Bundle-Name: Guava: Google Core Libraries for Java
  Bundle-SymbolicName: com.google.guava
  Bundle-Version: 33.0.0.jre
  Created-By: Apache Maven Bundle Plugin 5.1.8
  Export-Package: com.google.common.annotations;version="33.0.0",com.goo
   gle.common.base;version="33.0.0";uses:="javax.annotation",com.google.
   common.cache;version="33.0.0";uses:="com.google.common.base,com.googl
   e.common.collect,com.google.common.util.concurrent,javax.annotation",
   com.google.common.collect;version="33.0.0";uses:="com.google.common.b
   ase,javax.annotation",com.google.common.escape;version="33.0.0";uses:
   ="com.google.common.base,javax.annotation",com.google.common.eventbus
   ;version="33.0.0",com.google.common.graph;version="33.0.0";uses:="com
   .google.common.collect,javax.annotation",com.google.common.hash;versi
   on="33.0.0";uses:="com.google.common.base,javax.annotation",com.googl
   e.common.html;version="33.0.0";uses:="com.google.common.escape",com.g
   oogle.common.io;version="33.0.0";uses:="com.google.common.base,com.go
   ogle.common.collect,com.google.common.graph,com.google.common.hash,ja
   vax.annotation",com.google.common.math;version="33.0.0";uses:="javax.
   annotation",com.google.common.net;version="33.0.0";uses:="com.google.
   common.base,com.google.common.collect,com.google.common.escape,javax.
   annotation",com.google.common.primitives;version="33.0.0";uses:="com.
   google.common.base,javax.annotation",com.google.common.reflect;versio
   n="33.0.0";uses:="com.google.common.collect,com.google.common.io,java
   x.annotation",com.google.common.util.concurrent;version="33.0.0";uses
   :="com.google.common.base,com.google.common.collect,com.google.common
   .util.concurrent.internal,javax.annotation",com.google.common.xml;ver
   sion="33.0.0";uses:="com.google.common.escape"
  Import-Package: com.google.common.util.concurrent.internal;version="[1
   .0,2)",javax.annotation;resolution:=optional;version="[3.0,4)",javax.
   crypto;resolution:=optional,javax.crypto.spec;resolution:=optional,su
   n.misc;resolution:=optional
  Require-Capability: osgi.ee;filter:="(&(osgi.ee=JavaSE)(version=1.8))"
  Tool: Bnd-6.3.1.202206071316
  

Test info pom requires endpoint.

  $ jgo info pom
                                                                                  
   Usage: jgo info pom [OPTIONS] TARGET                                           
                                                                                  
   Try 'jgo info pom --help' for help                                             
  ╭─ Error ──────────────────────────────────────────────────────────────────────╮
  │ Missing argument 'TARGET'.                                                   │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
  [2]

Test info pom with rich color.

  $ jgo --color=rich info pom com.google.guava:guava:33.0.0-jre
  \x1b[1m<\x1b[0m\x1b[39m?xml \x1b[0m\x1b[33mversion\x1b[0m\x1b[39m=\x1b[0m\x1b[32m"1\x1b[0m\x1b[32m.0"\x1b[0m\x1b[39m ?>\x1b[0m (esc)
  \x1b[39m<project \x1b[0m\x1b[33mxmlns\x1b[0m\x1b[39m=\x1b[0m\x1b[32m"http\x1b[0m\x1b[32m://maven.apache.org/POM/4.0.0"\x1b[0m\x1b[39m \x1b[0m (esc)
  \x1b[39mxmlns:\x1b[0m\x1b[33mxsi\x1b[0m\x1b[39m=\x1b[0m\x1b[32m"http\x1b[0m\x1b[32m://www.w3.org/2001/XMLSchema-instance"\x1b[0m\x1b[39m \x1b[0m (esc)
  \x1b[39mxsi:\x1b[0m\x1b[33mschemaLocation\x1b[0m\x1b[39m=\x1b[0m\x1b[32m"http\x1b[0m\x1b[32m://maven.apache.org/POM/4.0.0 \x1b[0m (esc)
  \x1b[32mhttp://maven.apache.org/maven-v4_0_0.xsd"\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <!-- do_not_remove: published-with-gradle-metadata -->\x1b[0m (esc)
  \x1b[39m  <modelVersion>\x1b[0m\x1b[1;36m4.0\x1b[0m\x1b[39m.\x1b[0m\x1b[1;36m0\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mmodelVersion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <parent>\x1b[0m (esc)
  \x1b[39m    <groupId>com.google.guava<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <artifactId>guava-parent<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <version>\x1b[0m\x1b[1;36m33.0\x1b[0m\x1b[39m.\x1b[0m\x1b[1;36m0\x1b[0m\x1b[39m-jre<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mparent\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <artifactId>guava<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <packaging>bundle<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mpackaging\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <name>Guava: Google Core Libraries for Java<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <url>\x1b[0m\x1b[4;94mhttps://github.com/google/guava\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95murl\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <description>\x1b[0m (esc)
  \x1b[39m    Guava is a suite of core and expanded libraries that include\x1b[0m (esc)
  \x1b[39m    utility classes, Google's collections, I/O classes, and\x1b[0m (esc)
  \x1b[39m    much more.\x1b[0m (esc)
  \x1b[39m  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdescription\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <dependencies>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>com.google.guava<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>failureaccess<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <version>\x1b[0m\x1b[1;36m1.0\x1b[0m\x1b[39m.\x1b[0m\x1b[1;36m2\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>com.google.guava<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>listenablefuture<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <version>\x1b[0m\x1b[1;36m9999.0\x1b[0m\x1b[39m-empty-to-avoid-conflict-with-guava<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>com.google.code.findbugs<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>jsr305<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>org.checkerframework<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>checker-qual<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>com.google.errorprone<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>error_prone_annotations<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <dependency>\x1b[0m (esc)
  \x1b[39m      <groupId>com.google.j2objc<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <artifactId>j2objc-annotations<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: does this comment belong on the <dependency> in \x1b[0m (esc)
  \x1b[39m<profiles>? -->\x1b[0m (esc)
  \x1b[39m    <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: want this only for dependency plugin but seems not to \x1b[0m (esc)
  \x1b[39mwork there? Maven runs without failure, but the resulting Javadoc is missing the\x1b[0m (esc)
  \x1b[39mhoped-for inherited text -->\x1b[0m (esc)
  \x1b[39m  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependencies\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <build>\x1b[0m (esc)
  \x1b[39m    <resources>\x1b[0m (esc)
  \x1b[39m      <resource>\x1b[0m (esc)
  \x1b[39m        <directory>..<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdirectory\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <includes>\x1b[0m (esc)
  \x1b[39m          <include>LICENSE<\x1b[0m\x1b[35m/\x1b[0m\x1b[95minclude\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <!-- copied from the parent pom because I couldn't figure out a way to\x1b[0m (esc)
  \x1b[39mmake combine.\x1b[0m\x1b[33mchildren\x1b[0m\x1b[39m=\x1b[0m\x1b[32m"append"\x1b[0m\x1b[39m work -->\x1b[0m (esc)
  \x1b[39m          <include>proguard/*<\x1b[0m\x1b[35m/\x1b[0m\x1b[95minclude\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mincludes\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <targetPath>META-INF<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtargetPath\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mresource\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mresources\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <plugins>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-jar-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <configuration>\x1b[0m (esc)
  \x1b[39m          <archive>\x1b[0m (esc)
  \x1b[39m            <manifestEntries>\x1b[0m (esc)
  \x1b[39m              <Automatic-Module-Name>com.google.common<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mAutomatic-Module-Name\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mmanifestEntries\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95marchive\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <extensions>true<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mextensions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <groupId>org.apache.felix<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-bundle-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <version>\x1b[0m\x1b[1;36m5.1\x1b[0m\x1b[39m.\x1b[0m\x1b[1;36m8\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <executions>\x1b[0m (esc)
  \x1b[39m          <execution>\x1b[0m (esc)
  \x1b[39m            <id>bundle-manifest<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <phase>process-classes<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mphase\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <goals>\x1b[0m (esc)
  \x1b[39m              <goal>manifest<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoal\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoals\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecution\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecutions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <configuration>\x1b[0m (esc)
  \x1b[39m          <instructions>\x1b[0m (esc)
  \x1b[39m            <Export-Package>\x1b[0m (esc)
  \x1b[39m              !com.google.common.base.internal,\x1b[0m (esc)
  \x1b[39m              !com.google.common.util.concurrent.internal,\x1b[0m (esc)
  \x1b[39m              com.google.common.*\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mExport-Package\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <Import-Package>\x1b[0m (esc)
  \x1b[39m              com.google.common.util.concurrent.internal,\x1b[0m (esc)
  \x1b[39m              javax.annotation;resolution:=optional,\x1b[0m (esc)
  \x1b[39m              javax.crypto.*;resolution:=optional,\x1b[0m (esc)
  \x1b[39m              sun.misc.*;resolution:=optional\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mImport-Package\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <Bundle-DocURL>\x1b[0m\x1b[4;94mhttps://github.com/google/guava/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mBundle-DocURL\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95minstructions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-compiler-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-source-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: include JDK sources when building testlib doc, too -->\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-dependency-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <executions>\x1b[0m (esc)
  \x1b[39m          <execution>\x1b[0m (esc)
  \x1b[39m            <id>unpack-jdk-sources<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <phase>generate-sources<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mphase\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <goals>\x1b[0m (esc)
  \x1b[39m              <goal>unpack-dependencies<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoal\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoals\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <configuration>\x1b[0m (esc)
  \x1b[39m              <includeArtifactIds>srczip<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mincludeArtifactIds\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <outputDirectory>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.build.directory\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/\x1b[0m\x1b[95mjdk-sources\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95moutputDir\x1b[0m (esc)
  \x1b[95mectory\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <silent>false<\x1b[0m\x1b[35m/\x1b[0m\x1b[95msilent\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <!-- Exclude module-info files \x1b[0m\x1b[1;39m(\x1b[0m\x1b[39msince we're using -source \x1b[0m\x1b[1;36m8\x1b[0m\x1b[39m to \x1b[0m (esc)
  \x1b[39mavoid other modules problems\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m and FileDescriptor \x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mwhich uses a language feature \x1b[0m (esc)
  \x1b[39mnot available in Java \x1b[0m\x1b[1;36m8\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m. -->\x1b[0m (esc)
  \x1b[39m              <excludes>**\x1b[0m\x1b[35m/\x1b[0m\x1b[95mmodule-info.java\x1b[0m\x1b[39m,**\x1b[0m\x1b[35m/java/io/\x1b[0m\x1b[95mFileDescriptor.java\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexcl\x1b[0m (esc)
  \x1b[95mudes\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecution\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecutions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <groupId>org.codehaus.mojo<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <artifactId>animal-sniffer-maven-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-javadoc-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <configuration>\x1b[0m (esc)
  \x1b[39m          <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: Move this to the parent after making jdk-sources \x1b[0m (esc)
  \x1b[39mavailable there. -->\x1b[0m (esc)
  \x1b[39m          <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: can we use includeDependencySources and a local \x1b[0m (esc)
  \x1b[39mcom.oracle.java:jdk-lib:noversion:sources instead of all this unzipping and \x1b[0m (esc)
  \x1b[39mmanual sourcepath modification? -->\x1b[0m (esc)
  \x1b[39m          <!-- \x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mWe need JDK *sources*, not just -link, so that \x1b[0m\x1b[1;39m{\x1b[0m\x1b[39m@inheritDoc\x1b[0m\x1b[1;39m}\x1b[0m\x1b[39m \x1b[0m (esc)
  \x1b[39mworks.\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m -->\x1b[0m (esc)
  \x1b[39m          <sourcepath>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.build.sourceDirectory\x1b[0m\x1b[1;39m}\x1b[0m\x1b[39m:$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.build.directory\x1b[0m (esc)
  \x1b[1;39m}\x1b[0m\x1b[35m/\x1b[0m\x1b[95mjdk-sources\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95msourcepath\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <!-- Passing `-subpackages com.google.common` breaks things, so we \x1b[0m (esc)
  \x1b[39mexplicitly exclude everything else instead. -->\x1b[0m (esc)
  \x1b[39m          <!-- excludePackageNames requires specification of packages separately\x1b[0m (esc)
  \x1b[39mfrom \x1b[0m\x1b[32m"all subpackages"\x1b[0m\x1b[39m.\x1b[0m (esc)
  \x1b[39m               \x1b[0m\x1b[4;94mhttps://issues.apache.org/jira/browse/MJAVADOC-584\x1b[0m\x1b[39m -->\x1b[0m (esc)
  \x1b[39m          <excludePackageNames>\x1b[0m (esc)
  \x1b[39m            com.azul.tooling.in,com.google.common.base.internal,com.google.commo\x1b[0m (esc)
  \x1b[39mn.base.internal.*,com.google.thirdparty.publicsuffix,com.google.thirdparty.publi\x1b[0m (esc)
  \x1b[39mcsuffix.*,com.oracle.*,com.sun.*,java.*,javax.*,jdk,jdk.*,org.*,sun.*\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexcludePackageNames\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <!-- Ignore some tags that are found in Java \x1b[0m\x1b[1;36m11\x1b[0m\x1b[39m sources but not \x1b[0m (esc)
  \x1b[39mrecognized\x1b[0m\x1b[33m...\x1b[0m\x1b[39m under -source \x1b[0m\x1b[1;36m8\x1b[0m\x1b[39m, I think it was? I can no longer reproduce the \x1b[0m (esc)
  \x1b[39mfailure. -->\x1b[0m (esc)
  \x1b[39m          <tags>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>apiNote<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>implNote<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>implSpec<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>jls<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>revised<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <tag>\x1b[0m (esc)
  \x1b[39m              <name>spec<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mname\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <placement>X<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplacement\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtag\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtags\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <!-- \x1b[0m\x1b[1;35mTODO\x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mcpovirk\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m: Move this to the parent after making the \x1b[0m (esc)
  \x1b[39mpackage-list files available there. -->\x1b[0m (esc)
  \x1b[39m          <!-- We add the link ourselves, both so that we can choose Java \x1b[0m\x1b[1;36m9\x1b[0m\x1b[39m over\x1b[0m (esc)
  \x1b[39mthe version that -source suggests and so that we can solve the JSR305 problem \x1b[0m (esc)
  \x1b[39mdescribed below. -->\x1b[0m (esc)
  \x1b[39m          <detectJavaApiLink>false<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdetectJavaApiLink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <offlineLinks>\x1b[0m (esc)
  \x1b[39m            <!-- We need local copies of some of these for \x1b[0m\x1b[1;36m2\x1b[0m\x1b[39m reasons: a \x1b[0m (esc)
  \x1b[39mUser-Agent problem \x1b[0m\x1b[1;39m(\x1b[0m\x1b[4;94mhttps://stackoverflow.com/a/47891403/28465\x1b[0m\x1b[4;94m)\x1b[0m\x1b[39m and an SSL \x1b[0m (esc)
  \x1b[39mproblem \x1b[0m\x1b[1;39m(\x1b[0m\x1b[4;94mhttps://issues.apache.org/jira/browse/MJAVADOC-507\x1b[0m\x1b[4;94m)\x1b[0m\x1b[4;94m.\x1b[0m\x1b[39m If we choose to \x1b[0m (esc)
  \x1b[39mwork around the User-Agent problem, we can go back to <links>, sidestepping the \x1b[0m (esc)
  \x1b[39mSSL problem. -->\x1b[0m (esc)
  \x1b[39m            <!-- Even after we stop using JSR305 annotations in our own code, \x1b[0m (esc)
  \x1b[39mwe'll want this link so that NullPointerTester's docs can link to @CheckForNull \x1b[0m (esc)
  \x1b[39mand friends\x1b[0m\x1b[33m...\x1b[0m\x1b[39m at least once we start using this config for guava-testlib. -->\x1b[0m (esc)
  \x1b[39m            <offlineLink>\x1b[0m (esc)
  \x1b[39m              <url>\x1b[0m\x1b[4;94mhttps://static.javadoc.io/com.google.code.findbugs/jsr305/3.0\x1b[0m (esc)
  \x1b[4;94m.1/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95murl\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <location>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.basedir\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/javadoc-link/\x1b[0m\x1b[95mjsr305\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mlocation\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mofflineLink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <offlineLink>\x1b[0m (esc)
  \x1b[39m              <url>\x1b[0m\x1b[4;94mhttps://static.javadoc.io/com.google.j2objc/j2objc-annotation\x1b[0m (esc)
  \x1b[4;94ms/1.1/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95murl\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <location>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.basedir\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/javadoc-link/\x1b[0m\x1b[95mj2objc-annotations\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mloca\x1b[0m (esc)
  \x1b[95mtion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mofflineLink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <!-- The JDK doc must be listed after JSR305 \x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mand as an \x1b[0m (esc)
  \x1b[39m<offlineLink>, not a <link>\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m so that JSR305 \x1b[0m\x1b[32m"claims"\x1b[0m\x1b[39m javax.annotation. -->\x1b[0m (esc)
  \x1b[39m            <offlineLink>\x1b[0m (esc)
  \x1b[39m              <url>\x1b[0m\x1b[4;94mhttps://docs.oracle.com/javase/9/docs/api/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95murl\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <location>\x1b[0m\x1b[4;94mhttps://docs.oracle.com/javase/9/docs/api/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mlocation\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mofflineLink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <!-- The Checker Framework likewise would claim javax.annotations, \x1b[0m (esc)
  \x1b[39mdespite providing only a subset of the JSR305 annotations, so it must likewise \x1b[0m (esc)
  \x1b[39mcome after JSR305. -->\x1b[0m (esc)
  \x1b[39m            <offlineLink>\x1b[0m (esc)
  \x1b[39m              <url>\x1b[0m\x1b[4;94mhttps://checkerframework.org/api/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95murl\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <location>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.basedir\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/javadoc-link/\x1b[0m\x1b[95mchecker-framework\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mlocat\x1b[0m (esc)
  \x1b[95mion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mofflineLink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mofflineLinks\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <links>\x1b[0m (esc)
  \x1b[39m            <link>\x1b[0m\x1b[4;94mhttps://errorprone.info/api/latest/\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mlink\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mlinks\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <overview>..\x1b[0m\x1b[35m/\x1b[0m\x1b[95moverview.html\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95moverview\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <artifactId>maven-resources-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <executions>\x1b[0m (esc)
  \x1b[39m          <execution>\x1b[0m (esc)
  \x1b[39m            <id>gradle-module-metadata<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <phase>compile<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mphase\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <goals>\x1b[0m (esc)
  \x1b[39m              <goal>copy-resources<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoal\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoals\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <configuration>\x1b[0m (esc)
  \x1b[39m              <outputDirectory>target/publish<\x1b[0m\x1b[35m/\x1b[0m\x1b[95moutputDirectory\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <resources>\x1b[0m (esc)
  \x1b[39m                <resource>\x1b[0m (esc)
  \x1b[39m                  <directory>.<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdirectory\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                  <includes>\x1b[0m (esc)
  \x1b[39m                    <include>module.json<\x1b[0m\x1b[35m/\x1b[0m\x1b[95minclude\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mincludes\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                  <filtering>true<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mfiltering\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mresource\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mresources\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecution\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecutions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <plugin>\x1b[0m (esc)
  \x1b[39m        <groupId>org.codehaus.mojo<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <artifactId>build-helper-maven-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <executions>\x1b[0m (esc)
  \x1b[39m          <execution>\x1b[0m (esc)
  \x1b[39m            <id>attach-gradle-module-metadata<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <goals>\x1b[0m (esc)
  \x1b[39m              <goal>attach-artifact<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoal\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgoals\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <configuration>\x1b[0m (esc)
  \x1b[39m              <artifacts>\x1b[0m (esc)
  \x1b[39m                <artifact>\x1b[0m (esc)
  \x1b[39m                  <file>target/publish/module.json<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mfile\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                  <type>module<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mtype\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m                <\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifact\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m              <\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifacts\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecution\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexecutions\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugins\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mbuild\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <profiles>\x1b[0m (esc)
  \x1b[39m    <profile>\x1b[0m (esc)
  \x1b[39m      <id>srczip-parent<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <activation>\x1b[0m (esc)
  \x1b[39m        <file>\x1b[0m (esc)
  \x1b[39m          <exists>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mjava.home\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/../\x1b[0m\x1b[95msrc.zip\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexists\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mfile\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mactivation\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <dependencies>\x1b[0m (esc)
  \x1b[39m        <dependency>\x1b[0m (esc)
  \x1b[39m          <groupId>jdk<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <artifactId>srczip<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <version>\x1b[0m\x1b[1;36m999\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <scope>system<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mscope\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <systemPath>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mjava.home\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/../\x1b[0m\x1b[95msrc.zip\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95msystemPath\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <optional>true<\x1b[0m\x1b[35m/\x1b[0m\x1b[95moptional\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependencies\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mprofile\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <profile>\x1b[0m (esc)
  \x1b[39m      <id>srczip-lib<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mid\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <activation>\x1b[0m (esc)
  \x1b[39m        <file>\x1b[0m (esc)
  \x1b[39m          <exists>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mjava.home\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/lib/\x1b[0m\x1b[95msrc.zip\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mexists\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mfile\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mactivation\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <dependencies>\x1b[0m (esc)
  \x1b[39m        <dependency>\x1b[0m (esc)
  \x1b[39m          <groupId>jdk<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mgroupId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <artifactId>srczip<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <version>\x1b[0m\x1b[1;36m999\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mversion\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <scope>system<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mscope\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <systemPath>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mjava.home\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/lib/\x1b[0m\x1b[95msrc.zip\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95msystemPath\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <optional>true<\x1b[0m\x1b[35m/\x1b[0m\x1b[95moptional\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependency\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mdependencies\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <build>\x1b[0m (esc)
  \x1b[39m        <plugins>\x1b[0m (esc)
  \x1b[39m          <plugin>\x1b[0m (esc)
  \x1b[39m            <artifactId>maven-javadoc-plugin<\x1b[0m\x1b[35m/\x1b[0m\x1b[95martifactId\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <configuration>\x1b[0m (esc)
  \x1b[39m              <!-- We need to point at the java.base subdirectory because Maven \x1b[0m (esc)
  \x1b[39mappears to assume that package foo.bar is located in foo/bar and not \x1b[0m (esc)
  \x1b[39mjava.base/foo/bar when translating excludePackageNames into filenames to pass to\x1b[0m (esc)
  \x1b[39mjavadoc. \x1b[0m\x1b[1;39m(\x1b[0m\x1b[39mNote that manually passing -exclude to javadoc appears to possibly not\x1b[0m (esc)
  \x1b[39mwork at all for java.* types??\x1b[0m\x1b[1;39m)\x1b[0m\x1b[39m Also, referring only to java.base avoids a lot \x1b[0m (esc)
  \x1b[39mof other sources. -->\x1b[0m (esc)
  \x1b[39m              <sourcepath>$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.build.sourceDirectory\x1b[0m\x1b[1;39m}\x1b[0m\x1b[39m:$\x1b[0m\x1b[1;39m{\x1b[0m\x1b[39mproject.build.direc\x1b[0m (esc)
  \x1b[39mtory\x1b[0m\x1b[1;39m}\x1b[0m\x1b[35m/jdk-sources/\x1b[0m\x1b[95mjava.base\x1b[0m\x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95msourcepath\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m            <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mconfiguration\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m          <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugin\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m        <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mplugins\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m      <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mbuild\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m    <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mprofile\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m  <\x1b[0m\x1b[35m/\x1b[0m\x1b[95mprofiles\x1b[0m\x1b[39m>\x1b[0m (esc)
  \x1b[39m<\x1b[0m\x1b[35m/\x1b[0m\x1b[95mproject\x1b[0m\x1b[1m>\x1b[0m (esc)


Test info versions requires coordinates.

  $ jgo info versions
                                                                                  
   Usage: jgo info versions [OPTIONS] COORDINATE                                  
                                                                                  
   Try 'jgo info versions --help' for help                                        
  ╭─ Error ──────────────────────────────────────────────────────────────────────╮
  │ Missing argument 'COORDINATE'.                                               │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
  [2]

Test info versions with coordinates.

  $ jgo info versions com.google.guava:guava | head -n100
  Available versions for com.google.guava:guava:
    r03
    r05
    r06
    r07
    r08
    r09
    10.0-rc1
    10.0-rc2
    10.0-rc3
    10.0
    10.0.1
    11.0-rc1
    11.0
    11.0.1
    11.0.2
    12.0-rc1
    12.0-rc2
    12.0
    12.0.1
    13.0-rc1
    13.0-rc2
    13.0
    13.0.1
    14.0-rc1
    14.0-rc2
    14.0-rc3
    14.0
    14.0.1
    15.0-rc1
    15.0
    16.0-rc1
    16.0
    16.0.1
    17.0-rc1
    17.0-rc2
    17.0
    18.0-rc1
    18.0-rc2
    18.0
    19.0-rc1
    19.0-rc2
    19.0-rc3
    19.0
    20.0-rc1
    20.0
    21.0-rc1
    21.0-rc2
    21.0
    22.0-rc1
    22.0-rc1-android
    22.0
    22.0-android
    23.0-rc1
    23.0-rc1-android
    23.0
    23.0-android
    23.1-android
    23.1-jre
    23.2-android
    23.2-jre
    23.3-android
    23.3-jre
    23.4-android
    23.4-jre
    23.5-android
    23.5-jre
    23.6-android
    23.6-jre
    23.6.1-android
    23.6.1-jre
    24.0-android
    24.0-jre
    24.1-android
    24.1-jre
    24.1.1-android
    24.1.1-jre
    25.0-android
    25.0-jre
    25.1-android
    25.1-jre
    26.0-android
    26.0-jre
    27.0-android
    27.0-jre
    27.0.1-android
    27.0.1-jre
    27.1-android
    27.1-jre
    28.0-android
    28.0-jre
    28.1-android
    28.1-jre
    28.2-android
    28.2-jre
    29.0-android
    29.0-jre
    30.0-android
    30.0-jre
    30.1-android

Test info entrypoints without jgo.toml.

  $ jgo info entrypoints
  ERROR    jgo.toml not found
  [1]

Test that piping to xpath works regardless of wrap mode (auto-detects non-TTY).

  $ jgo --wrap=smart info pom org.scijava:parsington:3.1.0 | grep -c '<project'
  1

  $ jgo --wrap=raw info pom org.scijava:parsington:3.1.0 | grep -c '<project'
  1
