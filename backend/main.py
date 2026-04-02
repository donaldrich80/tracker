from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from backend.database import create_tables
from backend.api import projects, cards, events, search, webhooks
from backend.ws.router import ws_router
from backend.mcp.server import mcp, mcp_app
from backend.scanner.detector import scan_projects
from backend.database import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        await create_tables()
        async with AsyncSessionLocal() as db:
            await scan_projects(db)
        yield


app = FastAPI(title="Tracker", lifespan=lifespan)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(cards.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(ws_router)
app.mount("/mcp", mcp_app)

FRONTEND_DIST = os.getenv("FRONTEND_DIST", "./frontend/dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="static")
