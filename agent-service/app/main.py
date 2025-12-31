"""
FastAPI Application

Main entry point for the agent service.
"""

from fastapi import FastAPI
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
