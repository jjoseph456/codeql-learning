/**
 * VULNERABLE: SQL Injection
 * CodeQL should flag: js/sql-injection
 *
 * The user input flows directly into a SQL query without sanitization.
 * This is the #1 most common finding customers ask about.
 */
const express = require('express');
const mysql = require('mysql');
const app = express();

const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'password',
  database: 'testdb'
});

// BAD: Direct string concatenation with user input
app.get('/user', (req, res) => {
  const userId = req.query.id;
  const query = "SELECT * FROM users WHERE id = '" + userId + "'";
  db.query(query, (err, results) => {
    if (err) return res.status(500).send(err);
    res.json(results);
  });
});

// GOOD: Parameterized query (safe)
app.get('/user-safe', (req, res) => {
  const userId = req.query.id;
  const query = "SELECT * FROM users WHERE id = ?";
  db.query(query, [userId], (err, results) => {
    if (err) return res.status(500).send(err);
    res.json(results);
  });
});

app.listen(3000);
