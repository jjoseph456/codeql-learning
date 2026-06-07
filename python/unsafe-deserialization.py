"""
VULNERABLE: Unsafe Deserialization
CodeQL should flag: py/unsafe-deserialization

pickle.loads() with untrusted data = arbitrary code execution.
"""
import pickle
import base64
from flask import Flask, request

app = Flask(__name__)


# BAD: Deserializing user-controlled data with pickle
@app.route('/load-session')
def load_session():
    session_data = request.cookies.get('session')
    decoded = base64.b64decode(session_data)
    user_session = pickle.loads(decoded)  # RCE via crafted pickle payload
    return f"Welcome back, {user_session['username']}"


# GOOD: Use JSON for untrusted data (no code execution possible)
import json

@app.route('/load-session-safe')
def load_session_safe():
    session_data = request.cookies.get('session')
    decoded = base64.b64decode(session_data)
    user_session = json.loads(decoded)  # Safe — only parses data structures
    return f"Welcome back, {user_session['username']}"


if __name__ == '__main__':
    app.run(debug=True)
