from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles

router = APIRouter(tags=["Stream Frontend"])

# backend/routers/stream_frontend.py -> backend/static/stream_frontend/
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static" / "stream_frontend"
ASSETS_DIR = FRONTEND_DIR / "assets"

# Serve CSS and JavaScript assets under /stream-ui/assets/...
router.mount(
    "/stream-ui/assets",
    StaticFiles(directory=ASSETS_DIR),
    name="stream-frontend-assets",
)


@router.get("/stream-ui/", include_in_schema=False)
async def telemetry_frontend():
    """Serve the live telemetry dashboard."""
    return FileResponse(FRONTEND_DIR / "index.html", media_type="text/html")


@router.get("/stream-ui/control", include_in_schema=False)
async def stream_control_frontend():
    """Serve the stream control page."""
    return FileResponse(FRONTEND_DIR / "control.html", media_type="text/html")

@router.get("/stream-ui/caller", include_in_schema=False)
async def stream_control_frontend():
    """Serve the stream control page."""
    return FileResponse(FRONTEND_DIR / "caller.html", media_type="text/html")