# Code Agent Platform

AI-powered code generation platform demonstrating enterprise agentic AI patterns.

## Quick Start
```bash
# Terminal 1: Python agent-service
cd agent-service
source ../.venv/bin/activate
USE_MOCK_LLM=true uvicorn app.main:app --reload

# Terminal 2: Java gateway
cd gateway-service
./mvnw spring-boot:run

# Open http://localhost:8080
```

## Current Architecture
```mermaid
flowchart TB
    Browser[Browser :8080]

    subgraph Gateway["Java Gateway (Spring Boot :8080)"]
        Static[Static Files]
        TaskCtrl[TaskController]
        AuthFilter[AuthFilter - TODO]
        RateFilter[RateLimitFilter - TODO]
    end

    subgraph Agent["Python Agent Service (FastAPI :8000)"]
        Routes["/tasks endpoints"]
        CodeAgent[CodeAgent]
        TaskExec[TaskExecution]
    end

    subgraph LLM["LLM Layer"]
        Factory[get_llm_client]
        Mock[MockLLMClient]
        Grok[GrokClient]
    end

    subgraph Tools["Tools"]
        Syntax[SyntaxChecker]
        Runner[CodeRunner]
    end

    Browser --> Gateway
    Static --> Browser
    TaskCtrl --> Routes
    Routes --> CodeAgent
    CodeAgent --> TaskExec
    CodeAgent --> Factory
    Factory --> Mock
    Factory --> Grok
    CodeAgent --> Syntax
    Routes --> Runner
```

## Request Flow
```mermaid
sequenceDiagram
    participant Browser
    participant Java as Java Gateway :8080
    participant Python as Python :8000
    participant CodeAgent
    participant LLM
    participant AST as AST Parser

    Browser->>Java: GET /
    Java-->>Browser: index.html

    Browser->>Java: POST /api/tasks {description}
    Java->>Python: POST /tasks {description}

    Python->>CodeAgent: initiate_task()

    Note over Browser: SSE Stream Opens

    CodeAgent->>LLM: Classify task
    CodeAgent-->>Browser: SSE: node_start (identify)
    LLM-->>CodeAgent: "code_generation"
    CodeAgent-->>Browser: SSE: node_complete (identify)

    CodeAgent->>LLM: Generate code
    CodeAgent-->>Browser: SSE: node_start (execute)
    LLM-->>CodeAgent: "def hello_world()..."
    CodeAgent-->>Browser: SSE: node_complete (execute)

    CodeAgent->>AST: Validate syntax
    CodeAgent-->>Browser: SSE: node_start (evaluate)
    AST-->>CodeAgent: Valid, score=1.0
    CodeAgent-->>Browser: SSE: node_complete (evaluate)

    CodeAgent-->>Browser: SSE: result {code, status}

    Note over Browser: User clicks Run Code

    Browser->>Java: POST /api/tasks/execute {code}
    Java->>Python: POST /tasks/execute {code}
    Python-->>Java: {output, success}
    Java-->>Browser: {output, success}
```

## CodeAgent Workflow (LangGraph)
```mermaid
stateDiagram-v2
    [*] --> identify
    identify --> execute: task classified
    execute --> evaluate: code generated
    evaluate --> [*]: valid (score >= 0.8)
    evaluate --> execute: invalid (retry, max 3)
```

| Node | Purpose | Tool |
|------|---------|------|
| identify | Classify task type | LLM |
| execute | Generate Python code | LLM |
| evaluate | Validate syntax | AST Parser |

## Key Files

### Java Gateway
| File | Purpose |
|------|---------|
| `GatewayApplication.java` | Spring Boot entry |
| `TaskController.java` | Proxy to Python, SSE streaming |
| `AuthFilter.java` | JWT validation (TODO) |
| `RateLimitFilter.java` | Rate limiting (TODO) |

### Python Agent
| File | Purpose |
|------|---------|
| `routes.py` | POST /tasks, /tasks/execute |
| `code_agent.py` | LangGraph workflow |
| `task_execution.py` | Observable progress, SSE events |
| `grok_client.py` | xAI Grok LLM |
| `mock_client.py` | Mock LLM for testing |
| `logging_utils.py` | Request tracing [req-xxx] |

## Server Logs
```bash
# Python logs
tail -f /tmp/python-server.log

# Java logs
tail -f /tmp/java-server.log

# Filter by request ID
grep "req-abc123" /tmp/python-server.log
```

## Module Status

| Module | Status |
|--------|--------|
| 1-5 Foundation | ✅ |
| 6 SSE Streaming | ✅ |
| 7 Code Execution | ✅ |
| 8 Java Gateway | ✅ |
| 9+ See README | 📋 |
