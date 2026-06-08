# CodeQL: How It Works (From Zero)

## The Problem It Solves

Developers write code. Sometimes that code has security holes — not because they're dumb, but because apps are complex. A user types something into a form, and 47 functions later, that text ends up inside a database command that an attacker can manipulate.

**No human reviewer can trace every possible path data takes through a million-line codebase.** CodeQL does.

---

## Step 1: Turning Code Into a Database

Before you can search code, you need to **index** it — just like Google crawls web pages before you can search them.

```
Your source code (.py, .js, .java files)
        ↓
   CodeQL "creates a database"
        ↓
A structured representation of EVERYTHING:
  - Every variable
  - Every function call
  - Every if/else branch
  - Every parameter passed between functions
  - Every return value
```

This is what `codeql database create` does. It reads your code and builds a **searchable map** of how everything connects.

**Analogy**: Imagine turning a city into a GPS map. The streets are function calls. The intersections are where data gets passed. Now you can ask "can a car get from Point A to Point B?"

---

## Step 2: Queries = Questions You Ask the Map

A "query" is a **question** you ask that database. CodeQL has its own language (called QL) because normal languages can't express "trace all possible paths data could take."

**The 3 parts of every security query:**

```
SOURCE: Where does untrusted data enter?
  → HTTP request, file upload, cookie, URL parameter, environment variable

SINK: Where would that data be dangerous?
  → SQL query, shell command, eval(), file path, HTML response

FLOW: Can the data actually get from source to sink?
  → CodeQL traces through function calls, variable assignments,
    return values, even across files
```

**If all 3 exist → alert. If any is missing → no alert.**

---

## Step 3: Why "Flow" Is the Hard Part

This is what makes CodeQL different from simple text search (like grep):

```python
# File: routes.py
@app.route('/search')
def search():
    query = request.args.get('q')    # SOURCE: user types something
    return do_search(query)          # passes it to another function

# File: database.py  
def do_search(term):
    cleaned = term.strip()           # some processing
    return run_query(cleaned)        # passes it again

# File: db_engine.py
def run_query(text):
    sql = f"SELECT * FROM items WHERE name = '{text}'"  # SINK!
    cursor.execute(sql)              # SQL injection here
```

A **grep** search for "user input in SQL" would never find this — it spans 3 files and 3 function calls.

**CodeQL traces**: `request.args.get('q')` → `query` → `do_search(query)` → `term` → `cleaned` → `run_query(cleaned)` → `text` → SQL string → `cursor.execute()`

It proves the path exists. **That's data flow analysis.**

---

## Step 4: What Queries Look Like

Think of it like SQL but for code:

| SQL (searches databases) | CodeQL (searches code) |
|---|---|
| `SELECT * FROM users WHERE role = 'admin'` | "Find where user input reaches a dangerous function" |

**Real CodeQL query in plain English:**

> "Find me every place where data from an HTTP request eventually reaches a `pickle.loads()` call without being sanitized in between."

**What that looks like in actual QL:**

```ql
from DataFlow::PathNode source, DataFlow::PathNode sink
where
  source is an HTTP request parameter    // SOURCE: user input
  and sink is a call to pickle.loads()   // SINK: dangerous function
  and data flows from source to sink     // FLOW: CodeQL proves the connection
select sink, "Unsafe deserialization from $@.", source, "user input"
```

**Each query file asks ONE question:**

| Query file | Question it asks |
|---|---|
| `CWE-502/UnsafeDeserialization.ql` | "Does user input reach pickle/yaml/marshal?" |
| `CWE-918/FullServerSideRequestForgery.ql` | "Does user input control a URL in requests.get()?" |
| `CWE-94/CodeInjection.ql` | "Does user input reach eval() or exec()?" |
| `CWE-79/ReflectedXss.ql` | "Does user input get sent back in an HTML response?" |
| `CWE-89/SqlInjection.ql` | "Does user input end up in a SQL string?" |

GitHub ships ~50-90 of these queries per language. They run automatically on every push.

---

## Step 5: What Customers Actually See

```
Developer pushes code to a PR
        ↓
GitHub Actions runs automatically
        ↓
CodeQL creates database (indexes the code)
        ↓
Runs ~50-90 queries (one per vulnerability type)
        ↓
Produces a SARIF file (list of alerts with locations)
        ↓
Uploads to GitHub
        ↓
Developer sees ⚠️ alerts directly on the PR:
  "Line 42: SQL injection — user input flows to database query"
```

---

## Step 6: Why "No Alert" Doesn't Mean "No Bug"

CodeQL is **precision-focused**. It only alerts when it can PROVE all 3 parts:

```
✅ Alert: source exists + sink exists + flow proven between them
❌ No alert: any piece is missing or can't be proven
```

This means:
- Code with bugs CodeQL can't trace → no alert (false negative)
- Code that LOOKS dangerous but has no untrusted source → no alert (correct)
- Code where the "safe" version is used (e.g., `json.loads` instead of `pickle.loads`) → no alert (correct)

**This is by design.** Fewer false positives = developers trust the tool and actually fix things.

---

## Step 7: Why Things Break (Common Ticket Patterns)

| What went wrong | In plain terms |
|---|---|
| **Exit code 32** | "I couldn't build the map — the code wouldn't compile, so I have nothing to search" |
| **0 findings** | "I built the map fine, asked all my questions, and none of the dangerous patterns exist" |
| **Exit code 100** | "I crashed while asking a question because the map was too complex for my internal memory" |
| **Exit code 2** | "The build failed so the map is incomplete" |
| **"Default Setup" confusion** | "There are two separate robots — customer confused which one is running" |

---

## The One-Sentence Summary

> **CodeQL turns code into a searchable database, then runs pre-written questions that ask "can an attacker's input reach a dangerous operation?" — if yes, it raises an alert on the PR.**

---

## Local Example (What You Just Ran)

```bash
# Step 1: Build the database (index the code)
codeql database create py-db --language=python --source-root=python/

# Step 2: Run all the questions against it
codeql database analyze py-db codeql/python-queries --format=sarif-latest --output=results/py-results.sarif

# Step 3: See what it found
# → 13 alerts: code injection, SSRF, unsafe deserialization, XSS, flask debug
```

What CodeQL traced in YOUR code:
```
request.cookies.get('session')  →  base64.b64decode()  →  pickle.loads()
       SOURCE                         FLOW                    SINK
       
Result: ⚠️ "Unsafe deserialization depends on a user-provided value"
```
