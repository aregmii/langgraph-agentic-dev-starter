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


# Serve web-ui (separate module but served by Python for now)
web_ui_path = Path(__file__).parent.parent.parent / "web-ui"
if web_ui_path.exists():
    app.mount("/", StaticFiles(directory=web_ui_path, html=True), name="web-ui")