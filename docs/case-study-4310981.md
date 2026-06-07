# Case Study: Ticket #4310981 — Code Quality + Java/Kotlin + Private Registry (Self-Hosted)

## Summary

| Field | Value |
|-------|-------|
| **Ticket** | #4310981 |
| **Customer** | Paytient (Healthcare fintech) |
| **Product** | Code Quality / CodeQL / Default Setup |
| **Error** | Exit code 2 — autobuild fails, "unable to access PAYTIENT_BOT_PAT" |
| **Root Cause** | Gradle guard clause hard-fails when PAT env var is missing; Code Quality doesn't pass org secrets |
| **Resolution** | Customer softened Gradle guard + upgraded Java + added memory to self-hosted runners |
| **Duration** | Apr 21 → May 15 (24 days, multi-phase) |

---

## Why This Ticket Is Worth Studying

This ticket demonstrates:
1. **Multiple interacting limitations** — not a single root cause but a stack of issues
2. **Default Setup vs Advanced Setup confusion** — the #1 source of customer confusion
3. **Private registry proxy behavior** — how it works, when it doesn't
4. **Correct escalation pattern** — gathering artifacts, consulting engineering
5. **Managing customer expectations** — when a feature gap exists
6. **Multi-turn investigation** — each reply peels back another layer

---

## The Problem Stack (Layer by Layer)

```
Layer 1: Mixed Java + Kotlin
    → Forces build-mode: autobuild (none = Java only)

Layer 2: Private dependencies (GitHub Packages)
    → Needs authentication to resolve

Layer 3: Org-level secrets ≠ Default Setup secrets
    → Code Quality doesn't pass Actions secrets to autobuild

Layer 4: Private Registry Proxy
    → The SUPPORTED path for Default Setup auth
    → Was working! But...

Layer 5: Gradle guard clause
    → settings.gradle checks: "if PAYTIENT_BOT_PAT is blank, throw exception"
    → Kills the build BEFORE the proxy can do its job

Layer 6: Default Setup vs Advanced Setup confusion
    → Customer had both running simultaneously
    → They are COMPLETELY separate systems
```

---

## Key Technical Concepts Demonstrated

### 1. Code Quality vs Code Scanning (Default Setup vs Advanced Setup)

