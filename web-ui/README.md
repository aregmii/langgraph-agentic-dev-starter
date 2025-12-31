# Code Agent Web UI

Browser interface for the Code Agent platform.

## Development

Currently served by Python FastAPI. Will be served by Java Gateway in the future.
```bash
# Start server
cd ../agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Open browser
open http://localhost:8000
```
