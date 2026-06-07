/**
 * VULNERABLE: Cross-Site Scripting (XSS)
 * CodeQL should flag: js/xss, js/reflected-xss
 *
 * User input is reflected back in the HTML response without escaping.
 */
const express = require('express');
const app = express();

// BAD: Reflected XSS — user input directly in response HTML
app.get('/search', (req, res) => {
  const searchTerm = req.query.q;
  res.send(`<h1>Results for: ${searchTerm}</h1>`);
});

// BAD: DOM-based XSS via innerHTML (client-side)
app.get('/profile', (req, res) => {
  res.send(`
    <html>
    <body>
      <div id="greeting"></div>
      <script>
        const name = new URLSearchParams(window.location.search).get('name');
        document.getElementById('greeting').innerHTML = 'Hello, ' + name;
      </script>
    </body>
    </html>
  `);
});

// GOOD: Escaped output (safe)
const escapeHtml = (str) => str.replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[c]));

app.get('/search-safe', (req, res) => {
  const searchTerm = escapeHtml(req.query.q || '');
  res.send(`<h1>Results for: ${searchTerm}</h1>`);
});

app.listen(3001);
