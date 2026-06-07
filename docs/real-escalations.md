# Real CodeQL Escalations — Study Guide

These are actual issues from `github/codeql-action` with full debug logs.
Read through each case to understand how engineering triages and resolves them.

---

## Case 1: "No source code was seen during the build" (CLI v2.22.1 regression)

**Issue**: [github/codeql-action#2955](https://github.com/github/codeql-action/issues/2955)
**Frequency**: Very common — this is the #1 CodeQL error you'll encounter.

### What Happened
After upgrading to CodeQL CLI 2.22.1, JS/TS extraction started failing with:
```
CodeQL detected code written in JavaScript/TypeScript but could not process any of it.
```

### Key Debug Log Lines
```log
Extracting javascript
  Running command: [/opt/hostedtoolcache/CodeQL/2.22.1/x64/codeql/javascript/tools/autobuild.sh]
  [build-stdout] Opening project /home/runner/work/components/components/tsconfig.json
  [build-stdout] Done opening project (1239 ms)
  [build-stderr] No JavaScript or TypeScript code found.
Finalizing javascript
  Exit code was 32
```

### Root Cause
CLI v2.22.1 introduced a change to **exclude generated code** from extraction.
It excludes:
1. All files in the `outDir` directory specified by `tsconfig.json`
2. Any `.js` files that have a matching `.ts` file

The customer had `"outDir": "."` in their tsconfig → the ENTIRE repo got excluded.

### Resolution
- **Workaround**: Change `outDir` to a dedicated build directory (e.g., `./dist`)
- **Fix**: Engineering tracked internally; future CLI versions will be smarter about this

### What You Learn
- Always check `tsconfig.json` when JS/TS extraction fails
- New CLI versions can introduce silent behavior changes
- The error message is generic — the REAL cause is buried in debug logs
- Engineering response pattern: ask for repo link → reproduce → identify new logic → provide workaround → track fix

---

## Case 2: OOM (Out of Memory) During JS/TS Extraction

**Issue**: [github/codeql-action#2697](https://github.com/github/codeql-action/issues/2697)
**Frequency**: Common for large monorepos

### What Happened
Customer's CodeQL workflow for JavaScript-TypeScript failed with a cryptic autobuild error.
Debug artifacts revealed the real issue:

### Key Debug Log Lines
```log
[build-stderr] <--- Last few GCs --->
[build-stderr] [2003:0x573a5a0] 185467 ms: Mark-Compact 3808.7 (3892.5) -> 3793.8 (3893.5) MB,
    3045.50 / 0.00 ms (average mu = 0.101, current mu = 0.046) allocation failure;
    scavenge might not succeed

[build-stderr] FATAL ERROR: Ineffective mark-compacts near heap limit
    Allocation failed - JavaScript heap out of memory

[build-stderr] Exception while extracting .../content.ts.
[build-stderr] The TypeScript parser wrapper crashed, possibly from running out of memory.
    at com.semmle.ts.extractor.TypeScriptParser.getExceptionFromMalformedResponse(TypeScriptParser.java:396)
    at com.semmle.ts.extractor.TypeScriptParser.talkToParserWrapper(TypeScriptParser.java:364)
    at com.semmle.ts.extractor.TypeScriptParser.parse(TypeScriptParser.java:434)

[ERROR] Spawned process exited abnormally (code 1; tried to run: autobuild.sh)
```

### Triage Questions Asked by Engineering
1. Can you rerun with **debug logging** turned on? (uploads `debug-artifacts.zip`)
2. How many lines of JS/TS code? → Customer said **1.47 million lines**
3. What runner size? → Standard GitHub-hosted (7GB RAM)

### Resolution
- Customer switched to a **larger runner** (8 cores / 32GB RAM / 300GB SSD) → success
- Engineering acknowledged this is expected for ~1.5M LOC JS/TS projects
- Work planned to reduce memory requirements in future versions

### What You Learn
- `FATAL ERROR: Ineffective mark-compacts near heap limit` = OOM
- JS/TS extraction runs Node.js under the hood — it's the TypeScript parser hitting V8 heap limits
- Standard runners have ~7GB RAM; large repos need larger runners
- The initial error (`autobuild.sh exit code 1`) is useless — you NEED debug artifacts
- How to ask for debug logs: "Can you rerun with debug logging enabled?"

---

## Case 3: SARIF Upload Silently Stopped Working (v3.30.4 regression)

**Issue**: [github/codeql-action#3156](https://github.com/github/codeql-action/issues/3156)
**Frequency**: Occasional after action version bumps

### What Happened
After bumping `upload-sarif` from v3.30.3 to v3.30.4:
- v3.30.3: Upload succeeds, shows full processing output
- v3.30.4: Upload completes silently with NO output — alerts disappear

### Key Evidence
The customer provided side-by-side run comparisons:
- Same SARIF file (identical content)
- Same workflow (only version changed)
- v3.30.3 = works, v3.30.4 = silently fails

### Workaround
Pin to the working version:
```yaml
# Instead of:
uses: github/codeql-action/upload-sarif@v3
# Use:
uses: github/codeql-action/upload-sarif@v3.30.3
```

### What You Learn
- Version pinning is the fastest customer workaround
- "Silent" failures (no error, just no results) are the hardest to debug
- When a customer reports "it stopped working" — ask what changed (version bump)
- Side-by-side run comparison is the gold standard for proving a regression

---

## Case 4: Common Patterns You'll See in Escalations

### Pattern: Customer workflow file
When reading escalations, you'll always see this structure:
```yaml
- uses: github/codeql-action/init@v3      # Step 1: Initialize
  with:
    languages: javascript-typescript
    queries: security-extended

- uses: github/codeql-action/autobuild@v3  # Step 2: Build (this is where most fail)

- uses: github/codeql-action/analyze@v3    # Step 3: Analyze + upload
  with:
    category: "/language:javascript-typescript"
```

### Pattern: Environment variables in logs
```
CODEQL_ACTION_VERSION: 3.29.1       ← action version
CodeQL/2.22.1/x64/codeql            ← CLI version (in the path)
CODEQL_RAM: 6920                    ← RAM allocated (MB)
CODEQL_THREADS: 2                   ← CPU threads
```

### Pattern: Exit codes
| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General error (build failed, extraction error) |
| 2 | Usage error (bad arguments) |
| 32 | No source code found (extraction produced nothing) |
| 33 | Database finalization failure |

---

## How to Get Debug Logs from a Customer

Tell them to re-run the workflow with one of these approaches:

**Option A**: Add `ACTIONS_STEP_DEBUG` secret
```
Settings → Secrets → Actions → New secret
Name: ACTIONS_STEP_DEBUG
Value: true
```

**Option B**: Re-run with debug logging
Click "Re-run all jobs" → check "Enable debug logging"

This uploads a `debug-artifacts.zip` with detailed extraction logs.

---

## Key Repos to Search When Investigating

| Repo | What's There |
|------|-------------|
| [github/codeql-action](https://github.com/github/codeql-action/issues) | Action bugs, version regressions |
| [github/codeql](https://github.com/github/codeql/issues) | Query bugs, false positives, language support |
| [github/codeql-cli-binaries](https://github.com/github/codeql-cli-binaries/releases) | CLI release notes, known issues per version |
| github/c2c-actions-support | Internal escalations (label: `code-scanning`) |

---

## Exercise: Read These Issues Yourself

1. **#2955** — Understand how `tsconfig.json` affects extraction
2. **#2697** — Learn to recognize OOM patterns in stack traces
3. **#3156** — Practice identifying version regressions
4. **#2719** — `upload-sarif` fails with "Not Found" (permissions issue)
5. **#2702** — `UnsupportedOperationException combining SARIF files`

For each one, ask yourself:
- What was the customer's first symptom?
- What information did engineering request?
- What was the root cause?
- What was the workaround vs. the permanent fix?
