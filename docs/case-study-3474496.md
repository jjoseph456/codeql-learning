# Case Study: Ticket #3474496 — C# PoolGrowthError (CodeQL Internal Bug Fixed in 2.22.1)

## Summary

| Field | Value |
|-------|-------|
| **Ticket** | #3474496 |
| **Customer** | Youi Insurance (Australia) |
| **Product** | CodeQL / Code Scanning / C# |
| **Error** | `PoolGrowthError: Tried to grow a pool beyond the maximum number of pages allowed` |
| **Exit Code** | 100 (internal error) |
| **Root Cause** | CodeQL CLI 2.21.4 bug in string pool during `NamedElement.getName` evaluation — fixed in 2.22.1 |
| **Resolution** | Upgrade to CodeQL CLI 2.22.1 (pin via `tools:` input temporarily) |
| **Duration** | Jun 11 → Jun 27 (16 days) |
| **Escalation** | `github/codeql-team#4068` |

---

## Why This Ticket Is Worth Studying

This ticket demonstrates:
1. **A genuine CodeQL engine bug** — not a config issue, not a customer error
2. **How to recognize "this needs engineering"** quickly — internal crash ≠ misconfiguration
3. **The `tools:` input workaround** — how to pin a specific CodeQL bundle version
4. **Large runner resource allocation** — 96 cores, 367GB RAM, still crashes (it's not OOM)
5. **Multi-layer reusable workflows** — complex org-wide CodeQL setup
6. **Fast turnaround pattern** — identify known issue → escalate → fix shipped

---

## The Error Signature

```
com.semmle.util.exception.CatastrophicError:
  An error occurred while evaluating Element::NamedElement.getName/0#dispred#6665e8e4/2@i16#d4b8bwfi

Tried to grow a pool located at
  /home/runner/work/_temp/codeql_databases/csharp/db-csharp/default/strings/0/pageDump
  beyond the maximum number of pages allowed.

Exit code: 100
```

### How to Instantly Identify This Class of Bug

| Signal | What It Means |
|--------|---------------|
| `CatastrophicError` | Internal CodeQL engine crash (not user error) |
| `PoolGrowthError` | String pool exceeded max pages — evaluator bug or truly massive DB |
| Exit code `100` | Fatal internal error (vs 32 = "no code found") |
| Crash during `run-queries` | Build/extraction succeeded; query evaluation failed |
| `strings/0/pageDump` | Specific to string concatenation operations in evaluator |

### Key Distinction: PoolGrowthError vs OOM

| PoolGrowthError | OOM (Out of Memory) |
|-----------------|---------------------|
| Hard page limit in evaluator | JVM heap exhausted |
| More RAM won't help | More RAM will help |
| Bug in query evaluation logic | Database too large for available resources |
| Fix = CodeQL upgrade | Fix = bigger runner / more RAM |
| Exit code 100 | Exit code 137 (OOM kill) or Java OutOfMemoryError |

---

## The Customer's Setup

```yaml
# Runner: ubuntu-latest-96c-pn (96-core, 384GB RAM, 2TB SSD)
# CodeQL auto-detected: --ram=366965 --threads=96
# CLI version: 2.21.4
# Language: csharp (autobuild)
```

Multi-layer reusable workflow chain:
```
codeql.yml (repo)
  → workflow-sast-source.yml (org shared)
    → sast-detect-languages.yml (detects languages)
    → sast-get-config.yml (gets config)
    → sast-analyze-compiled.yml (runs CodeQL)
      → Determines build mode (manual/autobuild/none)
      → Runs init → build → analyze
      → Filters SARIF → uploads
```

---

## Investigation & Resolution Timeline

### Day 1 (Jun 11-12): Customer files ticket with full error
- Customer proactively included the error, runner specs, and offered debug artifacts
- Internal note found similar issue: `github/codeql-team#2500` (old)
- Public issue: `github/codeql/issues/10703`

### Day 2 (Jun 12-13): Artifacts gathered, escalated
- Support confirmed: 96-core runner with 384GB RAM → not a resource issue
- Confirmed: error is in the evaluator string pool, not extraction/build
- Escalated to engineering: `github/codeql-team#4068`

### Day 7 (Jun 18): Engineering confirms fix
> "Our engineer has done a fix for your issue, the fix should be in the next release for CodeQL"

### Day 15 (Jun 26): Fix released in 2.22.1
- Workaround provided with explicit `tools:` pin:

```yaml
- name: Initialize CodeQL
  uses: github/codeql-action/init@v3
  with:
    languages: ${{ matrix.language }}
    build-mode: ${{ matrix.build-mode }}
    tools: https://github.com/github/codeql-action/releases/download/codeql-bundle-v2.22.1/codeql-bundle-linux64.tar.gz
```

### Day 16 (Jun 27): Customer confirms resolution

---

## Technical Deep Dive: What the RA (Relational Algebra) Dump Tells Us

The error dump shows the query that crashed:

```
Element::NamedElement.getName/0#dispred#6665e8e4
```

This is a **recursive predicate** that computes fully-qualified names for C# elements:
- Generic type arguments: `Method<T>` → concatenates `<`, type arg names, `>`
- Event accessors: `add_EventName`, `remove_EventName`
- Property accessors: `get_PropertyName`, `set_PropertyName`
- Tuple elements: `(element1, element2)`

The bug: when a C# codebase has deeply nested generics or many tuple types, the string concatenation generates so many unique strings that it **exceeds the evaluator's internal page limit** for the string pool. This is a hard limit in the evaluator, not related to available RAM.

---

## Related Engineering Issues

| Issue | What It Tracks |
|-------|----------------|
| `github/codeql-team#4068` | This specific escalation |
| `github/codeql-team#2500` | Older similar PoolGrowthError (C#) |
| `github/codeql-team#2509` | Older escalation for same class of bug |
| `github/codeql/issues/10703` | Public issue tracking page limit errors |

---

## Workaround: Pinning a Specific CodeQL Bundle

When engineering ships a fix in a new CLI version but the Action hasn't rolled forward yet:

```yaml
- uses: github/codeql-action/init@v3
  with:
    tools: https://github.com/github/codeql-action/releases/download/codeql-bundle-v2.22.1/codeql-bundle-linux64.tar.gz
```

**Platform-specific URLs**:
- Linux: `codeql-bundle-linux64.tar.gz`
- macOS (Intel): `codeql-bundle-osx64.tar.gz`
- macOS (ARM): `codeql-bundle-osx-arm64.tar.gz`
- Windows: `codeql-bundle-win64.tar.gz`

**When to remove**: Once `codeql-action/init@v3` auto-resolves to the fixed version (usually within a week of release).

---

## TL;DR for Future Tickets Like This

**When customer says**: "CodeQL crashes with internal error / PoolGrowthError / exit code 100"

**Immediate recognition**:
1. Exit code 100 = internal engine crash (not user fixable)
2. `PoolGrowthError` + `strings/pageDump` = string pool exhaustion bug
3. More RAM will NOT help (it's a hard page limit)
4. Check version → if < 2.22.1, suggest upgrade
5. If already on latest → escalate to engineering with debug artifacts

**Decision tree**:
```
Exit code 100 + CatastrophicError?
  ├── PoolGrowthError in strings/pageDump?
  │     ├── CodeQL < 2.22.1? → Upgrade or pin tools:
  │     └── CodeQL ≥ 2.22.1? → Escalate (new variant)
  └── Other CatastrophicError?
        → Escalate with debug artifacts
```

**How this differs from OOM** (Ticket #2697 in real-escalations.md):
- OOM: Java OutOfMemoryError, exit code 137, fix = more RAM
- PoolGrowthError: Hard evaluator limit, exit code 100, fix = CodeQL upgrade
