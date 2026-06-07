"""
VULNERABLE: Server-Side Request Forgery (SSRF)
CodeQL should flag: py/ssrf

User input controls a URL that the server fetches,
allowing access to internal services (169.254.169.254, localhost, etc.)
"""
import requests
from flask import Flask, request

app = Flask(__name__)


# BAD: User controls the full URL
@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    response = requests.get(url)  # Attacker sends: http://169.254.169.254/latest/meta-data/
    return response.text


# BAD: User controls part of the URL (still exploitable)
@app.route('/api-proxy')
def api_proxy():
    endpoint = request.args.get('endpoint')
    url = f"http://internal-api:8080/{endpoint}"
    response = requests.get(url)
    return response.text


# GOOD: Allowlist of permitted hosts
ALLOWED_HOSTS = ['api.github.com', 'httpbin.org']

@app.route('/fetch-safe')
def fetch_url_safe():
    url = request.args.get('url')
    from urllib.parse import urlparse
    parsed = urlparse(url)

    if parsed.hostname not in ALLOWED_HOSTS:
        return "Host not allowed", 403

    response = requests.get(url)
    return response.text


if __name__ == '__main__':
    app.run(debug=True)
