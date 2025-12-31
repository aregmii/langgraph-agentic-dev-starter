package com.codeagent.gateway.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Authentication filter - TODO: Implement JWT validation.
 *
 * Future implementation will:
 * - Validate JWT tokens from Authorization header
 * - Extract user info and add to request context
 * - Return 401 for invalid/missing tokens
 */
@Component
@Order(2)
public class AuthFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(AuthFilter.class);

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;

        // TODO: Implement JWT validation
        // For now, just pass through
        log.debug("[Auth] Pass through: {} {}", httpRequest.getMethod(), httpRequest.getRequestURI());

        chain.doFilter(request, response);
    }
}