| Feature | Code Quality / Default Setup | Advanced Setup |
|---------|------------------------------|----------------|
| Workflow | GitHub-managed (invisible) | Your codeql.yml |
| Build mode | Automatic (you can't change it) | You choose (none/autobuild/manual) |
| Secrets | NOT passed from org/repo secrets | Normal Actions secrets work |
| Private deps | Via Private Registry proxy only | Via your own build config |
| Query suite | Fixed by GitHub | You choose |
| Results UI | Security > Code Quality | Security > Code Scanning |
| Runner | You pick the label, that's it | Full control |

### 2. Private Registry Proxy (How It Actually Works)

```
Normal build:
  Gradle → maven.pkg.github.com → 401 → needs PAT

Code Quality Default Setup with Private Registry configured:
  Gradle → HTTP proxy (CodeQL auth proxy) → maven.pkg.github.com → 200
           ↑
           Proxy injects credentials transparently
           Your build doesn't need to know the PAT
```

**But**: If your build script checks `if (System.getenv("PAT") == null) throw Exception()`
BEFORE it even tries to resolve dependencies, the proxy never gets a chance to work.

### 3. Why Mixed Java + Kotlin Complicates Everything

```
Java only → build-mode: none → No build needed → Just scans source files
Java + Kotlin → build-mode: autobuild → Full Gradle build required → Needs dependencies
```

This is documented: "If only Java code is detected then build mode is set to none.
If Kotlin is detected, build mode is set to autobuild."

---

## The Investigation Flow (How This Was Solved)

### Phase 1: Initial Assessment (Day 1)
- Identified: known limitation with private registries + Java/Kotlin
- Found relevant engineering issues:
  - `github/codeql-team#4420` — Private registry config not observed for java/kotlin
  - `github/codeql-team#4482` — PKIX truststore issue (fixed in 2.24.2)
  - `github/code-scanning-engine-quality-team#1567` — Central tracking

### Phase 2: Guide Customer to Private Registry Setup (Day 10)
- Explained that org-level Actions secrets ≠ Default Setup auth
- Provided step-by-step Private Registry configuration
- Customer configured it → still failing

### Phase 3: Debug Artifacts Reveal Root Cause (Day 13)
From the proxy logs:
```
✅ Private registry proxy IS authenticating successfully to maven.pkg.github.com
❌ Gradle guard clause kills the build BEFORE dependencies are resolved
```

The fix:
```groovy
// BEFORE (blocks Code Quality):
def pat = System.getenv("PAYTIENT_BOT_PAT")
    ?: System.getenv("GITHUB_TOKEN")
    ?: throw new RuntimeException("PAT is not defined")

// AFTER (allows Code Quality proxy to work):
def pat = System.getenv("PAYTIENT_BOT_PAT")
    ?: System.getenv("GITHUB_TOKEN")
    ?: System.getenv("CODEQL_ACTION_ANALYSIS_KEY") ? "" : throw new RuntimeException("PAT required")
```

### Phase 4: Clarify Default Setup vs Advanced Setup (Day 13-20)
- Customer had BOTH running and was confused about which was which
- Key clarification: "Code Quality runs its own workflow. It does NOT reuse your codeql.yml."
- Customer chose: "I want findings in the Code Quality UI"

### Phase 5: Resolution (Day 24)
- Customer updated Gradle settings, upgraded Java runtime, added memory
- Code Quality working, findings appearing in UI
- Remaining concern: 20-minute runtime → escalated to engineering

---

## Debug Artifacts Analysis

### proxy-log-file-autobuild-languagejava-kotlin-*.zip
**What to look for**: Did the private registry proxy successfully authenticate?
```
✅ "Proxy authenticated to maven.pkg.github.com" → proxy works
❌ "401 Unauthorized" → credentials wrong or registry not configured
```

### debug-artifacts-autobuild-languagejava-kotlin-*.zip
**What to look for**: Where exactly does autobuild fail?
- If Gradle error → check for guard clauses, missing env vars
- If Maven error → check settings.xml, parent POM resolution
- If compilation error → missing dependencies, wrong JDK version

### debug-artifacts-none-languagejavascript-typescript-*.zip
**What to look for**: JS/TS analysis runs separately and usually succeeds (no build needed)

---

## Response Patterns Worth Noting

### Pattern: Progressive disclosure
Each reply revealed ONE new piece of information and asked ONE clarifying question.
Never dumped all possibilities at once.

### Pattern: Offering binary choices
> "Can you confirm which one you are trying to get working right now?"
> - "I need findings in the Code Quality UI"
> - "Code Scanning UI is fine as long as I can control the build"

### Pattern: Setting expectations about feature gaps
> "Today there is not a supported way to swap that workflow out for your own codeql.yml"

### Pattern: Providing interim workarounds
> "Temporarily uncheck Java/Kotlin in Code Quality so other languages can still scan"

### Pattern: Confirming resolution criteria
Every reply ended with: "To confirm it's resolved, [specific verification step]"

---

## Related Engineering Issues

| Issue | Status | What It Tracks |
|-------|--------|----------------|
| `github/codeql-team#4420` | Open | Private registry not observed for java/kotlin |
| `github/codeql-team#4482` | Closed | PKIX/truststore issue — fixed in CLI 2.24.2 |
| `github/code-scanning-engine-quality-team#1567` | Open | Central tracking for private registry support |

---

## TL;DR for Future Tickets Like This

**When customer says**: "Code Quality fails for Java/Kotlin with private dependencies"

**Check these in order**:
1. Does the repo have Kotlin? → Forces autobuild
2. Is a Private Registry configured at org level? → Required for Default Setup
3. Does the build script REQUIRE a PAT env var just to start? → The proxy can't help if the build dies first
4. Are they confused about Default Setup vs Advanced Setup? → Clarify they're separate systems
5. Can they soften their build guard clause or detect CodeQL context? → `CODEQL_ACTION_ANALYSIS_KEY` env var
