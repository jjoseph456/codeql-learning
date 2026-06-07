# Case Study: Ticket #3358800 — CodeQL C++ Manual Build: "No Findings" ≠ Broken

## Summary

| Field | Value |
|-------|-------|
| **Ticket** | #3358800 |
| **Customer** | Flexera (EMU enterprise — Snow Software/Flexera) |
| **Product** | CodeQL / Code Scanning / C++ |
| **Symptom** | "CodeQL manual build not producing expected results" — 0 alerts |
| **Root Cause** | Database is healthy (280K LOC extracted). Customer's test code doesn't match query detection patterns. |
| **Resolution** | Ongoing — engineering confirmed database is sound; customer needs to write buffer overflow patterns that match CodeQL's detection criteria |
| **Duration** | Apr 25 → Jun 10+ (multi-week, back-and-forth for artifacts) |
| **Escalation** | `github/codeql-team#3955` |

---

## Why This Ticket Is Worth Studying

This ticket demonstrates:
1. **"No findings" does NOT mean the database is empty** — the most common customer misconception
2. **C++ tracing (build-mode: manual) on macOS** — how to verify it's working
3. **How to read debug artifacts to confirm extraction** — SARIF, TRAP counts, LOC metrics
4. **False negative expectation management** — CodeQL doesn't detect all buffer overflows
5. **Multi-OS, multi-platform build** — macOS + Windows in same workflow
6. **Persistent artifact gathering** — customer took 4 attempts to provide debug artifacts

---

## The Setup

```yaml
# Reusable workflow — build-macos.yml
- name: Initialize CodeQL
  if: ${{ inputs.build_type == 'debug' }}
  uses: github/codeql-action/init@v3
  with:
    languages: c-cpp
    build-mode: manual

- name: Make target
  run: make macos-${{ inputs.arch }}-${{ inputs.build_type }}

- name: Perform CodeQL Analysis
  if: ${{ inputs.build_type == 'debug' }}
  uses: github/codeql-action/analyze@v3
  with:
    category: "macos"
```

Key details:
- **Language**: C/C++ (requires compilation tracing)
- **Build mode**: manual (correct — `make` between `init` and `analyze`)
- **Platform**: macOS ARM64 (macos-15 runner)
- **CodeQL CLI**: 2.21.3
- **Build system**: CMake + Make
- **Submodules**: yes (Boost libraries included)

---

## The Diagnostic Journey

### What the Customer Reported
> "The analysis step doesn't appear to detect any compiled source files or generate expected results"
> "The database remains empty or incomplete"

### What the Debug Artifacts Actually Show

| Metric | Value | Meaning |
|--------|-------|---------|
| TRAP files imported | 126,515 | Massive database — extraction worked perfectly |
| Successfully extracted files | 2,434 | Source files parsed |
| Lines of code | 399,097 | Total (including headers) |
| Lines of user code | 279,806 | Customer's actual code |
| Compiler errors | 10-50 per TU | System header warnings only (expected on macOS) |
| SARIF results | **0** | No security alerts found |

### The Key Insight

```
Database NOT empty ✅ (126K TRAP files, 280K LOC)
Tracing worked ✅ (main.cpp extracted with all Boost headers)
Queries ran ✅ (60/60 queries completed)
Results = 0 ← This is the "problem"
```

**The database is perfectly healthy. CodeQL simply didn't find any vulnerabilities matching its default query suite patterns.**

---

## Why "Buffer Overflow" Code Might Not Be Detected

CodeQL's C/C++ buffer overflow queries are:
- `CWE-120/VeryLikelyOverrunWrite.ql` — Literal buffer overflows (statically provable)
- `CWE-120/BadlyBoundedWrite.ql` — Bounds-checked writes with wrong bounds
- `CWE-676/DangerousFunctionOverflow.ql` — Use of gets(), strcpy() without bounds
- `Critical/OverflowStatic.ql` — Static array overflow

**What CodeQL DOES detect** (requires all of these):
1. A **source** — untrusted data flowing in
2. A **sink** — the data reaching a dangerous function
3. A **data flow path** connecting them

**What CodeQL does NOT detect**:
- Simple `char buf[10]; buf[20] = 'x';` — some patterns are too trivial/academic
- Buffer overflows that require runtime knowledge of array sizes
- Patterns where the source/sink relationship isn't modeled in the standard library

### Common customer mistake:
```cpp
// Customer thinks this should be detected:
void test_overflow() {
    char buffer[10];
    strcpy(buffer, "This string is way too long for the buffer!");
}
```

