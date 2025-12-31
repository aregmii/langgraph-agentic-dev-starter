# Code Agent Platform

AI-powered code generation demonstrating enterprise agentic AI patterns.

## Project Structure
```
langgraph-agentic-dev-starter/
├── agent-service/      # Python/FastAPI - AI Agents (port 8000)
├── gateway-service/    # Java/Spring Boot - API Gateway (port 8080)
└── web-ui/             # HTML/JS - Browser Interface (legacy, now in gateway)
```

## Quick Start
```bash
# Terminal 1: Start Python agent-service
cd agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Terminal 2: Start Java gateway
cd gateway-service
./mvnw spring-boot:run

# Open http://localhost:8080
```

## Server Logs
```bash
# View Python logs (if running in background)
tail -f /tmp/python-server.log

# View Java logs (if running in background)
tail -f /tmp/java-server.log
```

## Current Status (Module 8 Complete)
- Python agent-service: LangGraph workflow with SSE streaming
- Java gateway: Proxies UI and API calls to Python
- Mock mode for free development, Real mode uses Grok API

## Next Steps
- Module 9: Auth & Rate Limiting (JWT, Bucket4j)
- Module 10: Circuit Breaker (Resilience4j)
