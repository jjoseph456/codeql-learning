package com.learning.vulnerable;

import javax.xml.parsers.*;
import org.xml.sax.InputSource;
import javax.servlet.http.*;
import java.io.*;

/**
 * VULNERABLE: XML External Entity (XXE) Injection
 * CodeQL should flag: java/xxe
 *
 * Parsing XML from user input without disabling external entities
 * allows reading local files or SSRF via DTD declarations.
 */
public class XxeInjection extends HttpServlet {

    // BAD: Default XML parser with no protections
    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws Exception {
        String xmlInput = request.getParameter("data");

        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        // No protections set — vulnerable to XXE
        DocumentBuilder builder = factory.newDocumentBuilder();
        InputSource is = new InputSource(new StringReader(xmlInput));
        builder.parse(is); // Attacker sends: <!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
    }

    // GOOD: Disable external entities and DTDs
    protected void doPostSafe(HttpServletRequest request, HttpServletResponse response)
            throws Exception {
        String xmlInput = request.getParameter("data");

        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);

        DocumentBuilder builder = factory.newDocumentBuilder();
        InputSource is = new InputSource(new StringReader(xmlInput));
        builder.parse(is); // Safe — external entities disabled
    }
}
