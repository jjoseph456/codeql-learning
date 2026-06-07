/**
 * @name Find console.log statements with sensitive data
 * @description A simple starter query to find logging of passwords or tokens
 * @kind problem
 * @problem.severity warning
 * @id js/my-first-query/sensitive-logging
 * @tags security
 *       learning
 */

import javascript

from CallExpr log, StringLiteral arg
where
  log.getCalleeName() = "log" and
  log.getReceiver().(DotExpr).getPropertyName() = "log" and
  arg = log.getAnArgument() and
  arg.getValue().regexpMatch("(?i).*(password|token|secret|api.?key).*")
select log, "Possible sensitive data logged: " + arg.getValue()
