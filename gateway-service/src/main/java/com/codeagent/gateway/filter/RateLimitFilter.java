package com.codeagent.gateway.filter;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Rate limiting filter - TODO: Implement with Bucket4j.
 *
 * Future implementation will:
 * - Limit requests per client IP
 * - Return 429 when limit exceeded
 * - Use sliding window algorithm
 */
@Component
@Order(1)
public class RateLimitFilter implements Filter {

    private static final Logger log = LoggerFactory.getLogger(RateLimitFilter.class);

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest httpRequest = (HttpServletRequest) request;

        // TODO: Implement rate limiting with Bucket4j
        // For now, just pass through
        log.debug("[RateLimit] Pass through: {} {}", httpRequest.getMethod(), httpRequest.getRequestURI());

        chain.doFilter(request, response);
    }
}
