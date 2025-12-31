# Gateway Service

Java/Spring Boot API Gateway for Code Agent Platform.

## Features

| Feature | Status | Description |
|---------|--------|-------------|
| Static UI serving | ✅ | Serves web-ui |
| Proxy to Python | ✅ | Routes /api/tasks to agent-service |
| SSE streaming | ✅ | Streams responses from Python |
| Rate limiting | 📋 TODO | Bucket4j implementation |
| JWT Auth | 📋 TODO | Spring Security + JWT |
| Circuit breaker | 📋 TODO | Resilience4j |

## Quick Start
```bash
# Terminal 1: Start Python agent-service
cd ../agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Terminal 2: Start Java gateway
cd ../gateway-service
./mvnw spring-boot:run

# Open http://localhost:8080
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| / | GET | Serves index.html |
| /api/tasks | POST | Create task (SSE stream) |
| /api/tasks/execute | POST | Execute code |
| /api/tasks/{id} | GET | Get task status |
| /actuator/health | GET | Health check |
