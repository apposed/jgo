Tests jgo info path.

A coordinate is required.

  $ jgo info path > /dev/null 2>&1
  [2]

Show the path of an artifact in the local repository cache.

  $ jgo info path com.google.code.findbugs:jsr305:3.0.2
  */com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar (glob)

The printed path is the real file, ready for use with other tools.

  $ mkdir "$TMPDIR/path-dest"
  $ cp "$(jgo info path com.google.code.findbugs:jsr305:3.0.2)" "$TMPDIR/path-dest"
  $ ls "$TMPDIR/path-dest"
  jsr305-3.0.2.jar

Multiple coordinates print one path per line, in order.

  $ jgo info path junit:junit:4.13.2 com.google.code.findbugs:jsr305:3.0.2
  */junit/junit/4.13.2/junit-4.13.2.jar (glob)
  */com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar (glob)

Packaging and classifier are honored, and need not be JARs.

  $ jgo info path com.google.code.findbugs:jsr305:pom:3.0.2
  */com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.pom (glob)

  $ jgo info path com.google.code.findbugs:jsr305:jar:sources:3.0.2 2>/dev/null
  */com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2-sources.jar (glob)

An unresolvable artifact prints no paths at all, and fails.

  $ jgo info path junit:junit:4.13.2 org.example:does-not-exist:1.0 2>/dev/null
  [1]

Offline mode resolves cached artifacts, but never downloads.

  $ jgo --offline info path com.google.code.findbugs:jsr305:3.0.2
  */com/google/code/findbugs/jsr305/3.0.2/jsr305-3.0.2.jar (glob)

  $ jgo --offline info path org.example:does-not-exist:1.0 2>&1 | grep -o "offline mode is on"
  offline mode is on
