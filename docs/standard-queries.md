# CodeQL Standard Queries — The Ones That Matter

These are the queries that fire most often in customer scans.
Study them at: https://github.com/github/codeql/tree/main

## JavaScript/TypeScript (Most Common in Support)

| Query ID | What It Finds | Precision |
|----------|---------------|-----------|
| `js/sql-injection` | User input → SQL string | High |
| `js/xss` | User input → HTML output | High |
| `js/reflected-xss` | HTTP param → response body | High |
| `js/path-injection` | User input → file path | High |
| `js/code-injection` | User input → eval/Function | High |
| `js/command-line-injection` | User input → exec/spawn | High |
| `js/prototype-polluting-assignment` | Prototype pollution | Medium |
| `js/missing-rate-limiting` | No rate limit on auth endpoints | Low |
| `js/insecure-randomness` | Math.random() for security | Medium |
| `js/hardcoded-credentials` | Passwords/keys in source | High |

## Python

| Query ID | What It Finds | Precision |
|----------|---------------|-----------|
| `py/sql-injection` | User input → SQL | High |
| `py/code-injection` | User input → eval/exec | High |
| `py/command-line-injection` | User input → subprocess | High |
| `py/ssrf` | User input → requests.get URL | High |
| `py/path-injection` | User input → open() path | High |
| `py/unsafe-deserialization` | pickle.loads with user data | High |
| `py/flask-debug` | Flask debug=True in prod | Medium |
| `py/clear-text-logging-sensitive-data` | Logging passwords | Medium |

## Java

| Query ID | What It Finds | Precision |
|----------|---------------|-----------|
| `java/sql-injection` | User input → Statement.execute | High |
| `java/xxe` | XML parsing without disabling entities | High |
| `java/ssrf` | User input → URL connection | High |
| `java/command-line-injection` | User input → Runtime.exec | High |
| `java/path-injection` | User input → File constructor | High |
| `java/ldap-injection` | User input → LDAP query | High |
| `java/xss` | User input → HttpServletResponse | High |
| `java/insecure-cookie` | Cookie without Secure flag | Medium |
| `java/spring-disabled-csrf` | CSRF protection disabled | Medium |

## How to Read a Query File

Every `.ql` file has this structure:
```ql
/**
 * @name Human-readable name          ← Shows in alert title
 * @description What this finds       ← Shows in alert body
 * @kind path-problem                 ← How results are displayed
 * @problem.severity error            ← Severity level
 * @security-severity 9.8             ← CVSS-like score
 * @precision high                    ← False positive rate
 * @id lang/query-id                  ← Unique identifier
 * @tags security                     ← Categorization
 *       external/cwe/cwe-089         ← CWE mapping
 */

import language                        // Language-specific library
import DataFlow::PathGraph             // For taint tracking

class MySource extends ...  { }        // Where bad data comes from
class MySink extends ...    { }        // Where bad data causes harm
class MySanitizer extends ...  { }     // What makes data safe

from MySource source, MySink sink
where /* taint flows from source to sink without sanitizer */
select sink, source, sink, "Alert message"
```

## Query Suites (What Customers Run)

```
codeql/<language>-queries:codeql-suites/<language>-code-scanning.qls
  └── Default: highest precision only (fewest false positives)

codeql/<language>-queries:codeql-suites/<language>-security-extended.qls
  └── security-extended: all security queries (default for code scanning)

codeql/<language>-queries:codeql-suites/<language>-security-and-quality.qls
  └── Most comprehensive: security + quality (most alerts, some noisy)
```

## Running a Specific Query Locally

```bash
# Run a single query against your database
codeql query run queries/find-sensitive-logging.ql --database=js-db

# Run the full security suite
codeql database analyze js-db codeql/javascript-queries:codeql-suites/javascript-security-extended.qls \
  --format=sarif-latest --output=results.sarif

# Run and get human-readable CSV
codeql database analyze js-db codeql/javascript-queries \
  --format=csv --output=results.csv
```

## Where to Find Query Source Code

Browse the actual implementations at:
- **JS**: https://github.com/github/codeql/tree/main/javascript/ql/src/Security
- **Python**: https://github.com/github/codeql/tree/main/python/ql/src/Security
- **Java**: https://github.com/github/codeql/tree/main/java/ql/src/Security

Each folder maps to a CWE category (e.g., `CWE-089` = SQL injection).
