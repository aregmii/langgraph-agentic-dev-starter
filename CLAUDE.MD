# Code Agent Project

LangGraph-based code generation agent with SSE streaming.

## Project Structure

- `agent-service/` - Python FastAPI backend
- `agent-service/static/test-sse.html` - Browser test page

## Quick Start

```bash
# Start server (mock mode - free)
cd ~/Workspace/langgraph-agentic-dev-starter/agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Open browser
open http://localhost:8000/static/test-sse.html
```

## Mock vs Real Mode

| Mode | Command | Speed | Cost |
|------|---------|-------|------|
| Mock | `USE_MOCK_LLM=true uvicorn ...` | ~300ms | Free |
| Real | `uvicorn ...` | ~5000ms | API credits |
