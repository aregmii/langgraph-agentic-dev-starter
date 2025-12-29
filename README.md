# LangGraph Agentic Code Assistant

A production-ready AI-powered code generation agent built with LangGraph, FastAPI, and (planned) Java Spring Boot gateway. This project serves as both a learning exercise and a foundation for building multi-agent systems.

## 🎯 Project Vision

Build an iterative code assistant with a web UI where:
- **Left panel**: Code editor (accumulates generated code)
- **Right panel**: Chat interface with real-time progress updates
- User sends requests like "Write a sort function" → "Now add main()" → "Add error handling"
- Each request includes previous code as context
- Real-time streaming shows: "🔍 Identifying... ⚡ Generating... ✅ Validating..."

```
┌─────────────────────────────────────────────────────────────────┐
│  Code Agent                                        [Settings]   │
├─────────────────────────────────┬───────────────────────────────┤
│   Code Editor                   │   Chat                        │
│   ┌───────────────────────────┐ │   ┌───────────────────────┐   │
│   │ def sort_list(lst):       │ │   │ You: Add reverse param│   │
│   │     return sorted(lst)    │ │   │                       │   │
│   │                           │ │   │ 🔍 Identifying...     │   │
│   │ def main():               │ │   │ ⚡ Generating...      │   │
│   │     print(sort_list([3])) │ │   │ ✅ Validating...      │   │
│   └───────────────────────────┘ │   │                       │   │
│   [▶ Run]  [Clear]              │   │ Agent: Done! ✓        │   │
│   Output: [1, 2, 3]             │   └───────────────────────┘   │
└─────────────────────────────────┴───────────────────────────────┘
```

---

## 🏗️ Architecture

### Current: Single Agent with Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                      Code Agent                             │
│                                                             │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐              │
│   │ Identify │ → │ Execute  │ → │ Evaluate │              │
│   │ (LLM)    │   │ (LLM)    │   │ (AST)    │              │
│   └──────────┘   └──────────┘   └────┬─────┘              │
│                                      │                     │
│                        Retry ◄───────┘                     │
└─────────────────────────────────────────────────────────────┘
```

### Future: Multi-Agent Orchestration

```
                        ┌─────────────┐
                        │ Supervisor  │
                        └──────┬──────┘
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Doc      │    │ Code     │    │ Debugger │
        │ Lookup   │    │ Writer   │    │ Agent    │
        │ (RAG)    │    │ Agent    │    │          │
        └──────────┘    └──────────┘    └──────────┘
