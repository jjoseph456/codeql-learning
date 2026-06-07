package com.learning.vulnerable;

import java.sql.*;
import javax.servlet.http.*;

/**
 * VULNERABLE: SQL Injection (Java)
 * CodeQL should flag: java/sql-injection
 *
 * String concatenation in SQL queries with user input.
 */
public class SqlInjection extends HttpServlet {

    // BAD: String concatenation with user input
    protected void doGet(HttpServletRequest request, HttpServletResponse response) {
        String userId = request.getParameter("id");
        String query = "SELECT * FROM users WHERE id = '" + userId + "'";

        try {
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db");
            Statement stmt = conn.createStatement();
            ResultSet rs = stmt.executeQuery(query); // SQL injection here
            // process results...
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    // GOOD: PreparedStatement with parameterized query
    protected void doGetSafe(HttpServletRequest request, HttpServletResponse response) {
        String userId = request.getParameter("id");

        try {
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db");
            PreparedStatement stmt = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
            stmt.setString(1, userId); // Safe — properly escaped
            ResultSet rs = stmt.executeQuery();
            // process results...
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }
}
