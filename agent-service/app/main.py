"""
FastAPI Application

Main entry point for the agent service.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.api.routes import router as tasks_router
from app.health.health import router as health_router

app = FastAPI(
    title="Code Agent API",
    description="LangGraph-based AI agent for code generation and manipulation",
    version="0.1.0",
)

# Register routers
app.include_router(tasks_router)
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint - basic service info."""
    return {
        "service": "code-agent",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Serve static files (test UI)
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")