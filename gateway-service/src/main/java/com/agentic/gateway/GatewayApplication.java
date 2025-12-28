package com.agentic.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Entry point for the Gateway Service.
 * 
 * This service handles:
 * - REST API for client requests
 * - Request routing to Redis queue
 * - Task status polling
 * - Health checks and metrics
 */
@SpringBootApplication
public class GatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}