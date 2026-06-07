# Case Study: Ticket #4394657 — Java build-mode: none + Private Maven Parent POM

## Summary

| Field | Value |
|-------|-------|
| **Ticket** | #4394657 |
| **Customer** | Iberia Airlines (Coforge contractor) |
| **Product** | CodeQL / Code Scanning |
| **Error** | Exit code 32 — "could not process any of it using the 'none' build mode" |
| **Root Cause** | CodeQL's internal Maven can't resolve private parent POM from AWS CodeArtifact |
| **Resolution** | Customer found root cause themselves; `build-mode: manual` works as workaround |

---

## The Setup

Customer has a **standardized CI workflow** across their entire Java org:
- All Java libraries use `build-mode: none` (no compilation needed for CodeQL)
- Maven artifacts (including parent POMs) hosted in **AWS CodeArtifact** (private registry)
- Credentials injected via `.github/config/settings.xml` → copied to `/root/.m2/settings.xml`
- Chain of reusable workflows: `codeartifact-java-maven.yml` → init → build → analyze

**The twist**: One specific repo (`dist-web-client`) fails, while a simpler repo (`ppm-notification-provider-api`) using the EXACT same workflow + same parent POM passes.

---

## The Failure Chain (from debug logs)

### Step 1: CodeQL reads Maven settings
```log
[build-stdout] Found user Maven settings.xml file at /root/.m2/settings.xml
[build-stdout] Basing CodeQL settings for Maven on existing Maven settings from /root/.m2/settings.xml
[build-stdout] Wrote CodeQL settings for Maven to .../codeql_databases/java/working/settings.xml
```
CodeQL creates its OWN Maven settings file, based on the runner's `/root/.m2/settings.xml`.

### Step 2: CodeQL runs Maven depgraph plugin internally
```log
[autobuild] Apache Maven 3.9.15
[autobuild] [INFO] --- depgraph:4.0.3-CodeQL:graph (default-cli) @ dist-web-client ---
[autobuild] [INFO] Artifact com.ba.captwo.maven.parents:web-api-parent:pom:1.2.56 is present
    in the local repository, but cached from a remote repository ID that is unavailable
```
CodeQL's internal Maven tries to resolve the private parent POM. It's cached locally but the remote repository ID doesn't match what's available.

### Step 3: Maven FATAL error
```log
[ERROR] Some problems were encountered while processing the POMs:
[FATAL] Non-resolvable parent POM for com.ib.captwo.ndc.dist:dist-web-client:3.102.0:
    The following artifacts could not be resolved...
    was not found in https://repo.maven.apache.org/maven2
[ERROR] The build could not read 1 project -> [Help 1]
```
The private parent POM isn't on Maven Central. CodeQL's Maven settings don't have AWS CodeArtifact credentials.

### Step 4: Fallback extraction fails
```log
[WARN] Running maven to determine the project dependency graph failed. Continuing anyway.
```
CodeQL continues with fallback standalone extraction...

### Step 5: Zero files extracted
```log
[DETAILS] database index-files> Found 0 files.
[ERROR] database finalize> CodeQL detected code written in Java/Kotlin but could not process any of it
    using the 'none' build mode.
```
Exit code 32 — total failure.

---

## Why the Simple Repo Passes

The simpler `ppm-notification-provider-api` hits the SAME Maven FATAL error but CodeQL's fallback scan can still partially succeed because:
- Its source structure is straightforward (direct `.java` files in `src/main/java/`)
- It has fewer unresolvable type references
- It doesn't rely on generated sources from XSD/WSDL plugins

The complex `dist-web-client`:
- Depends heavily on generated sources (from `mvn process-sources` → XSD/WSDL → Java)
- Has more complex dependency chains
- The fallback extractor can't resolve enough types to extract anything useful

---

## Key Technical Insight: How build-mode: none Works for Java

```
build-mode: none
    │
    ├─ 1. CodeQL runs its OWN Maven invocation (depgraph plugin)
    │     to determine the dependency graph
    │     Uses: /root/.m2/settings.xml (or its copy)
    │     Problem: No access to private registries
    │
    ├─ 2. If Maven fails → fallback to standalone extraction
    │     Tries to extract source files WITHOUT dependency info
    │     May succeed for simple projects, fails for complex ones
    │
    └─ 3. codeql database index-files
          Scans the source tree for .java files to include
          If extraction produced nothing → "Found 0 files" → exit code 32
```

