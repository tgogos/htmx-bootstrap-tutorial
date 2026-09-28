# Standard library imports
import asyncio
import time

# Third-party imports
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

# Capture the start time of the application
start_time = time.time()

router = APIRouter()


@router.get(
    "/",
    summary="Root redirect",
    response_description="Redirects to the HTMX UI",
    include_in_schema=False,
)
async def root():
    """Send browsers to the primary UI (anonymous users then hit /auth/login)."""
    return RedirectResponse(url="/ui/dashboard", status_code=303)


@router.get(
    "/health",
    summary="Get the service status",
    response_description="Health status...",
)
async def health():
    """
    An easy way to get back information about the status of FastAPI HTMX Starter
    """
    from app.utils.mongo import check_database_connection
    from app.db.connection import check_sqlite_connection

    db_healthy = await check_database_connection()
    sqlite_healthy = await check_sqlite_connection()
    external_service_healthy = await check_external_service()
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)

    health_status = {
        "status": "ok",
        "mongodb_ping": "ok" if db_healthy else "not ok",
        "sqlite_ping": "ok" if sqlite_healthy else "not ok",
        "external_service": "healthy" if external_service_healthy else "unhealthy",
        "uptime_seconds": uptime_seconds,
    }

    if not db_healthy or not sqlite_healthy or not external_service_healthy:
        health_status["status"] = "unhealthy"

    return health_status


async def check_external_service():
    """
    Check the availability of external services.

    Returns:
        bool: True if external service is healthy, False otherwise
    """
    await asyncio.sleep(0.1)  # Simulate a service check delay
    return True