This MAY or MAY NOT be flagged depending on:
- Whether the source is a literal (less interesting to taint tracking)
- Whether the query uses local data flow vs global data flow
- The specific precision level of the default suite

---

## Debug Artifacts Cheat Sheet for C++ Tickets

### Confirming extraction worked:

```bash
# 1. Check TRAP file count in dataset-import log
grep "of 126515" cpp/log/dataset-import-*.log | head -5

# 2. Check SARIF metrics
python3 -c "
import json
sarif = json.load(open('cpp.sarif'))
for run in sarif['runs']:
    metrics = run.get('properties',{}).get('metricResults',[])
    for m in metrics:
        if 'lines' in m.get('rule',{}).get('id',''):
            print(f\"{m['rule']['id']} = {m['value']}\")
"

# 3. Check notifications for extracted file count
# Look for: cpp/diagnostics/successfully-extracted-files = N
```

### Confirming build was traced:

```bash
# In finalize log, look for TRAP import completing:
grep "TRAP import complete" cpp/log/database-finalize-*.log
# Should see: "[PROGRESS] database finalize> TRAP import complete (53s)."
# A non-trivial time (>5s) means real data was imported
```

### If database IS empty (contrast with this case):
```
TRAP import complete (0.1s)  ← BAD: nothing was imported
Lines of code = 0            ← BAD: no code found
```

---

## Investigation Flow: C++ "No Findings" Tickets

```
Step 1: Get debug artifacts
    ↓
Step 2: Check SARIF metrics (LOC, extracted files count)
    ├── LOC = 0 → Extraction failed → tracing issue
    └── LOC > 0 → Extraction succeeded → query detection issue
           ↓
Step 3: If extraction succeeded but 0 results:
    ├── Ask: "What specific alert were you expecting?"
    ├── Check: Is the vulnerable pattern in the default query suite?
    ├── Check: Is the code a realistic flow (source→sink) or just a local buffer?
    └── Explain: CodeQL is precision-focused; not all unsafe code triggers alerts
```

---

## Communication Patterns in This Ticket

### Pattern: Customer confuses "no alerts" with "broken scan"
This is the #1 misunderstanding. The response should:
1. Confirm the database is healthy (cite metrics)
2. Ask what specific vulnerability they expected
3. Explain CodeQL's precision model (taint tracking, source→sink)

### Pattern: Difficulty getting proper debug artifacts
This customer took 4 attempts:
- Attempt 1: Sent only workflow logs (not debug artifacts)
- Attempt 2: Linked to private repo (can't access)
- Attempt 3: Sent workflow run logs again (identical to #1)
- Attempt 4: Finally sent actual `debug-artifacts.zip`

**Lesson**: Be very explicit about what "debug artifacts" means:
> "The debug artifacts are a separate downloadable ZIP from the workflow run page (under 'Artifacts' at the bottom), NOT the workflow logs. They are only generated when you add `debug: true` to the init step."

### Pattern: Engineering confirmed "database is not empty"
Once engineering says the database is healthy, pivot to:
> "Could you let us know if there were any specific alerts you were expecting?"

---

## Workflow Configuration Notes

### CodeQL only runs on `debug` builds:
```yaml
if: ${{ inputs.build_type == 'debug' }}
```
This is **smart** — debug builds have no optimizations, so code structure matches source better.

### Using `category` in analyze:
```yaml
category: "macos"
```
This allows separate SARIF uploads per platform (macOS vs Windows can have different findings).

### Submodules enabled:
```yaml
- uses: actions/checkout@v4
  with:
    submodules: true
```
This means CodeQL also scans submodule code (Boost etc.) — explains the 400K total LOC.

---

## TL;DR for Future Tickets Like This

**When customer says**: "CodeQL isn't finding anything / database is empty / no results"

**Check these in order**:
1. **Get debug artifacts** (not just logs!) — `debug: true` must be set
2. **Check SARIF LOC metrics** — if > 0, database is healthy
3. **Check TRAP import time** in finalize log — if > 5s, real code was imported
4. **If database healthy but 0 results**: Ask what they expected to find
5. **If they say "buffer overflow"**: Explain CodeQL needs source→sink flows, not just local unsafe code
6. **If they've inserted test code**: Ask for the exact snippet and verify it matches a real CWE pattern

**The bottom line**: For C/C++, "0 alerts" is a normal outcome for well-written code. CodeQL is high-precision by design — it doesn't flag everything, only things it can prove are exploitable through data flow.
