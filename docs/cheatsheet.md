# CodeQL Cheat Sheet

## Core Concepts (Plain English)

| Term | What It Means |
|------|---------------|
| **Source** | Where untrusted data enters (user input, HTTP params, file reads) |
| **Sink** | Where bad data causes damage (SQL exec, file write, eval) |
| **Taint tracking** | CodeQL traces data from source → sink through variables & functions |
| **Data flow** | The path data takes through code (local = same function, global = across functions) |
| **Sanitizer** | Code that cleans/validates data, breaking the taint chain |

## Running CodeQL Locally

```bash
# Step 1: Create a database (one per language)
codeql database create my-js-db --language=javascript --source-root=./javascript/
codeql database create my-py-db --language=python --source-root=./python/

# Step 2: Run security queries
codeql database analyze my-js-db codeql/javascript-queries:codeql-suites/javascript-security-extended.qls \
  --format=sarif-latest --output=js-results.sarif

# Step 3: View results (human-readable)
codeql database analyze my-js-db codeql/javascript-queries:codeql-suites/javascript-security-extended.qls \
  --format=csv --output=js-results.csv
```

## Query Suites (What to Run)

| Suite | Use Case |
|-------|----------|
| `*-security-extended.qls` | All security queries — what customers see by default |
| `*-security-and-quality.qls` | Security + code quality (more alerts, some noisy) |
| `*-code-scanning.qls` | Tuned for GitHub code scanning (highest precision) |

## Writing a Basic Query

```ql
/**
 * @name Find eval calls with user input
 * @description Detects eval() calls that may execute attacker-controlled code
 * @kind path-problem
 * @problem.severity error
 * @security-severity 9.8
 * @precision high
 * @id js/my-custom-eval-check
 * @tags security
 */

import javascript
import DataFlow::PathGraph

// Source: HTTP request parameters
class UserInput extends DataFlow::Node {
  UserInput() { this = any(Http::RequestInputAccess r) }
}

// Sink: eval() or Function() calls
class EvalSink extends DataFlow::Node {
  EvalSink() {
    exists(DataFlow::InvokeNode call |
      call.getCalleeName() = ["eval", "Function"] and
      this = call.getArgument(0)
    )
  }
}
```

## Metadata That Matters (for precision/false positive tuning)

```ql
// These tags at the top of a .ql file control how alerts behave:
@precision high        // Few false positives — shown by default
@precision medium      // Some false positives — shown in security-extended
@precision low         // Many false positives — only in security-and-quality

@problem.severity error    // Critical — blocks PRs if required
@problem.severity warning  // Important — shows in scan results
@problem.severity recommendation  // Nice-to-fix — informational
```

## Common Customer Questions → Answers

**Q: Why did my dismissed alert come back?**
A: Alerts are tied to the specific code location + query. If the code moves or the query changes, it's treated as a new alert.

**Q: Why isn't CodeQL finding [obvious vulnerability]?**
A: Check if the framework is supported. CodeQL needs to understand the source→sink path through the specific libraries used.

**Q: How do I suppress a false positive in code?**
A: Add a comment above the flagged line:
```java
// lgtm[java/sql-injection]   ← legacy syntax
// codeql[java/sql-injection]  ← newer syntax (CodeQL 2.15+)
```

**Q: Default setup vs Advanced setup?**
A: Default = zero-config, auto-detects languages, uses standard queries. Advanced = custom workflow YAML, manual build steps, custom queries.
