# CodeQL Learning Lab 🔬

A hands-on repo for learning CodeQL and GitHub Code Scanning.
Each folder contains **intentionally vulnerable** code samples that CodeQL should detect.

## Structure

```
├── javascript/       # SQL injection, XSS, path traversal
├── python/           # Code injection, SSRF, unsafe deserialization
├── java/             # SQLi, XXE, LDAP injection
├── queries/          # Custom .ql files you write
├── .github/workflows # Code scanning workflow
└── docs/             # Notes and cheat sheets
```

## Getting Started

### 1. Run CodeQL Locally
```bash
# Create a database for JavaScript
codeql database create js-db --language=javascript --source-root=javascript/

# Run the security queries
codeql database analyze js-db codeql/javascript-queries --format=sarif-latest --output=results.sarif
```

### 2. Run via GitHub Actions
Push to GitHub and the code scanning workflow runs automatically.
Check the **Security** tab → **Code scanning alerts** for results.

### 3. Write Custom Queries
Add `.ql` files to the `queries/` folder and run them against your databases.

## Learning Path

1. **Week 1**: Understand what CodeQL detects (run scans, review alerts)
2. **Week 2**: Read existing queries, understand sources/sinks/taint tracking
3. **Week 3**: Write simple custom queries (find patterns in your code)
4. **Week 4**: Tackle false positives, learn metadata and precision tuning

## Resources

- [CodeQL docs](https://codeql.github.com/docs/)
- [CodeQL for VS Code](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-codeql)
- [Standard query library](https://github.com/github/codeql)
- [vscode-codeql-starter workspace](https://github.com/github/vscode-codeql-starter)