```

---

## 📁 Project Structure

```
langgraph-agentic-dev-starter/
├── .env                          # API keys (XAI_API_KEY)
├── .gitignore
├── README.md
│
├── agent-service/                # Python - AI Brain
│   ├── pyproject.toml            # Dependencies & config
│   ├── app/
│   │   ├── main.py               # FastAPI application
│   │   ├── logging_utils.py      # Workflow metrics & logging
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py         # POST /tasks, GET /tasks/{id}
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── code_agent.py     # LangGraph workflow
│   │   │
│   │   ├── classifier/
│   │   │   ├── __init__.py
│   │   │   ├── prompts.py        # Classification prompts
│   │   │   └── task_identifier.py # LLM-based task classification
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── base_evaluator.py # Evaluator interface
│   │   │   ├── base_llm.py       # LLM client interface
│   │   │   ├── base_router.py    # Router interface (legacy)
│   │   │   ├── base_tool.py      # Tool interface
│   │   │   └── task_state.py     # TaskState, TaskType, TaskStatus
│   │   │
│   │   ├── evaluators/
│   │   │   ├── __init__.py
│   │   │   └── syntax_evaluator.py # AST-based syntax validation
│   │   │
│   │   ├── executors/
│   │   │   ├── __init__.py
│   │   │   ├── code_executor.py  # LLM code generation
│   │   │   └── prompts.py        # Task-specific prompts
│   │   │
│   │   ├── health/
│   │   │   ├── __init__.py
│   │   │   └── health.py         # /health/live, /health/ready
│   │   │
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   └── grok_client.py    # xAI Grok implementation
│   │   │
│   │   ├── metrics/
│   │   │   └── __init__.py       # (TODO: Prometheus metrics)
│   │   │
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── code_runner.py    # Execute code in subprocess
│   │       └── syntax_checker.py # AST syntax validation
│   │
│   └── tests/                    # (TODO: Add tests)
│
├── gateway-service/              # Java - Enterprise Gateway (TODO)
│   ├── pom.xml
│   └── src/
│
└── k8s/                          # Kubernetes manifests (TODO)
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- xAI API key (https://console.x.ai/)

### Setup

```bash
# Clone the repo
git clone https://github.com/aregmii/langgraph-agentic-dev-starter.git
cd langgraph-agentic-dev-starter

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e "./agent-service[dev]"

# Set up API key
echo 'XAI_API_KEY=your-key-here' > .env

# Run the server
cd agent-service
uvicorn app.main:app --reload
```

### Test

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Write a Python function to sort a list of integers"}'
```

### Expected Server Output

```
20:24:18 │ INFO  │ 🔍 [ IDENTIFY ] Analyzing: 'Write a Python function to sort...'
20:24:22 │ INFO  │    └── Done (3924ms) - Task type: code_generation
20:24:22 │ INFO  │ ⚡ [ EXECUTE  ] Generating code for code_generation...
20:24:26 │ INFO  │    └── Done (3460ms) - Generated 630 chars
20:24:26 │ INFO  │ ✅ [ EVALUATE ] Validating syntax...
20:24:26 │ INFO  │    └── Done (1ms) - Passed! Score: 1.0

==================================================
📊 WORKFLOW COMPLETE - Task eea3e46f...
==================================================
Total Duration: 7390ms

Node Breakdown:
  identify        │   3924ms │ ██████████████████████████████
  execute         │   3460ms │ ██████████████████████████████
  evaluate        │      1ms │ 

🐢 Slowest: identify (3924ms)
==================================================
```

---

## 📊 Agentic Design Patterns Covered

| Pattern | Status | Location |
|---------|--------|----------|
| **Loop** (goal → execute → adapt) | ✅ Done | `code_agent.py` |
| **Prompt Chaining** | ✅ Done | Identify → Execute → Evaluate |
| **Structured Output** | ✅ Done | `TaskState` dataclass |
| **Routing/Classification** | ✅ Done | `TaskIdentifier` (LLM-based) |
| **Reflection** | ✅ Done | Evaluate → Retry loop |
| **Tool Use** | ⚠️ Partial | Syntax checker (not LLM-selected) |
| **Streaming** | 🔜 Next | SSE for real-time updates |
| **Error Handling** | 📋 Planned | Retries, timeouts, guardrails |
| **Embeddings/RAG** | 📋 Planned | Vector search for docs |
| **Planning** | 📋 Planned | Multi-step plan generation |
| **Multi-Agent** | 📋 Planned | Supervisor + specialized agents |
| **Memory** | 📋 Planned | Short-term + long-term context |

---

## 📋 Module Plan

### ✅ Completed Modules

| Module | Description | Key Files |
|--------|-------------|-----------|
| **0: Foundation** | Project setup, dependencies | `pyproject.toml`, `pom.xml` |
| **1: Core Interfaces** | Base classes, TaskState | `core/*.py` |
| **2: Tools** | Syntax checker, code runner | `tools/*.py` |
| **3: Graph & Routing** | LangGraph workflow, classifier | `agents/`, `classifier/` |
| **4: FastAPI** | REST API, health checks | `api/`, `health/`, `main.py` |
| **5: Observability** | Structured logging, metrics | `logging_utils.py` |

### 🔜 Upcoming Modules

| Module | Description | Patterns |
|--------|-------------|----------|
| **6: Streaming** | SSE for real-time progress to client | Streaming |
| **7: Error Handling** | Retries, timeouts, resilience | Guardrails |
| **8: Production Patterns** | Async queue, Redis, DI | - |
| **9: Embeddings & RAG** | Vector search, semantic retrieval | RAG |
| **10: Tool Use (LLM-selected)** | Agent picks tools dynamically | Tool Use |
| **11: Multi-Agent Foundation** | Supervisor + specialized agents | Multi-Agent |
| **12: Agent Registry** | Add agents without code changes | Extensibility |
| **13: Memory & Context** | Short-term + long-term | Memory |
| **14: Tests** | Unit + integration tests | - |
| **15: Docker/K8s** | Containerization, deployment | - |
| **16: Streaming UI** | Streamlit web app | Final UI |

---

## 🔧 API Reference

### POST /tasks
Create and execute a coding task.

**Request:**
```json
{
  "description": "Write a function to sort a list",
  "context": "def existing_function(): pass"  // optional
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "status": "completed",
  "task_type": "code_generation",
  "generated_code": "def sort_list(lst): ...",
  "evaluation_score": 1.0,
  "evaluation_feedback": "Code is syntactically valid",
  "error_message": null
}
```

### GET /tasks/{task_id}
Get task status and result.

### GET /health/live
Liveness probe for Kubernetes.

### GET /health/ready
Readiness probe for Kubernetes.

### GET /docs
Swagger UI documentation.

---

## 🛠️ Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | xAI Grok | Free tier, OpenAI-compatible API |
| Framework | LangGraph | Explicit workflow, cycles for retry |
| Web Framework | FastAPI | Async, auto-docs, type hints |
| Task Classification | LLM-based | Flexible, handles nuanced requests |
| Code Validation | AST parsing | Fast, safe, no execution needed |
| Logging | Structured with timing | Per-node metrics, bottleneck detection |

---

## 🐛 Known Issues / TODO

### Code Quality (from Claude Code review)
- [ ] P0: Async task queue (currently blocks HTTP request)
- [ ] P0: Redis storage (in-memory lost on restart)
- [ ] P0: LLM error handling (no retries/timeouts)
- [ ] P1: Dependency injection (creates LLM client per request)
- [ ] P1: Use Pydantic Settings for config
- [ ] P1: Add tests
- [ ] P2: Prometheus metrics implementation
- [ ] P2: Fix prompt variable inconsistency (`context` vs `context_section`)

### Features
- [ ] Streaming progress to client (SSE)
- [ ] Iterative code building (context accumulation)
- [ ] Code execution in UI
- [ ] Multi-language support (currently Python only)

---

## 📚 Learning Resources

### Agentic Design Patterns
- [YouTube: Agentic Design Patterns](https://www.youtube.com/watch?v=YlpknqWkbdo)

### Key Concepts
- **LangGraph**: State machine for LLM workflows with cycles
- **Prompt Chaining**: Break complex tasks into subtasks
- **Reflection**: Agent evaluates and improves its own output
- **RAG**: Retrieve relevant context before generation
- **Multi-Agent**: Specialized agents coordinated by supervisor

---

## 🤝 Contributing

This is a learning project. Feel free to fork and experiment!

---

## 📄 License

MIT

---

## 📝 Session Notes

### Last Session: Dec 28, 2025

**Completed:**
- Module 5: Observability with structured logging
- Fixed API key persistence issues
- Verified end-to-end workflow with metrics

**Next Session:**
1. Add streaming (SSE) for real-time client updates
2. Continue with Module 6: Error Handling
3. Build toward the Streamlit UI

**To Resume:**
```bash
cd ~/Workspace/langgraph-agentic-dev-starter
source .venv/bin/activate
cd agent-service
uvicorn app.main:app --reload
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Write a hello world function"}'
```