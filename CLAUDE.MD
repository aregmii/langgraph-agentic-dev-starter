# Code Agent Project

LangGraph-based code generation agent with SSE streaming.

## Project Structure

```
agent-service/
├── app/
│   ├── main.py              # FastAPI app
│   ├── logging_utils.py     # Request-traced logging
│   ├── api/
│   │   ├── routes.py        # POST /tasks (SSE stream)
│   │   └── workflow_events.py
│   ├── agents/
│   │   ├── code_agent.py    # CodeAgent class
│   │   └── task_execution.py # TaskExecution with progress
│   └── llm/
│       ├── grok_client.py   # Real Grok API
│       └── mock_client.py   # Mock for testing
└── static/
    └── test-sse.html        # Browser test UI
```

## Quick Start

```bash
cd ~/Workspace/langgraph-agentic-dev-starter/agent-service
source ../.venv/bin/activate

# Mock mode (free, fast)
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Real mode (uses API credits)
uvicorn app.main:app --reload

# Open test UI
open http://localhost:8000/static/test-sse.html
```

## Server Logs

Logs are prefixed with request ID for tracing:
```
[req-a1b2c3d4] 🆕 NEW REQUEST
[req-a1b2c3d4] → [CodeAgent] Classifying task type using LLM...
[req-a1b2c3d4] ✓ Done (202ms) → Task type: code_generation
```

Filter by request: `grep "req-a1b2c3d4" /tmp/server.log`