---

## The Workflow Structure (What Makes This Tricky)

```yaml
# Customer's reusable workflow order:
steps:
  - name: Copy Maven settings.xml to root .m2    # ← Has CodeArtifact creds
    run: |
      mkdir -p /root/.m2
      cp .github/config/settings.xml /root/.m2/settings.xml

  - name: Generate sources                        # ← mvn process-sources (works!)
    run: mvn -B process-sources

  - name: Initialize CodeQL                       # ← build-mode: none
    uses: codeql-action/init@v4

  - name: Build and Package                       # ← Regular Maven build (works!)
    uses: build-java-maven-action@v1

  - name: Perform CodeQL Analysis                 # ← FAILS here
    uses: codeql-action/analyze@v4                #    CodeQL's internal Maven can't
                                                  #    access AWS CodeArtifact
```

The irony: The actual Maven build works fine (because it uses the correct settings.xml with CodeArtifact creds). But CodeQL's INTERNAL Maven invocation during `analyze` doesn't have the right credentials.

---

## Resolution Options

### Workaround (what customer did):
Switch to `build-mode: manual` — CodeQL traces the actual Maven build instead of running its own:
```yaml
- uses: github/codeql-action/init@v4
  with:
    languages: java
    build-mode: manual    # ← Changed from 'none'

- name: Build
  run: mvn -B package -DskipTests

- uses: github/codeql-action/analyze@v4
```

### Proper fix options:
1. **Ensure CodeQL's Maven can access the private registry** — pre-populate `/root/.m2/settings.xml` with CodeArtifact creds BEFORE the analyze step (but CodeQL may overwrite it)
2. **Use `build-mode: autobuild`** — let CodeQL trace the actual build process
3. **Pre-resolve the parent POM** — run `mvn dependency:resolve` before CodeQL init so it's cached locally

---

## What You Learn From This Ticket

### Investigation Skills:
1. **Compare working vs failing** — same workflow, different repos = the difference is in the code/project structure
2. **Read debug artifacts** — the `database-trace-command` log shows EXACTLY what Maven commands CodeQL runs internally
3. **Trace the credential flow** — settings.xml is written by `setup-java`, but CodeQL has its own Maven invocation that may not inherit those creds
4. **Understand fallback behavior** — `build-mode: none` has a silent fallback path that works for simple projects but fails for complex ones

### Product Knowledge:
1. `build-mode: none` ≠ "no build at all" — CodeQL still runs Maven internally for the dependency graph
2. CodeQL's Maven uses its OWN settings file (derived from `/root/.m2/settings.xml` but modified)
3. Private registries (AWS CodeArtifact, Nexus, Artifactory) are a common pain point with `build-mode: none`
4. The depgraph Maven plugin (`depgraph:4.0.3-CodeQL`) is CodeQL's internal tool for resolving dependencies
5. Exit code 32 means "detected language but extracted nothing"

### Support Response Patterns:
1. **First response was template** — asked for debug logs (standard procedure)
2. **Second response was slightly off** — suggested Kotlin detection issue (not the root cause)
3. **Customer self-resolved** — they dug into the logs themselves and found the root cause
4. **Lesson**: When a customer provides detailed analysis in their initial report, engage with THEIR hypothesis first rather than running through templates

---

## Debug Artifacts Breakdown

| File | What's Inside | Key Finding |
|------|---------------|-------------|
| `database-trace-command-*.log` | CodeQL's internal Maven run | Shows the depgraph plugin failure |
| `database-index-files-*.log` | File scanning results | "Found 0 files" |
| `database-finalize-*.log` | Final error | Exit code 32 |
| `database-init-*.log` | CodeQL bundle download | Version 2.25.5 confirmed |
| `db-java-partial.zip` | Partial database | Empty — nothing extracted |

---

## Related Docs

- [CodeQL build modes for compiled languages](https://docs.github.com/en/code-security/code-scanning/creating-an-advanced-setup-for-code-scanning/codeql-code-scanning-for-compiled-languages#codeql-build-modes)
- [Troubleshooting: no source code seen](https://gh.io/troubleshooting-code-scanning/no-source-code-seen-during-build)
- [Specifying build steps manually](https://docs.github.com/en/code-security/code-scanning/creating-an-advanced-setup-for-code-scanning/codeql-code-scanning-for-compiled-languages#about-specifying-build-steps-manually)
