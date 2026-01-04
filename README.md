# Code Agent Platform

AI-powered code generation platform demonstrating enterprise agentic AI patterns.

## Quick Start
```bash
git clone https://github.com/aregmii/langgraph-agentic-dev-starter.git
cd langgraph-agentic-dev-starter

# Setup Python
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e "./agent-service[dev]"
echo 'XAI_API_KEY=your-key' > .env

# Terminal 1: Start Python
cd agent-service
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Terminal 2: Start Java
cd gateway-service
./mvnw spring-boot:run

# Open http://localhost:8080
```

## Architecture
```mermaid
flowchart TB
    Browser[Browser :8080]

    subgraph Gateway["Java Gateway (Spring Boot)"]
        Static[Static Files]
        Proxy[TaskController]
        Auth[Auth - TODO]
        Rate[RateLimit - TODO]
    end

    subgraph Agent["Python Agent Service (FastAPI)"]
        API[REST API]
        CodeAgent[CodeAgent]
    end

    subgraph LLM["LLM"]
        Mock[Mock - Free]
        Grok[Grok - Real]
    end

    Browser --> Gateway
    Proxy --> API
    CodeAgent --> LLM
```

## Request Flow
```mermaid
sequenceDiagram
    participant Browser
    participant Java as Java :8080
    participant Python as Python :8000
    participant LLM

    Browser->>Java: POST /api/tasks
    Java->>Python: POST /tasks

    loop CodeAgent Workflow
        Python->>LLM: Identify task type
        Python-->>Browser: SSE: identify
        Python->>LLM: Generate code
        Python-->>Browser: SSE: execute
        Python->>Python: Validate (AST)
        Python-->>Browser: SSE: evaluate
    end

    Python-->>Browser: SSE: result
```

## Target Architecture (Multi-Agent)
```mermaid
sequenceDiagram
    participant User
    participant Gateway
    participant Supervisor
    participant Planner
    participant Coder
    participant Validator
    participant DocWriter

    User->>Gateway: "Add sorting with error handling"
    Gateway->>Supervisor: Forward request

    Supervisor->>Planner: Break down task
    Planner-->>Supervisor: [1. Sort, 2. Errors, 3. Tests]

    loop Each step
        Supervisor->>Coder: Generate code
        Supervisor->>Validator: Check syntax
        alt Errors (Reflection)
            Validator-->>Supervisor: Errors
            Supervisor->>Coder: Fix
        end
    end

    Supervisor->>DocWriter: Add documentation
    Supervisor-->>User: Final result (SSE)
```

## Agentic Design Patterns

| Pattern | Implementation | Status |
|---------|----------------|--------|
| **Prompt Chaining** | Identify → Execute → Evaluate | ✅ |
| **Structured Output** | TaskState dataclass | ✅ |
| **Routing** | LLM-based task classification | ✅ |
| **Reflection** | Validator → Coder retry loop | ✅ |
| **Streaming** | SSE real-time events | ✅ |
| **Planning** | Planner Agent | 📋 |
| **Multi-Agent** | Supervisor orchestration | 📋 |
| **Tool Use** | Dynamic tool selection | 📋 |
| **Memory** | Context persistence | 📋 |
| **Guardrails** | Input/output validation | 📋 |

## Module Roadmap

| # | Module | Status | Description |
|---|--------|--------|-------------|
| 1-5 | Foundation | ✅ | Core, Tools, Graph, API, Logging |
| 6 | SSE Streaming | ✅ | Real-time progress events |
| 7 | Code Execution | ✅ | Run generated code in UI |
| 8 | Java Gateway | ✅ | Serve UI, proxy to Python |
| 9 | Auth & Rate Limiting | 📋 | JWT, Bucket4j |
| 10 | Circuit Breaker | 📋 | Resilience4j |
| 11 | Planner Agent | 📋 | Task decomposition |
| 12 | Multi-Agent Supervisor | 📋 | Orchestrate specialists |
| 13 | Memory Store | 📋 | Context persistence |
| 14 | Task Queue | 📋 | Decouple submission from processing |
| 15 | RAG / Doc Agent | 📋 | Documentation lookup |
| 16 | Guardrails | 📋 | Safety validation |
| 17 | Docker / K8s | 📋 | Containerization |

## Future: Task Queue Architecture

To independently scale task submission and worker processing, we plan to explore Redis-based queue patterns:

- **Lists** (LPUSH/BRPOP) - Simple FIFO queue
- **Sorted Sets** (ZADD/ZREM) - Priority-based processing
- **Streams** (XADD/XREAD) - Consumer groups, acknowledgments

This will enable:
- Decoupled scaling (more workers without changing gateway)
- Fault tolerance (tasks persist if workers restart)
- Backpressure handling (queue depth monitoring)

## Project Structure
```
langgraph-agentic-dev-starter/
├── agent-service/           # Python/FastAPI
│   └── app/
│       ├── agents/          # CodeAgent, TaskExecution
│       ├── api/             # Routes, SSE events
│       ├── llm/             # Grok + Mock clients
│       └── tools/           # Syntax checker, code runner
├── gateway-service/         # Java/Spring Boot
│   └── src/main/java/
│       ├── controller/      # TaskController
│       └── filter/          # Auth, RateLimit (TODO)
└── web-ui/                  # Legacy (now in gateway)
```
