package com.codeagent.gateway.controller;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.util.Map;

/**
 * Task controller that proxies requests to Python agent-service.
 */
@RestController
@RequestMapping("/api/tasks")
public class TaskController {

    private static final Logger log = LoggerFactory.getLogger(TaskController.class);

    private final WebClient webClient;

    public TaskController(@Value("${agent-service.url}") String agentServiceUrl) {
        this.webClient = WebClient.builder()
                .baseUrl(agentServiceUrl)
                .build();
        log.info("Gateway configured to proxy to: {}", agentServiceUrl);
    }

    /**
     * Create a new task - proxies to Python and streams SSE response.
     */
    @PostMapping(produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<String> createTask(@RequestBody Map<String, Object> request) {
        String description = (String) request.getOrDefault("description", "");
        log.info("[Gateway] Received task: '{}'", truncate(description, 50));

        return webClient.post()
                .uri("/tasks")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(String.class)
                .doOnNext(event -> log.debug("[Gateway] Streaming: {}", truncate(event, 80)))
                .doOnComplete(() -> log.info("[Gateway] Stream completed"))
                .doOnError(e -> log.error("[Gateway] Stream error: {}", e.getMessage()));
    }

    /**
     * Execute code - proxies to Python.
     */
    @PostMapping(value = "/execute", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> executeCode(@RequestBody Map<String, Object> request) {
        log.info("[Gateway] Execute code request");

        String response = webClient.post()
                .uri("/tasks/execute")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue(request)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        log.info("[Gateway] Execute completed");
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    /**
     * Get task by ID - proxies to Python.
     */
    @GetMapping("/{taskId}")
    public ResponseEntity<String> getTask(@PathVariable String taskId) {
        log.info("[Gateway] Get task: {}", taskId);

        String response = webClient.get()
                .uri("/tasks/{taskId}", taskId)
                .retrieve()
                .bodyToMono(String.class)
                .block();

        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_JSON)
                .body(response);
    }

    private String truncate(String s, int maxLen) {
        return s.length() > maxLen ? s.substring(0, maxLen) + "..." : s;
    }
}
