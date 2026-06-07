/**
 * VULNERABLE: Path Traversal
 * CodeQL should flag: js/path-injection
 *
 * User input controls a file path without validation.
 */
const express = require('express');
const path = require('path');
const app = express();

// BAD: User input directly in file path
app.get('/download', (req, res) => {
  const filename = req.query.file;
  const filePath = '/var/uploads/' + filename;
  res.sendFile(filePath);
});

// GOOD: Validate the resolved path stays within the allowed directory
app.get('/download-safe', (req, res) => {
  const filename = req.query.file;
  const basePath = '/var/uploads';
  const filePath = path.resolve(basePath, filename);

  if (!filePath.startsWith(basePath)) {
    return res.status(403).send('Access denied');
  }
  res.sendFile(filePath);
});

app.listen(3002);
