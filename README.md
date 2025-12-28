# LangGraph Agentic Dev Starter

An open-source, extensible skeleton for building production-ready AI dev agent platforms.

## Architecture
```
┌─────────────┐     ┌─────────┐     ┌─────────────────┐
│   Client    │────►│ Gateway │────►│  Redis Queue    │
└─────────────┘     │ (Java)  │     └────────┬────────┘
                    └─────────┘              │
                          ▲                  ▼
                          │         ┌─────────────────┐
                          └─────────│  Agent Service  │
                           (poll)   │  (Python)       │
                                    └─────────────────┘
```

## Quick Start
```bash
# Coming soon - Docker Compose setup
```

## Project Structure

- `agent-service/` - Python AI service (LangGraph, FastAPI)
- `gateway-service/` - Java gateway (Spring Boot)
- `k8s/` - Kubernetes manifests
- `docs/` - Documentation and ADRs

## Extension Points

This project is designed to be extended:

1. **LLM Providers** - Implement `BaseLLMClient`
2. **Routers** - Implement `BaseRouter`
3. **Tools** - Implement `BaseTool`
4. **Evaluators** - Implement `BaseEvaluator`

See `docs/extensions/` for guides.