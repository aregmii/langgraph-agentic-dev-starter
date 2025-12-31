# Code Agent Platform

AI-powered code generation demonstrating enterprise agentic AI patterns.

## Project Structure
```
langgraph-agentic-dev-starter/
├── agent-service/      # Python/FastAPI - AI Agents
├── gateway-service/    # Java/Spring Boot - API Gateway (planned)
└── web-ui/             # HTML/JS - Browser Interface
```

## Quick Start
```bash
cd agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Open http://localhost:8000
```
