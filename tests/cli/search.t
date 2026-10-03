Tests jgo search command.

Test search requires query argument.

  $ jgo search
                                                                                  
   Usage: jgo search [OPTIONS] QUERY...                                           
                                                                                  
   Try 'jgo search --help' for help                                               
  ╭─ Error ──────────────────────────────────────────────────────────────────────╮
  │ Missing argument 'QUERY...'.                                                 │
  ╰──────────────────────────────────────────────────────────────────────────────╯
                                                                                  
  [2]

Test search --help shows usage.

  $ jgo search --help
                                                                                  
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
                                                                                  


Test search with query.

Temporarily disabled until it can be made to work more robustly.

# $ jgo search scijava-ops
# Found 9 artifacts:
# 
# 1. org.scijava:scijava-ops-indexer:1.0.0
# 
# 2. org.scijava:scijava-ops-api:1.0.0
# 
# 3. org.scijava:scijava-ops-engine:1.0.0
# 
# 4. org.scijava:scijava-ops-spi:1.0.0
# 
# 5. org.scijava:scijava-ops-flim:1.0.0
# 
# 6. org.scijava:scijava-ops-opencv:1.0.0
# 
# 7. org.scijava:scijava-ops-image:1.0.0
# 
# 8. org.scijava:scijava-ops-tutorial:1.0.0
# 
# 9. org.scijava:scijava-ops-ext-parser:1.0.0
# 


Test search with --dry-run.

  $ jgo --dry-run search jython
  [DRY-RUN] Would search Maven Central for 'jython' with limit 20
