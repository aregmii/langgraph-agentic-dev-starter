"""
Health Check Endpoints

Used by Kubernetes for liveness and readiness probes.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness():
    """
    Liveness probe - is the service running?
    
    Kubernetes restarts the pod if this fails.
    """
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    """
    Readiness probe - is the service ready to accept traffic?
        
    TODO: Add checks for:
    - Redis connection
    - LLM API reachability
    """
    return {"status": "ready"}