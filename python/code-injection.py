"""
VULNERABLE: Code Injection
CodeQL should flag: py/code-injection

User input passed directly to eval() or exec().
"""
from flask import Flask, request

app = Flask(__name__)


# BAD: eval() with user input — remote code execution
@app.route('/calculate')
def calculate():
    expression = request.args.get('expr')
    result = eval(expression)  # Attacker sends: __import__('os').system('rm -rf /')
    return f"Result: {result}"


# BAD: exec() with user input
@app.route('/run')
def run_code():
    code = request.form.get('code')
    exec(code)  # Full arbitrary code execution
    return "Done"


# GOOD: Use a safe math parser instead
import ast

@app.route('/calculate-safe')
def calculate_safe():
    expression = request.args.get('expr')
    # Only allow literal expressions (numbers, strings, lists, etc.)
    try:
        result = ast.literal_eval(expression)
    except (ValueError, SyntaxError):
        return "Invalid expression", 400
    return f"Result: {result}"


if __name__ == '__main__':
    app.run(debug=True)
