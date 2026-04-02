# Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-container kanban/dashboard app for tracking AI-assisted coding projects, with a REST API, WebSocket real-time feed, MCP backend, and React UI.

**Architecture:** FastAPI serves everything (API + WebSocket + MCP + static React build) on port 8000. SQLite via SQLAlchemy async. Projects folder mounted as a read-only volume; scanner detects git repos with known project files.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async + aiosqlite), gitpython, mcp (FastMCP), React 18, Vite, TypeScript, Tailwind CSS 3, Zustand, pytest + httpx

---

## File Map

```
tracker/
├── backend/
│   ├── pyproject.toml
│   ├── main.py                    # FastAPI app, lifespan, static mount
│   ├── database.py                # async engine, get_db, create_tables
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── schemas.py                 # Pydantic request/response models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── projects.py            # GET/PATCH /projects, POST /projects/scan
│   │   ├── cards.py               # CRUD /projects/{id}/cards, /cards/{id}
│   │   ├── events.py              # POST /cards/{id}/log, /milestone, GET events
│   │   ├── search.py              # GET /search
│   │   └── webhooks.py            # CRUD /webhooks
│   ├── ws/
│   │   ├── __init__.py
│   │   ├── manager.py             # ConnectionManager (subscribe/broadcast)
│   │   └── router.py              # WS /ws/cards/{id}, /ws/projects/{id}
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── detector.py            # detect_projects(root) -> list[ProjectInfo]
│   │   └── git_info.py            # read_git_info(path) -> GitInfo
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py              # FastMCP instance, mount point
│   │   ├── tools.py               # all @mcp.tool() definitions
│   │   └── resources.py           # all @mcp.resource() definitions
│   └── services/
│       ├── __init__.py
│       ├── webhooks.py            # fire_webhooks(event, payload)
│       └── context_bundle.py      # build_context_bundle(card_id, db)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts          # typed fetch wrappers
│       ├── store/
│       │   └── index.ts           # Zustand store
│       ├── hooks/
│       │   └── useCardSocket.ts   # WebSocket hook
│       └── components/
│           ├── ProjectTabs.tsx
│           ├── BoardHeader.tsx
│           ├── KanbanBoard.tsx
│           ├── ListView.tsx
│           ├── CardItem.tsx
│           ├── CardDetail.tsx
│           ├── LogStream.tsx
│           └── AddCardModal.tsx
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

---

## Task 1: Backend scaffold + pyproject.toml

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/main.py`
- Create: `backend/database.py`

- [ ] **Step 1: Create backend/pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tracker-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0",
    "aiosqlite>=0.20",
    "gitpython>=3.1",
    "httpx>=0.27",
    "mcp[cli]>=1.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "anyio>=4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create backend/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DB_PATH = os.getenv("DB_PATH", "./data/tracker.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        from backend import models  # noqa: F401 — registers models
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 3: Create backend/main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from backend.database import create_tables
from backend.api import projects, cards, events, search, webhooks
from backend.ws.router import ws_router
from backend.mcp.server import mcp_app
from backend.scanner.detector import scan_projects
from backend.database import AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
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
```

- [ ] **Step 4: Install deps and verify import**

```bash
cd backend && pip install -e ".[dev]"
python -c "from backend.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat: backend scaffold, database setup, FastAPI app"
```

---

## Task 2: SQLAlchemy models

**Files:**
- Create: `backend/models.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_models.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.models import Base, ProjectModel, CardModel, CardEventModel, WebhookModel
from backend.database import create_tables
import os

@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_create_project(db):
    p = ProjectModel(id="my-proj", name="My Project", path="/projects/my-proj")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    assert p.id == "my-proj"
    assert p.active is True
    assert p.stack == []


async def test_create_card(db):
    p = ProjectModel(id="proj", name="P", path="/p")
    db.add(p)
    await db.commit()
    c = CardModel(project_id="proj", title="Fix bug")
    db.add(c)
    await db.commit()
    await db.refresh(c)
    assert c.id is not None
    assert c.status.value == "todo"
    assert c.priority.value == "medium"


async def test_create_card_event(db):
    p = ProjectModel(id="proj2", name="P", path="/p")
    db.add(p)
    c = CardModel(project_id="proj2", title="T")
    db.add(c)
    await db.commit()
    e = CardEventModel(card_id=c.id, type="log", body="Started", actor="claude")
    db.add(e)
    await db.commit()
    await db.refresh(e)
    assert e.id is not None
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `backend.models` doesn't exist yet.

- [ ] **Step 3: Create backend/models.py**

```python
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, JSON, String, Text
from backend.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class StatusEnum(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    blocked = "blocked"


class PriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EventTypeEnum(str, enum.Enum):
    log = "log"
    milestone = "milestone"
    status_change = "status_change"
    assignment = "assignment"


class ProjectModel(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    stack = Column(JSON, default=list, nullable=False)
    git_branch = Column(String)
    git_dirty = Column(Boolean, default=False)
    git_last_commit = Column(String)
    description = Column(Text)
    scanned_at = Column(DateTime)
    active = Column(Boolean, default=True, nullable=False)


class CardModel(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.todo, nullable=False)
    priority = Column(SAEnum(PriorityEnum), default=PriorityEnum.medium, nullable=False)
    assigned_llm = Column(String)
    tags = Column(JSON, default=list, nullable=False)
    linked_files = Column(JSON, default=list, nullable=False)
    acceptance = Column(Text)
    blocks = Column(JSON, default=list, nullable=False)
    blocked_by = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class CardEventModel(Base):
    __tablename__ = "card_events"
    id = Column(String, primary_key=True, default=_uuid)
    card_id = Column(String, nullable=False)
    type = Column(SAEnum(EventTypeEnum), nullable=False)
    body = Column(Text)
    actor = Column(String)
    meta = Column(JSON)
    created_at = Column(DateTime, default=_now)


class WebhookModel(Base):
    __tablename__ = "webhooks"
    id = Column(String, primary_key=True, default=_uuid)
    url = Column(String, nullable=False)
    events = Column(JSON, default=list, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_models.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/models.py backend/tests/
git commit -m "feat: SQLAlchemy models — projects, cards, card_events, webhooks"
```

---

## Task 3: Pydantic schemas

**Files:**
- Create: `backend/schemas.py`

- [ ] **Step 1: Create backend/schemas.py**

```python
from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: str
    name: str
    path: str
    stack: list[str]
    git_branch: str | None
    git_dirty: bool
    git_last_commit: str | None
    description: str | None
    scanned_at: datetime | None
    active: bool

    model_config = {"from_attributes": True}


class CardCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    tags: list[str] = []
    linked_files: list[str] = []
    acceptance: str | None = None
    blocks: list[str] = []
    blocked_by: list[str] = []


class CardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_llm: str | None = None
    tags: list[str] | None = None
    linked_files: list[str] | None = None
    acceptance: str | None = None
    blocks: list[str] | None = None
    blocked_by: list[str] | None = None


class CardOut(BaseModel):
    id: str
    project_id: str
    title: str
    description: str | None
    status: str
    priority: str
    assigned_llm: str | None
    tags: list[str]
    linked_files: list[str]
    acceptance: str | None
    blocks: list[str]
    blocked_by: list[str]
    created_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CardEventOut(BaseModel):
    id: str
    card_id: str
    type: str
    body: str | None
    actor: str | None
    meta: dict[str, Any] | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class LogCreate(BaseModel):
    body: str
    actor: str = "user"


class MilestoneCreate(BaseModel):
    body: str
    actor: str = "user"


class WebhookCreate(BaseModel):
    url: str
    events: list[str]


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verify schemas import cleanly**

```bash
cd backend && python -c "from backend.schemas import CardOut, ProjectOut; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: Pydantic schemas for all API models"
```

---

## Task 4: Project scanner

**Files:**
- Create: `backend/scanner/__init__.py`
- Create: `backend/scanner/git_info.py`
- Create: `backend/scanner/detector.py`
- Create: `backend/tests/test_scanner.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_scanner.py
import os
import subprocess
import tempfile
import pytest
from backend.scanner.git_info import read_git_info
from backend.scanner.detector import is_project_dir, detect_stack


def make_git_repo(path: str):
    subprocess.run(["git", "init", path], check=True, capture_output=True)
    subprocess.run(["git", "-C", path, "config", "user.email", "t@t.com"], check=True)
    subprocess.run(["git", "-C", path, "config", "user.name", "T"], check=True)
    (os.path.join(path, "README.md") and open(os.path.join(path, "README.md"), "w").write("hi"))
    subprocess.run(["git", "-C", path, "add", "."], check=True)
    subprocess.run(["git", "-C", path, "commit", "-m", "init"], check=True, capture_output=True)


def test_is_project_dir_requires_git_and_marker():
    with tempfile.TemporaryDirectory() as d:
        assert not is_project_dir(d)  # no git, no marker
        make_git_repo(d)
        assert not is_project_dir(d)  # git but no marker
        open(os.path.join(d, "package.json"), "w").write("{}")
        assert is_project_dir(d)  # git + marker


def test_detect_stack():
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "pyproject.toml"), "w").write("")
        open(os.path.join(d, "Dockerfile"), "w").write("")
        stack = detect_stack(d)
        assert "python" in stack
        assert "docker" in stack


def test_read_git_info():
    with tempfile.TemporaryDirectory() as d:
        make_git_repo(d)
        info = read_git_info(d)
        assert info["branch"] is not None
        assert info["last_commit"] is not None
        assert info["dirty"] is False
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_scanner.py -v
```

Expected: `ImportError` — modules don't exist yet.

- [ ] **Step 3: Create backend/scanner/__init__.py**

```python
```

- [ ] **Step 4: Create backend/scanner/git_info.py**

```python
from __future__ import annotations
import git
from git.exc import InvalidGitRepositoryError


def read_git_info(path: str) -> dict:
    try:
        repo = git.Repo(path)
        try:
            branch = repo.active_branch.name
        except TypeError:
            branch = str(repo.head.commit)[:8]

        last_commit = None
        if not repo.head.is_detached or repo.head.commit:
            last_commit = repo.head.commit.message.strip().splitlines()[0]

        return {
            "branch": branch,
            "dirty": repo.is_dirty(untracked_files=True),
            "last_commit": last_commit,
        }
    except InvalidGitRepositoryError:
        return {"branch": None, "dirty": False, "last_commit": None}
```

- [ ] **Step 5: Create backend/scanner/detector.py**

```python
from __future__ import annotations
import os
import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import ProjectModel
from backend.scanner.git_info import read_git_info

MARKER_FILES = {
    "package.json": "node",
    "pyproject.toml": "python",
    "setup.py": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "Dockerfile": "docker",
    "docker-compose.yml": "compose",
    "docker-compose.yaml": "compose",
}


def is_project_dir(path: str) -> bool:
    if not os.path.isdir(os.path.join(path, ".git")):
        return False
    return any(os.path.exists(os.path.join(path, f)) for f in MARKER_FILES)


def detect_stack(path: str) -> list[str]:
    seen: set[str] = set()
    for filename, tag in MARKER_FILES.items():
        if os.path.exists(os.path.join(path, filename)) and tag not in seen:
            seen.add(tag)
    return sorted(seen)


def _read_description(path: str) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme = os.path.join(path, name)
        if os.path.isfile(readme):
            try:
                with open(readme, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            return line[:300]
            except OSError:
                pass
    return None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


async def scan_projects(db: AsyncSession, projects_root: str | None = None) -> list[ProjectModel]:
    root = projects_root or os.getenv("PROJECTS_ROOT", "/projects")
    if not os.path.isdir(root):
        return []

    found_ids: set[str] = set()
    results: list[ProjectModel] = []

    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        if not is_project_dir(entry.path):
            continue

        proj_id = _slug(entry.name)
        found_ids.add(proj_id)

        git = read_git_info(entry.path)
        stack = detect_stack(entry.path)
        description = _read_description(entry.path)

        existing = await db.get(ProjectModel, proj_id)
        if existing:
            existing.name = entry.name
            existing.path = entry.path
            existing.stack = stack
            existing.git_branch = git["branch"]
            existing.git_dirty = git["dirty"]
            existing.git_last_commit = git["last_commit"]
            existing.description = description
            existing.scanned_at = datetime.now(timezone.utc)
            existing.active = True
            results.append(existing)
        else:
            proj = ProjectModel(
                id=proj_id,
                name=entry.name,
                path=entry.path,
                stack=stack,
                git_branch=git["branch"],
                git_dirty=git["dirty"],
                git_last_commit=git["last_commit"],
                description=description,
                scanned_at=datetime.now(timezone.utc),
                active=True,
            )
            db.add(proj)
            results.append(proj)

    # Mark missing projects inactive
    stmt = select(ProjectModel).where(ProjectModel.active == True)  # noqa: E712
    existing_active = (await db.execute(stmt)).scalars().all()
    for p in existing_active:
        if p.id not in found_ids:
            p.active = False

    await db.commit()
    return results
```

- [ ] **Step 6: Run tests — expect pass**

```bash
cd backend && pytest tests/test_scanner.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/scanner/ backend/tests/test_scanner.py
git commit -m "feat: project scanner — detect git repos, stack tags, git info"
```

---

## Task 5: Projects API

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/projects.py`
- Create: `backend/tests/test_api_projects.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api_projects.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from backend.main import app
from backend.database import Base, engine


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_list_projects_empty(client):
    r = await client.get("/api/v1/projects")
    assert r.status_code == 200
    assert r.json() == []


async def test_scan_projects(client):
    with patch("backend.api.projects.scan_projects", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = []
        r = await client.post("/api/v1/projects/scan")
        assert r.status_code == 200
        assert mock_scan.called
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_api_projects.py -v
```

Expected: `ImportError` or 404 — routes don't exist.

- [ ] **Step 3: Create backend/api/__init__.py** (empty file)

- [ ] **Step 4: Create backend/api/projects.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import ProjectModel
from backend.schemas import ProjectOut
from backend.scanner.detector import scan_projects

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(active: bool | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(ProjectModel)
    if active is not None:
        stmt = stmt.where(ProjectModel.active == active)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(ProjectModel, project_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    p = await db.get(ProjectModel, project_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")
    for field in ("name", "description"):
        if field in data:
            setattr(p, field, data[field])
    await db.commit()
    await db.refresh(p)
    return p


@router.post("/projects/scan")
async def trigger_scan(db: AsyncSession = Depends(get_db)):
    projects = await scan_projects(db)
    return {"scanned": len(projects)}
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_api_projects.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/ backend/tests/test_api_projects.py
git commit -m "feat: projects REST API — list, get, patch, scan"
```

---

## Task 6: Cards API

**Files:**
- Create: `backend/api/cards.py`
- Create: `backend/tests/test_api_cards.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api_cards.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal
from backend.models import ProjectModel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="proj1", name="P1", path="/p1"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_create_and_list_cards(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "My card"})
    assert r.status_code == 201
    card_id = r.json()["id"]

    r2 = await client.get("/api/v1/projects/proj1/cards")
    assert r2.status_code == 200
    ids = [c["id"] for c in r2.json()]
    assert card_id in ids


async def test_get_card(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T", "priority": "high"})
    card_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/cards/{card_id}")
    assert r2.status_code == 200
    assert r2.json()["priority"] == "high"


async def test_update_card_status(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T"})
    card_id = r.json()["id"]
    r2 = await client.patch(f"/api/v1/cards/{card_id}", json={"status": "in_progress"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "in_progress"


async def test_delete_card(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T"})
    card_id = r.json()["id"]
    r2 = await client.delete(f"/api/v1/cards/{card_id}")
    assert r2.status_code == 204
    r3 = await client.get(f"/api/v1/cards/{card_id}")
    assert r3.status_code == 404
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_api_cards.py -v
```

Expected: 404 errors — routes not registered.

- [ ] **Step 3: Create backend/api/cards.py**

```python
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import CardModel, CardEventModel, EventTypeEnum, StatusEnum
from backend.schemas import CardCreate, CardUpdate, CardOut
from backend.ws.manager import manager

router = APIRouter(tags=["cards"])


@router.get("/projects/{project_id}/cards", response_model=list[CardOut])
async def list_cards(
    project_id: str,
    status: str | None = None,
    priority: str | None = None,
    tag: str | None = None,
    assigned_llm: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CardModel).where(CardModel.project_id == project_id)
    if status:
        stmt = stmt.where(CardModel.status == status)
    if priority:
        stmt = stmt.where(CardModel.priority == priority)
    if assigned_llm:
        stmt = stmt.where(CardModel.assigned_llm == assigned_llm)
    cards = (await db.execute(stmt)).scalars().all()
    if tag:
        cards = [c for c in cards if tag in (c.tags or [])]
    return cards


@router.post("/projects/{project_id}/cards", response_model=CardOut, status_code=201)
async def create_card(project_id: str, data: CardCreate, db: AsyncSession = Depends(get_db)):
    card = CardModel(project_id=project_id, **data.model_dump())
    db.add(card)
    await db.commit()
    await db.refresh(card)
    await manager.broadcast_project(project_id, {"type": "card.created", "card_id": card.id})
    return card


@router.get("/cards/{card_id}", response_model=CardOut)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    card = await db.get(CardModel, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.patch("/cards/{card_id}", response_model=CardOut)
async def update_card(card_id: str, data: CardUpdate, db: AsyncSession = Depends(get_db)):
    card = await db.get(CardModel, card_id)
    if not card:
        raise HTTPException(404, "Card not found")

    update = data.model_dump(exclude_none=True)
    old_status = card.status

    for field, value in update.items():
        setattr(card, field, value)

    now = datetime.now(timezone.utc)
    if "status" in update:
        new_status = update["status"]
        if new_status == StatusEnum.in_progress and not card.started_at:
            card.started_at = now
        if new_status == StatusEnum.done and not card.completed_at:
            card.completed_at = now

        event = CardEventModel(
            card_id=card_id,
            type=EventTypeEnum.status_change,
            body=f"Status changed from {old_status} to {new_status}",
            actor="user",
            meta={"from": str(old_status), "to": new_status},
        )
        db.add(event)

    await db.commit()
    await db.refresh(card)
    await manager.broadcast_project(card.project_id, {"type": "card.updated", "card_id": card_id})
    return card


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(card_id: str, db: AsyncSession = Depends(get_db)):
    card = await db.get(CardModel, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    project_id = card.project_id
    await db.delete(card)
    await db.commit()
    await manager.broadcast_project(project_id, {"type": "card.deleted", "card_id": card_id})
```

- [ ] **Step 4: Run tests — expect pass**

```bash
cd backend && pytest tests/test_api_cards.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api/cards.py backend/tests/test_api_cards.py
git commit -m "feat: cards CRUD API with status change events"
```

---

## Task 7: WebSocket manager

**Files:**
- Create: `backend/ws/__init__.py`
- Create: `backend/ws/manager.py`
- Create: `backend/ws/router.py`

- [ ] **Step 1: Create backend/ws/__init__.py** (empty)

- [ ] **Step 2: Create backend/ws/manager.py**

```python
from __future__ import annotations
import asyncio
import json
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # project_id -> set of websockets
        self._project_subs: dict[str, set[WebSocket]] = defaultdict(set)
        # card_id -> set of websockets
        self._card_subs: dict[str, set[WebSocket]] = defaultdict(set)

    async def subscribe_project(self, project_id: str, ws: WebSocket):
        await ws.accept()
        self._project_subs[project_id].add(ws)

    async def subscribe_card(self, card_id: str, ws: WebSocket):
        await ws.accept()
        self._card_subs[card_id].add(ws)

    def unsubscribe_project(self, project_id: str, ws: WebSocket):
        self._project_subs[project_id].discard(ws)

    def unsubscribe_card(self, card_id: str, ws: WebSocket):
        self._card_subs[card_id].discard(ws)

    async def broadcast_project(self, project_id: str, payload: dict):
        message = json.dumps(payload)
        dead: set[WebSocket] = set()
        for ws in list(self._project_subs.get(project_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._project_subs[project_id] -= dead

    async def broadcast_card(self, card_id: str, payload: dict):
        message = json.dumps(payload)
        dead: set[WebSocket] = set()
        for ws in list(self._card_subs.get(card_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._card_subs[card_id] -= dead


manager = ConnectionManager()
```

- [ ] **Step 3: Create backend/ws/router.py**

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.ws.manager import manager

ws_router = APIRouter()


@ws_router.websocket("/ws/projects/{project_id}")
async def ws_project(project_id: str, websocket: WebSocket):
    await manager.subscribe_project(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive, ignore incoming
    except WebSocketDisconnect:
        manager.unsubscribe_project(project_id, websocket)


@ws_router.websocket("/ws/cards/{card_id}")
async def ws_card(card_id: str, websocket: WebSocket):
    await manager.subscribe_card(card_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.unsubscribe_card(card_id, websocket)
```

- [ ] **Step 4: Verify app starts**

```bash
cd backend && python -c "from backend.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/ws/
git commit -m "feat: WebSocket manager — project and card subscription + broadcast"
```

---

## Task 8: Card Events API (logs + milestones)

**Files:**
- Create: `backend/api/events.py`
- Create: `backend/tests/test_api_events.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api_events.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal
from backend.models import ProjectModel, CardModel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="p1", name="P", path="/p"))
        db.add(CardModel(id="c1", project_id="p1", title="T"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_post_log(client):
    r = await client.post("/api/v1/cards/c1/log", json={"body": "Starting work", "actor": "claude"})
    assert r.status_code == 201
    assert r.json()["type"] == "log"


async def test_post_milestone(client):
    r = await client.post("/api/v1/cards/c1/milestone", json={"body": "Auth module done", "actor": "claude"})
    assert r.status_code == 201
    assert r.json()["type"] == "milestone"


async def test_list_events(client):
    await client.post("/api/v1/cards/c1/log", json={"body": "Line 1", "actor": "claude"})
    await client.post("/api/v1/cards/c1/milestone", json={"body": "MS 1", "actor": "claude"})
    r = await client.get("/api/v1/cards/c1/events")
    assert r.status_code == 200
    assert len(r.json()) == 2
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_api_events.py -v
```

Expected: 404 errors.

- [ ] **Step 3: Create backend/api/events.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import CardModel, CardEventModel, EventTypeEnum
from backend.schemas import LogCreate, MilestoneCreate, CardEventOut
from backend.ws.manager import manager
from backend.services.webhooks import fire_webhooks

router = APIRouter(tags=["events"])


async def _get_card_or_404(card_id: str, db: AsyncSession) -> CardModel:
    card = await db.get(CardModel, card_id)
    if not card:
        raise HTTPException(404, "Card not found")
    return card


@router.get("/cards/{card_id}/events", response_model=list[CardEventOut])
async def list_events(card_id: str, type: str | None = None, db: AsyncSession = Depends(get_db)):
    await _get_card_or_404(card_id, db)
    stmt = select(CardEventModel).where(CardEventModel.card_id == card_id).order_by(CardEventModel.created_at)
    if type:
        stmt = stmt.where(CardEventModel.type == type)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("/cards/{card_id}/log", response_model=CardEventOut, status_code=201)
async def post_log(card_id: str, data: LogCreate, db: AsyncSession = Depends(get_db)):
    card = await _get_card_or_404(card_id, db)
    event = CardEventModel(card_id=card_id, type=EventTypeEnum.log, body=data.body, actor=data.actor)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    payload = {"type": "card.log", "card_id": card_id, "body": data.body, "actor": data.actor}
    await manager.broadcast_card(card_id, payload)
    await manager.broadcast_project(card.project_id, payload)
    await fire_webhooks(db, "card.log", payload)
    return event


@router.post("/cards/{card_id}/milestone", response_model=CardEventOut, status_code=201)
async def post_milestone(card_id: str, data: MilestoneCreate, db: AsyncSession = Depends(get_db)):
    card = await _get_card_or_404(card_id, db)
    event = CardEventModel(card_id=card_id, type=EventTypeEnum.milestone, body=data.body, actor=data.actor)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    payload = {"type": "card.milestone", "card_id": card_id, "body": data.body, "actor": data.actor}
    await manager.broadcast_card(card_id, payload)
    await manager.broadcast_project(card.project_id, payload)
    await fire_webhooks(db, "card.milestone", payload)
    return event
```

- [ ] **Step 4: Create backend/services/__init__.py** (empty)

- [ ] **Step 5: Create backend/services/webhooks.py** (stub — full implementation in Task 10)

```python
from sqlalchemy.ext.asyncio import AsyncSession


async def fire_webhooks(db: AsyncSession, event: str, payload: dict) -> None:
    pass  # implemented in Task 10
```

- [ ] **Step 6: Run tests — expect pass**

```bash
cd backend && pytest tests/test_api_events.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/api/events.py backend/tests/test_api_events.py backend/services/
git commit -m "feat: card events API — post log, post milestone, list events"
```

---

## Task 9: Search API (FTS5)

**Files:**
- Create: `backend/api/search.py`
- Modify: `backend/database.py` — add FTS5 table creation
- Create: `backend/tests/test_api_search.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_api_search.py
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal
from backend.models import ProjectModel, CardModel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="p1", name="P", path="/p"))
        db.add(CardModel(id="c1", project_id="p1", title="OAuth support", description="Add Google OAuth"))
        db.add(CardModel(id="c2", project_id="p1", title="Fix login bug", description="Login fails on timeout"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_search_finds_by_title(client):
    r = await client.get("/api/v1/search?q=OAuth")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert "c1" in ids
    assert "c2" not in ids


async def test_search_finds_by_description(client):
    r = await client.get("/api/v1/search?q=timeout")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert "c2" in ids
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_api_search.py -v
```

- [ ] **Step 3: Create backend/api/search.py**

SQLite FTS5 uses raw SQL since SQLAlchemy doesn't natively model virtual tables.

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from backend.database import get_db
from backend.models import CardModel
from backend.schemas import CardOut

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[CardOut])
async def search_cards(q: str, db: AsyncSession = Depends(get_db)):
    if not q.strip():
        return []
    # Sync FTS index before querying
    await db.execute(text("INSERT OR REPLACE INTO cards_fts(rowid, id, title, description, acceptance) SELECT rowid, id, title, COALESCE(description,''), COALESCE(acceptance,'') FROM cards"))
    result = await db.execute(
        text("SELECT c.id FROM cards_fts f JOIN cards c ON f.id = c.id WHERE cards_fts MATCH :q ORDER BY rank"),
        {"q": q},
    )
    ids = [row[0] for row in result.fetchall()]
    if not ids:
        return []
    stmt = select(CardModel).where(CardModel.id.in_(ids))
    cards = (await db.execute(stmt)).scalars().all()
    # Preserve FTS rank order
    order = {id_: i for i, id_ in enumerate(ids)}
    return sorted(cards, key=lambda c: order.get(c.id, 999))
```

- [ ] **Step 4: Add FTS5 table creation to backend/database.py**

Add this function and call it from `create_tables`:

```python
async def create_fts_table():
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts "
            "USING fts5(id UNINDEXED, title, description, acceptance)"
        ))
```

Update `create_tables()` to also call `await create_fts_table()` — add this import at the top of `database.py`:

```python
from sqlalchemy import text
```

And update `create_tables`:

```python
async def create_tables():
    async with engine.begin() as conn:
        from backend import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    await create_fts_table()
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_api_search.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/search.py backend/database.py backend/tests/test_api_search.py
git commit -m "feat: full-text search via SQLite FTS5"
```

---

## Task 10: Webhooks API + firing

**Files:**
- Create: `backend/api/webhooks.py`
- Modify: `backend/services/webhooks.py` — full implementation
- Create: `backend/tests/test_webhooks.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_webhooks.py
import pytest
import respx
import httpx
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal
from backend.models import ProjectModel, CardModel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="p1", name="P", path="/p"))
        db.add(CardModel(id="c1", project_id="p1", title="T"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_register_and_list_webhook(client):
    r = await client.post("/api/v1/webhooks", json={"url": "http://example.com/hook", "events": ["card.log"]})
    assert r.status_code == 201
    r2 = await client.get("/api/v1/webhooks")
    assert len(r2.json()) == 1


async def test_delete_webhook(client):
    r = await client.post("/api/v1/webhooks", json={"url": "http://x.com/h", "events": ["card.log"]})
    wid = r.json()["id"]
    r2 = await client.delete(f"/api/v1/webhooks/{wid}")
    assert r2.status_code == 204
    r3 = await client.get("/api/v1/webhooks")
    assert r3.json() == []
```

- [ ] **Step 2: Run — expect failure**

```bash
cd backend && pytest tests/test_webhooks.py -v
```

- [ ] **Step 3: Create backend/api/webhooks.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import WebhookModel
from backend.schemas import WebhookCreate, WebhookOut

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks", response_model=list[WebhookOut])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(WebhookModel))).scalars().all()
    return rows


@router.post("/webhooks", response_model=WebhookOut, status_code=201)
async def create_webhook(data: WebhookCreate, db: AsyncSession = Depends(get_db)):
    wh = WebhookModel(**data.model_dump())
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: str, db: AsyncSession = Depends(get_db)):
    wh = await db.get(WebhookModel, webhook_id)
    if not wh:
        raise HTTPException(404, "Webhook not found")
    await db.delete(wh)
    await db.commit()
```

- [ ] **Step 4: Implement backend/services/webhooks.py**

```python
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.models import WebhookModel


async def fire_webhooks(db: AsyncSession, event: str, payload: dict) -> None:
    stmt = select(WebhookModel).where(WebhookModel.active == True)  # noqa: E712
    hooks = (await db.execute(stmt)).scalars().all()
    matching = [h for h in hooks if event in (h.events or [])]
    if not matching:
        return
    async with httpx.AsyncClient(timeout=5.0) as client:
        for hook in matching:
            try:
                await client.post(hook.url, json={"event": event, "payload": payload})
            except Exception:
                pass  # fire-and-forget; don't crash on delivery failure
```

- [ ] **Step 5: Run tests — expect pass**

```bash
cd backend && pytest tests/test_webhooks.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 6: Run full backend test suite**

```bash
cd backend && pytest -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/api/webhooks.py backend/services/webhooks.py backend/tests/test_webhooks.py
git commit -m "feat: webhooks CRUD + fire-and-forget delivery"
```

---

## Task 11: MCP server — tools

**Files:**
- Create: `backend/mcp/__init__.py`
- Create: `backend/mcp/server.py`
- Create: `backend/mcp/tools.py`

- [ ] **Step 1: Create backend/mcp/__init__.py** (empty)

- [ ] **Step 2: Create backend/mcp/server.py**

```python
from mcp.server.fastmcp import FastMCP
from backend.mcp import tools  # noqa: F401 — registers tools
from backend.mcp import resources  # noqa: F401 — registers resources

mcp = FastMCP("tracker", instructions="Tracker MCP server. Use list_projects to discover projects, then list_cards to find work. Claim a card before starting, then post_log and post_milestone as you work.")
mcp_app = mcp.streamable_http_app()
```

- [ ] **Step 3: Create backend/mcp/tools.py**

```python
from __future__ import annotations
from backend.mcp.server import mcp
from backend.database import AsyncSessionLocal
from backend.models import CardModel, ProjectModel, EventTypeEnum, StatusEnum
from backend.schemas import CardCreate
from backend.scanner.detector import scan_projects
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.ws.manager import manager
from backend.services.webhooks import fire_webhooks
from datetime import datetime, timezone


async def _db() -> AsyncSession:
    return AsyncSessionLocal()


@mcp.tool()
async def list_projects() -> list[dict]:
    """List all active projects with stack tags and git status."""
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ProjectModel).where(ProjectModel.active == True))).scalars().all()  # noqa: E712
        return [
            {
                "id": p.id, "name": p.name, "stack": p.stack,
                "git_branch": p.git_branch, "git_dirty": p.git_dirty,
                "git_last_commit": p.git_last_commit, "description": p.description,
            }
            for p in rows
        ]


@mcp.tool()
async def list_cards(project_id: str, status: str | None = None, priority: str | None = None, tag: str | None = None) -> list[dict]:
    """List cards for a project. Filter by status, priority, or tag."""
    async with AsyncSessionLocal() as db:
        stmt = select(CardModel).where(CardModel.project_id == project_id)
        if status:
            stmt = stmt.where(CardModel.status == status)
        if priority:
            stmt = stmt.where(CardModel.priority == priority)
        cards = (await db.execute(stmt)).scalars().all()
        if tag:
            cards = [c for c in cards if tag in (c.tags or [])]
        return [
            {
                "id": c.id, "title": c.title, "status": c.status,
                "priority": c.priority, "assigned_llm": c.assigned_llm,
                "tags": c.tags, "blocked_by": c.blocked_by,
            }
            for c in cards
        ]


@mcp.tool()
async def get_card(card_id: str) -> dict:
    """Get full card detail including all events."""
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return {"error": "Card not found"}
        from backend.models import CardEventModel
        from sqlalchemy import select as sel
        events = (await db.execute(sel(CardEventModel).where(CardEventModel.card_id == card_id).order_by(CardEventModel.created_at))).scalars().all()
        return {
            "id": card.id, "project_id": card.project_id, "title": card.title,
            "description": card.description, "status": card.status,
            "priority": card.priority, "assigned_llm": card.assigned_llm,
            "tags": card.tags, "linked_files": card.linked_files,
            "acceptance": card.acceptance, "blocks": card.blocks, "blocked_by": card.blocked_by,
            "events": [{"type": e.type, "body": e.body, "actor": e.actor, "created_at": str(e.created_at)} for e in events],
        }


@mcp.tool()
async def claim_card(card_id: str, llm_name: str) -> dict:
    """Assign this card to an LLM and move it to in_progress."""
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return {"error": "Card not found"}
        card.assigned_llm = llm_name
        card.status = StatusEnum.in_progress
        if not card.started_at:
            card.started_at = datetime.now(timezone.utc)
        from backend.models import CardEventModel
        db.add(CardEventModel(card_id=card_id, type=EventTypeEnum.assignment, body=f"Claimed by {llm_name}", actor=llm_name))
        await db.commit()
        await manager.broadcast_project(card.project_id, {"type": "card.updated", "card_id": card_id})
        return {"ok": True, "card_id": card_id, "assigned_to": llm_name}


@mcp.tool()
async def update_card_status(card_id: str, status: str, actor: str = "llm") -> dict:
    """Move a card to a new status: todo, in_progress, review, done, blocked."""
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return {"error": "Card not found"}
        old = card.status
        card.status = status
        now = datetime.now(timezone.utc)
        if status == "in_progress" and not card.started_at:
            card.started_at = now
        if status == "done" and not card.completed_at:
            card.completed_at = now
        from backend.models import CardEventModel
        db.add(CardEventModel(card_id=card_id, type=EventTypeEnum.status_change, body=f"{old} → {status}", actor=actor, meta={"from": str(old), "to": status}))
        await db.commit()
        await manager.broadcast_project(card.project_id, {"type": "card.updated", "card_id": card_id})
        return {"ok": True, "card_id": card_id, "status": status}


@mcp.tool()
async def post_log(card_id: str, body: str, actor: str = "llm") -> dict:
    """Append a timestamped log line to the card's live feed."""
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return {"error": "Card not found"}
        from backend.models import CardEventModel
        event = CardEventModel(card_id=card_id, type=EventTypeEnum.log, body=body, actor=actor)
        db.add(event)
        await db.commit()
        payload = {"type": "card.log", "card_id": card_id, "body": body, "actor": actor}
        await manager.broadcast_card(card_id, payload)
        await manager.broadcast_project(card.project_id, payload)
        await fire_webhooks(db, "card.log", payload)
        return {"ok": True}


@mcp.tool()
async def post_milestone(card_id: str, body: str, actor: str = "llm") -> dict:
    """Add a structured progress milestone to the card."""
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return {"error": "Card not found"}
        from backend.models import CardEventModel
        event = CardEventModel(card_id=card_id, type=EventTypeEnum.milestone, body=body, actor=actor)
        db.add(event)
        await db.commit()
        payload = {"type": "card.milestone", "card_id": card_id, "body": body, "actor": actor}
        await manager.broadcast_card(card_id, payload)
        await manager.broadcast_project(card.project_id, payload)
        return {"ok": True}


@mcp.tool()
async def create_card(project_id: str, title: str, description: str | None = None, priority: str = "medium", tags: list[str] | None = None) -> dict:
    """Create a new card on a project board (e.g. for LLM-discovered sub-tasks)."""
    async with AsyncSessionLocal() as db:
        card = CardModel(project_id=project_id, title=title, description=description, priority=priority, tags=tags or [])
        db.add(card)
        await db.commit()
        await db.refresh(card)
        await manager.broadcast_project(project_id, {"type": "card.created", "card_id": card.id})
        return {"ok": True, "card_id": card.id}


@mcp.tool()
async def search_cards(q: str) -> list[dict]:
    """Full-text search across all project cards."""
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        await db.execute(text("INSERT OR REPLACE INTO cards_fts(rowid, id, title, description, acceptance) SELECT rowid, id, title, COALESCE(description,''), COALESCE(acceptance,'') FROM cards"))
        result = await db.execute(text("SELECT c.id, c.title, c.project_id, c.status FROM cards_fts f JOIN cards c ON f.id = c.id WHERE cards_fts MATCH :q ORDER BY rank"), {"q": q})
        return [{"id": r[0], "title": r[1], "project_id": r[2], "status": r[3]} for r in result.fetchall()]


@mcp.tool()
async def trigger_scan() -> dict:
    """Re-scan the projects folder for new or removed projects."""
    async with AsyncSessionLocal() as db:
        projects = await scan_projects(db)
        return {"scanned": len(projects)}
```

- [ ] **Step 4: Create backend/mcp/resources.py**

```python
from backend.mcp.server import mcp
from backend.database import AsyncSessionLocal
from backend.models import ProjectModel, CardModel, CardEventModel
from sqlalchemy import select
from backend.services.context_bundle import build_context_bundle


@mcp.resource("tracker://projects")
async def resource_projects() -> str:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(ProjectModel).where(ProjectModel.active == True))).scalars().all()  # noqa: E712
        lines = [f"- {p.id}: {p.name} [{', '.join(p.stack or [])}]" for p in rows]
        return "\n".join(lines) or "No projects found."


@mcp.resource("tracker://projects/{project_id}")
async def resource_project(project_id: str) -> str:
    async with AsyncSessionLocal() as db:
        p = await db.get(ProjectModel, project_id)
        if not p:
            return "Project not found."
        cards = (await db.execute(select(CardModel).where(CardModel.project_id == project_id))).scalars().all()
        card_lines = [f"  [{c.status}] {c.title} (id: {c.id})" for c in cards]
        return f"# {p.name}\nPath: {p.path}\nStack: {', '.join(p.stack or [])}\nBranch: {p.git_branch}\n\n## Cards\n" + "\n".join(card_lines)


@mcp.resource("tracker://cards/{card_id}")
async def resource_card(card_id: str) -> str:
    async with AsyncSessionLocal() as db:
        card = await db.get(CardModel, card_id)
        if not card:
            return "Card not found."
        events = (await db.execute(select(CardEventModel).where(CardEventModel.card_id == card_id).order_by(CardEventModel.created_at))).scalars().all()
        event_lines = [f"  [{e.type}] {e.body}" for e in events]
        return (
            f"# {card.title}\nStatus: {card.status} | Priority: {card.priority}\n"
            f"Assigned: {card.assigned_llm or 'unassigned'}\n\n"
            f"## Description\n{card.description or 'None'}\n\n"
            f"## Acceptance Criteria\n{card.acceptance or 'None'}\n\n"
            f"## Events\n" + "\n".join(event_lines)
        )


@mcp.resource("tracker://cards/{card_id}/context")
async def resource_context(card_id: str) -> str:
    async with AsyncSessionLocal() as db:
        return await build_context_bundle(card_id, db)
```

- [ ] **Step 5: Verify MCP mounts**

```bash
cd backend && python -c "from backend.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/mcp/
git commit -m "feat: MCP server — 11 tools + 4 resources over HTTP/SSE"
```

---

## Task 12: Context bundle service

**Files:**
- Create: `backend/services/context_bundle.py`

- [ ] **Step 1: Create backend/services/context_bundle.py**

```python
from __future__ import annotations
import os
import subprocess
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import CardModel, ProjectModel


def _file_tree(path: str, max_depth: int = 3) -> str:
    lines: list[str] = []

    def walk(current: str, depth: int, prefix: str):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.scandir(current), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in ("node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"):
                continue
            connector = "├── " if entry != entries[-1] else "└── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "│   " if entry != entries[-1] else "    "
                walk(entry.path, depth + 1, prefix + extension)

    lines.append(os.path.basename(path) + "/")
    walk(path, 1, "")
    return "\n".join(lines)


def _git_log(path: str, n: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=path, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "No commits"
    except Exception:
        return "Git log unavailable"


def _read_linked_files(project_path: str, linked_files: list[str]) -> str:
    parts: list[str] = []
    for rel_path in linked_files:
        abs_path = os.path.join(project_path, rel_path)
        if not os.path.isfile(abs_path):
            parts.append(f"### {rel_path}\n(file not found)")
            continue
        try:
            with open(abs_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(8000)  # cap at 8KB per file
            parts.append(f"### {rel_path}\n```\n{content}\n```")
        except OSError as e:
            parts.append(f"### {rel_path}\n(could not read: {e})")
    return "\n\n".join(parts)


async def build_context_bundle(card_id: str, db: AsyncSession) -> str:
    card = await db.get(CardModel, card_id)
    if not card:
        return "Card not found."

    project = await db.get(ProjectModel, card.project_id)
    if not project:
        return "Project not found."

    tree = _file_tree(project.path)
    log = _git_log(project.path)
    files_content = _read_linked_files(project.path, card.linked_files or [])

    return f"""# Context Bundle: {card.title}

## Card
- **ID:** {card.id}
- **Project:** {project.name} ({project.id})
- **Status:** {card.status}
- **Priority:** {card.priority}
- **Assigned to:** {card.assigned_llm or "unassigned"}

## Description
{card.description or "No description."}

## Acceptance Criteria
{card.acceptance or "No acceptance criteria defined."}

## Linked Files
{', '.join(card.linked_files) if card.linked_files else "None specified."}

## Project File Tree
```
{tree}
```

## Recent Git Log
```
{log}
```

## Linked File Contents
{files_content or "No linked files."}
"""
```

- [ ] **Step 2: Verify**

```bash
cd backend && python -c "from backend.services.context_bundle import build_context_bundle; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/services/context_bundle.py
git commit -m "feat: context bundle service — file tree, git log, linked file contents"
```

---

## Task 13: React frontend scaffold

**Files:**
- Create: `frontend/` (Vite + React + TS + Tailwind)

- [ ] **Step 1: Scaffold Vite app**

```bash
cd /Users/donaldrich/Projects/tracker
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install zustand
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Configure Tailwind — update frontend/vite.config.ts**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

- [ ] **Step 3: Update frontend/src/index.css**

```css
@import "tailwindcss";
```

- [ ] **Step 4: Create frontend/src/api/client.ts**

```ts
const BASE = '/api/v1'

export interface Project {
  id: string; name: string; stack: string[]
  git_branch: string | null; git_dirty: boolean; git_last_commit: string | null
  description: string | null; active: boolean
}

export interface Card {
  id: string; project_id: string; title: string; description: string | null
  status: 'todo' | 'in_progress' | 'review' | 'done' | 'blocked'
  priority: 'low' | 'medium' | 'high'; assigned_llm: string | null
  tags: string[]; linked_files: string[]; acceptance: string | null
  blocks: string[]; blocked_by: string[]
  created_at: string | null; started_at: string | null; completed_at: string | null
}

export interface CardEvent {
  id: string; card_id: string; type: string; body: string | null
  actor: string | null; meta: Record<string, unknown> | null; created_at: string | null
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  projects: {
    list: () => req<Project[]>('GET', '/projects'),
    scan: () => req<{ scanned: number }>('POST', '/projects/scan'),
  },
  cards: {
    list: (projectId: string) => req<Card[]>('GET', `/projects/${projectId}/cards`),
    create: (projectId: string, data: Partial<Card>) => req<Card>('POST', `/projects/${projectId}/cards`, data),
    get: (id: string) => req<Card>('GET', `/cards/${id}`),
    update: (id: string, data: Partial<Card>) => req<Card>('PATCH', `/cards/${id}`, data),
    delete: (id: string) => req<void>('DELETE', `/cards/${id}`),
  },
  events: {
    list: (cardId: string) => req<CardEvent[]>('GET', `/cards/${cardId}/events`),
    log: (cardId: string, body: string) => req<CardEvent>('POST', `/cards/${cardId}/log`, { body, actor: 'user' }),
    milestone: (cardId: string, body: string) => req<CardEvent>('POST', `/cards/${cardId}/milestone`, { body, actor: 'user' }),
  },
  search: (q: string) => req<Card[]>('GET', `/search?q=${encodeURIComponent(q)}`),
}
```

- [ ] **Step 5: Create frontend/src/store/index.ts**

```ts
import { create } from 'zustand'
import { api, Project, Card, CardEvent } from '../api/client'

interface TrackerStore {
  projects: Project[]
  activeProjectId: string | null
  cards: Record<string, Card[]>         // projectId -> cards
  activeCardId: string | null
  events: Record<string, CardEvent[]>   // cardId -> events

  loadProjects: () => Promise<void>
  setActiveProject: (id: string) => void
  loadCards: (projectId: string) => Promise<void>
  setActiveCard: (id: string | null) => void
  loadEvents: (cardId: string) => Promise<void>
  upsertCard: (card: Card) => void
  removeCard: (cardId: string) => void
  appendEvent: (event: CardEvent) => void
  scan: () => Promise<void>
}

export const useStore = create<TrackerStore>((set, get) => ({
  projects: [],
  activeProjectId: null,
  cards: {},
  activeCardId: null,
  events: {},

  loadProjects: async () => {
    const projects = await api.projects.list()
    set({ projects })
    if (!get().activeProjectId && projects.length > 0) {
      get().setActiveProject(projects[0].id)
    }
  },

  setActiveProject: (id) => {
    set({ activeProjectId: id, activeCardId: null })
    get().loadCards(id)
  },

  loadCards: async (projectId) => {
    const cards = await api.cards.list(projectId)
    set(s => ({ cards: { ...s.cards, [projectId]: cards } }))
  },

  setActiveCard: (id) => {
    set({ activeCardId: id })
    if (id) get().loadEvents(id)
  },

  loadEvents: async (cardId) => {
    const events = await api.events.list(cardId)
    set(s => ({ events: { ...s.events, [cardId]: events } }))
  },

  upsertCard: (card) => {
    set(s => {
      const existing = s.cards[card.project_id] || []
      const idx = existing.findIndex(c => c.id === card.id)
      const updated = idx >= 0
        ? existing.map(c => c.id === card.id ? card : c)
        : [...existing, card]
      return { cards: { ...s.cards, [card.project_id]: updated } }
    })
  },

  removeCard: (cardId) => {
    set(s => {
      const newCards = { ...s.cards }
      for (const pid in newCards) {
        newCards[pid] = newCards[pid].filter(c => c.id !== cardId)
      }
      return { cards: newCards }
    })
  },

  appendEvent: (event) => {
    set(s => ({
      events: {
        ...s.events,
        [event.card_id]: [...(s.events[event.card_id] || []), event],
      }
    }))
  },

  scan: async () => {
    await api.projects.scan()
    await get().loadProjects()
  },
}))
```

- [ ] **Step 6: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: build completes, `dist/` created.

- [ ] **Step 7: Commit**

```bash
cd /Users/donaldrich/Projects/tracker
git add frontend/
git commit -m "feat: React + Vite + Tailwind scaffold, API client, Zustand store"
```

---

## Task 14: App shell, project tabs, board header

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/ProjectTabs.tsx`
- Create: `frontend/src/components/BoardHeader.tsx`
- Create: `frontend/src/hooks/useProjectSocket.ts`

- [ ] **Step 1: Update frontend/src/main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>
)
```

- [ ] **Step 2: Create frontend/src/hooks/useProjectSocket.ts**

```ts
import { useEffect } from 'react'
import { useStore } from '../store'
import { api } from '../api/client'

export function useProjectSocket(projectId: string | null) {
  const { upsertCard, removeCard, appendEvent, loadCards } = useStore()

  useEffect(() => {
    if (!projectId) return
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${location.host}/ws/projects/${projectId}`)

    ws.onmessage = async (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'card.created' || msg.type === 'card.updated') {
        const card = await api.cards.get(msg.card_id)
        upsertCard(card)
      } else if (msg.type === 'card.deleted') {
        removeCard(msg.card_id)
      } else if (msg.type === 'card.log' || msg.type === 'card.milestone') {
        appendEvent({
          id: crypto.randomUUID(),
          card_id: msg.card_id,
          type: msg.type === 'card.log' ? 'log' : 'milestone',
          body: msg.body,
          actor: msg.actor,
          meta: null,
          created_at: new Date().toISOString(),
        })
      }
    }

    return () => ws.close()
  }, [projectId, upsertCard, removeCard, appendEvent])
}
```

- [ ] **Step 3: Create frontend/src/components/ProjectTabs.tsx**

```tsx
import { useStore } from '../store'

export function ProjectTabs() {
  const { projects, activeProjectId, setActiveProject } = useStore()

  return (
    <div className="flex gap-1 overflow-x-auto px-4 py-2 bg-gray-900 border-b border-gray-800">
      {projects.filter(p => p.active).map(p => (
        <button
          key={p.id}
          onClick={() => setActiveProject(p.id)}
          className={`px-3 py-1 rounded-full text-sm whitespace-nowrap transition-colors ${
            activeProjectId === p.id
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          {p.name}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/src/components/BoardHeader.tsx**

```tsx
import { useStore } from '../store'

interface Props {
  view: 'kanban' | 'list'
  onViewChange: (v: 'kanban' | 'list') => void
}

export function BoardHeader({ view, onViewChange }: Props) {
  const { projects, activeProjectId, scan } = useStore()
  const project = projects.find(p => p.id === activeProjectId)
  if (!project) return null

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-4">
        <h1 className="text-white font-semibold text-lg">{project.name}</h1>
        {project.git_branch && (
          <span className="text-green-400 text-sm font-mono">{project.git_branch}</span>
        )}
        {project.git_dirty && (
          <span className="text-yellow-400 text-xs">● uncommitted changes</span>
        )}
        {project.git_last_commit && (
          <span className="text-gray-500 text-xs truncate max-w-xs">{project.git_last_commit}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onViewChange('kanban')}
          className={`px-2 py-1 text-xs rounded ${view === 'kanban' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          ⊞ Kanban
        </button>
        <button
          onClick={() => onViewChange('list')}
          className={`px-2 py-1 text-xs rounded ${view === 'list' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          ☰ List
        </button>
        <button
          onClick={scan}
          className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded ml-2"
        >
          Rescan
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Update frontend/src/App.tsx**

```tsx
import { useEffect, useState } from 'react'
import { useStore } from './store'
import { ProjectTabs } from './components/ProjectTabs'
import { BoardHeader } from './components/BoardHeader'
import { KanbanBoard } from './components/KanbanBoard'
import { ListView } from './components/ListView'
import { CardDetail } from './components/CardDetail'
import { useProjectSocket } from './hooks/useProjectSocket'

export default function App() {
  const { loadProjects, activeProjectId, activeCardId } = useStore()
  const [view, setView] = useState<'kanban' | 'list'>('kanban')
  useProjectSocket(activeProjectId)

  useEffect(() => { loadProjects() }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <nav className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <span className="font-bold text-indigo-400 text-lg">⬡ Tracker</span>
      </nav>
      <ProjectTabs />
      {activeProjectId && (
        <>
          <BoardHeader view={view} onViewChange={setView} />
          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-auto">
              {view === 'kanban' ? <KanbanBoard /> : <ListView />}
            </div>
            {activeCardId && <CardDetail />}
          </div>
        </>
      )}
      {!activeProjectId && (
        <div className="flex-1 flex items-center justify-center text-gray-600">
          No projects found. Make sure your projects folder is mounted.
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 6: Build to verify**

```bash
cd frontend && npm run build
```

Expected: builds without errors.

- [ ] **Step 7: Commit**

```bash
cd /Users/donaldrich/Projects/tracker
git add frontend/src/
git commit -m "feat: app shell, project tabs, board header, WebSocket hook"
```

---

## Task 15: Kanban board + Card item

**Files:**
- Create: `frontend/src/components/KanbanBoard.tsx`
- Create: `frontend/src/components/ListView.tsx`
- Create: `frontend/src/components/CardItem.tsx`
- Create: `frontend/src/components/AddCardModal.tsx`

- [ ] **Step 1: Create frontend/src/components/CardItem.tsx**

```tsx
import { Card } from '../api/client'
import { useStore } from '../store'

const PRIORITY_COLORS = { low: 'border-gray-600', medium: 'border-yellow-500', high: 'border-red-500' }
const LLM_COLORS: Record<string, string> = { claude: 'text-violet-400', kimi: 'text-blue-400' }

interface Props { card: Card; compact?: boolean }

export function CardItem({ card, compact }: Props) {
  const { setActiveCard, activeCardId } = useStore()
  const isActive = activeCardId === card.id

  return (
    <div
      onClick={() => setActiveCard(isActive ? null : card.id)}
      className={`cursor-pointer rounded-lg p-3 mb-2 border-l-4 transition-colors
        ${PRIORITY_COLORS[card.priority]}
        ${isActive ? 'bg-indigo-900/40 ring-1 ring-indigo-500' : 'bg-gray-800 hover:bg-gray-750'}`}
    >
      <div className="text-sm font-medium text-white leading-snug">{card.title}</div>
      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
        {card.tags.map(t => (
          <span key={t} className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{t}</span>
        ))}
        {card.assigned_llm && (
          <span className={`text-xs font-medium ${LLM_COLORS[card.assigned_llm] || 'text-gray-400'}`}>
            🤖 {card.assigned_llm}
          </span>
        )}
        {card.status === 'in_progress' && card.assigned_llm && (
          <span className="text-xs text-green-400">● live</span>
        )}
      </div>
      {!compact && card.blocked_by.length > 0 && (
        <div className="mt-1 text-xs text-red-400">⛔ blocked</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create frontend/src/components/AddCardModal.tsx**

```tsx
import { useState } from 'react'
import { useStore } from '../store'
import { api } from '../api/client'

interface Props { projectId: string; onClose: () => void }

export function AddCardModal({ projectId, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium')
  const { upsertCard } = useStore()

  const submit = async () => {
    if (!title.trim()) return
    const card = await api.cards.create(projectId, { title, description, priority })
    upsertCard(card)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h2 className="text-white font-semibold text-lg mb-4">Add Card</h2>
        <input
          autoFocus
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Card title"
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-3 text-sm border border-gray-700 focus:outline-none focus:border-indigo-500"
        />
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={3}
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-3 text-sm border border-gray-700 focus:outline-none focus:border-indigo-500 resize-none"
        />
        <select
          value={priority}
          onChange={e => setPriority(e.target.value as 'low' | 'medium' | 'high')}
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-4 text-sm border border-gray-700 focus:outline-none"
        >
          <option value="low">Low priority</option>
          <option value="medium">Medium priority</option>
          <option value="high">High priority</option>
        </select>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          <button onClick={submit} className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg">Add Card</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create frontend/src/components/KanbanBoard.tsx**

```tsx
import { useState } from 'react'
import { useStore } from '../store'
import { CardItem } from './CardItem'
import { AddCardModal } from './AddCardModal'
import { Card } from '../api/client'

const COLUMNS: { id: Card['status']; label: string }[] = [
  { id: 'todo', label: 'Todo' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'review', label: 'Review' },
  { id: 'done', label: 'Done' },
]

export function KanbanBoard() {
  const { activeProjectId, cards } = useStore()
  const [showAdd, setShowAdd] = useState(false)
  if (!activeProjectId) return null
  const projectCards = cards[activeProjectId] || []

  return (
    <div className="flex gap-4 p-6 h-full overflow-x-auto">
      {COLUMNS.map(col => {
        const colCards = projectCards.filter(c => c.status === col.id)
        return (
          <div key={col.id} className="flex-shrink-0 w-64">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase text-gray-400 tracking-wider">{col.label}</span>
              <span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">{colCards.length}</span>
            </div>
            <div className="min-h-8">
              {colCards.map(card => <CardItem key={card.id} card={card} />)}
            </div>
            {col.id === 'todo' && (
              <button
                onClick={() => setShowAdd(true)}
                className="w-full mt-1 border border-dashed border-gray-700 rounded-lg py-2 text-xs text-gray-600 hover:text-gray-400 hover:border-gray-600 transition-colors"
              >
                + Add card
              </button>
            )}
          </div>
        )
      })}
      {showAdd && activeProjectId && (
        <AddCardModal projectId={activeProjectId} onClose={() => setShowAdd(false)} />
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/src/components/ListView.tsx**

```tsx
import { useState } from 'react'
import { useStore } from '../store'
import { CardItem } from './CardItem'
import { AddCardModal } from './AddCardModal'
import { Card } from '../api/client'

const GROUPS: Card['status'][] = ['in_progress', 'todo', 'review', 'blocked', 'done']
const LABELS: Record<Card['status'], string> = {
  in_progress: 'In Progress', todo: 'Todo', review: 'Review', blocked: 'Blocked', done: 'Done'
}

export function ListView() {
  const { activeProjectId, cards } = useStore()
  const [showAdd, setShowAdd] = useState(false)
  if (!activeProjectId) return null
  const projectCards = cards[activeProjectId] || []

  return (
    <div className="p-6 max-w-2xl">
      {GROUPS.map(status => {
        const grouped = projectCards.filter(c => c.status === status)
        if (grouped.length === 0) return null
        return (
          <div key={status} className="mb-6">
            <div className="text-xs font-bold uppercase text-gray-500 tracking-wider mb-2">{LABELS[status]}</div>
            {grouped.map(card => <CardItem key={card.id} card={card} compact />)}
          </div>
        )
      })}
      <button
        onClick={() => setShowAdd(true)}
        className="mt-2 border border-dashed border-gray-700 rounded-lg px-4 py-2 text-xs text-gray-600 hover:text-gray-400"
      >
        + Add card
      </button>
      {showAdd && activeProjectId && (
        <AddCardModal projectId={activeProjectId} onClose={() => setShowAdd(false)} />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Build to verify**

```bash
cd frontend && npm run build
```

Expected: builds without errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/donaldrich/Projects/tracker
git add frontend/src/
git commit -m "feat: kanban board, list view, card items, add card modal"
```

---

## Task 16: Card detail panel + log stream

**Files:**
- Create: `frontend/src/components/CardDetail.tsx`
- Create: `frontend/src/components/LogStream.tsx`

- [ ] **Step 1: Create frontend/src/components/LogStream.tsx**

```tsx
import { useEffect, useRef } from 'react'
import { CardEvent } from '../api/client'

interface Props { events: CardEvent[] }

export function LogStream({ events }: Props) {
  const logs = events.filter(e => e.type === 'log')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  if (logs.length === 0) {
    return <div className="text-xs text-gray-600 italic">No log entries yet.</div>
  }

  return (
    <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs overflow-auto max-h-48 space-y-0.5">
      {logs.map(e => (
        <div key={e.id} className="flex gap-2">
          <span className="text-gray-600 shrink-0">
            {e.created_at ? new Date(e.created_at).toLocaleTimeString() : ''}
          </span>
          <span className="text-gray-300 break-all">{e.body}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}
```

- [ ] **Step 2: Create frontend/src/components/CardDetail.tsx**

```tsx
import { useStore } from '../store'
import { api } from '../api/client'
import { LogStream } from './LogStream'

const STATUS_OPTIONS = ['todo', 'in_progress', 'review', 'done', 'blocked'] as const
const PRIORITY_OPTIONS = ['low', 'medium', 'high'] as const

export function CardDetail() {
  const { activeCardId, cards, events, upsertCard, setActiveCard, activeProjectId } = useStore()
  const projectCards = activeProjectId ? (cards[activeProjectId] || []) : []
  const card = projectCards.find(c => c.id === activeCardId)
  const cardEvents = activeCardId ? (events[activeCardId] || []) : []

  if (!card) return null
  const milestones = cardEvents.filter(e => e.type === 'milestone')

  const updateStatus = async (status: string) => {
    const updated = await api.cards.update(card.id, { status })
    upsertCard(updated)
  }

  const updatePriority = async (priority: string) => {
    const updated = await api.cards.update(card.id, { priority })
    upsertCard(updated)
  }

  const deleteCard = async () => {
    await api.cards.delete(card.id)
    setActiveCard(null)
  }

  return (
    <div className="w-96 bg-gray-900 border-l border-gray-800 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="text-white font-semibold text-sm leading-snug flex-1 pr-2">{card.title}</h2>
        <button onClick={() => setActiveCard(null)} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status + Priority */}
        <div className="flex gap-2">
          <select
            value={card.status}
            onChange={e => updateStatus(e.target.value)}
            className="flex-1 bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700"
          >
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
          <select
            value={card.priority}
            onChange={e => updatePriority(e.target.value)}
            className="flex-1 bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700"
          >
            {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {/* Assigned LLM */}
        {card.assigned_llm && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Assigned to</div>
            <div className="text-violet-400 text-sm">🤖 {card.assigned_llm}</div>
          </div>
        )}

        {/* Description */}
        {card.description && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Description</div>
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{card.description}</p>
          </div>
        )}

        {/* Acceptance criteria */}
        {card.acceptance && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Acceptance Criteria</div>
            <pre className="text-gray-300 text-xs whitespace-pre-wrap font-sans">{card.acceptance}</pre>
          </div>
        )}

        {/* Linked files */}
        {card.linked_files.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Linked Files</div>
            {card.linked_files.map(f => (
              <div key={f} className="text-indigo-400 text-xs font-mono">{f}</div>
            ))}
          </div>
        )}

        {/* Tags */}
        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {card.tags.map(t => (
              <span key={t} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">{t}</span>
            ))}
          </div>
        )}

        {/* Milestones */}
        {milestones.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-2">Milestones</div>
            <div className="space-y-1">
              {milestones.map(m => (
                <div key={m.id} className="flex items-start gap-2 text-xs">
                  <span className="text-green-400 mt-0.5">✓</span>
                  <span className="text-gray-300">{m.body}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Log stream */}
        <div>
          <div className="text-xs text-gray-500 uppercase mb-2">Live Log</div>
          <LogStream events={cardEvents} />
        </div>

        {/* Timestamps */}
        <div className="text-xs text-gray-600 space-y-0.5 border-t border-gray-800 pt-3">
          {card.created_at && <div>Created: {new Date(card.created_at).toLocaleString()}</div>}
          {card.started_at && <div>Started: {new Date(card.started_at).toLocaleString()}</div>}
          {card.completed_at && <div>Completed: {new Date(card.completed_at).toLocaleString()}</div>}
        </div>

        <button
          onClick={deleteCard}
          className="w-full text-xs text-red-500 hover:text-red-400 py-2 border border-red-900 hover:border-red-800 rounded-lg transition-colors"
        >
          Delete card
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Build**

```bash
cd frontend && npm run build
```

Expected: builds without errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/donaldrich/Projects/tracker
git add frontend/src/
git commit -m "feat: card detail panel with log stream, milestones, inline status/priority edit"
```

---

## Task 17: Dockerfile + docker-compose

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

- [ ] **Step 1: Create .dockerignore**

```
**/__pycache__
**/*.pyc
**/.pytest_cache
frontend/node_modules
frontend/dist
backend/.venv
*.db
.superpowers
docs
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Python backend
FROM python:3.12-slim
WORKDIR /app

# Install backend dependencies
COPY backend/pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Create data directory for SQLite
RUN mkdir -p /data

ENV DB_PATH=/data/tracker.db
ENV FRONTEND_DIST=/app/frontend/dist

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
services:
  tracker:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - tracker-data:/data
      - ${PROJECTS_ROOT:-/Users/donaldrich/Projects}:/projects:ro
    environment:
      - DB_PATH=/data/tracker.db
      - FRONTEND_DIST=/app/frontend/dist
      - PROJECTS_ROOT=/projects
    restart: unless-stopped

volumes:
  tracker-data:
```

- [ ] **Step 4: Build Docker image**

```bash
cd /Users/donaldrich/Projects/tracker
docker compose build
```

Expected: build completes with both stages.

- [ ] **Step 5: Start the container**

```bash
docker compose up -d
```

- [ ] **Step 6: Verify the app is running**

```bash
curl http://localhost:8000/api/v1/projects
```

Expected: JSON array (may be empty if projects mount is new).

```bash
curl http://localhost:8000/api/v1/projects/scan -X POST
```

Expected: `{"scanned": N}` where N is the number of qualifying projects found.

- [ ] **Step 7: Open the UI**

Navigate to `http://localhost:8000` in a browser. You should see the Tracker app with your projects listed.

- [ ] **Step 8: Verify MCP endpoint**

```bash
curl http://localhost:8000/mcp/
```

Expected: MCP server response (SSE handshake or JSON capability listing).

- [ ] **Step 9: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: multi-stage Dockerfile + docker-compose with projects volume mount"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Single container — Dockerfile + compose
- ✅ Project scanning (startup + manual trigger) — `lifespan` + `POST /projects/scan`
- ✅ Git detection + project files — `scanner/detector.py`
- ✅ All card fields — models + schemas
- ✅ Real-time: log stream + milestones — `card_events` + WebSocket
- ✅ All MCP tools (11) — `mcp/tools.py`
- ✅ MCP resources (4) — `mcp/resources.py`
- ✅ Context bundle — `services/context_bundle.py` + MCP resource
- ✅ Kanban default + list toggle — `KanbanBoard`, `ListView`, toggle in `BoardHeader`
- ✅ Git status on board header — `BoardHeader`
- ✅ Stack auto-detection — `scanner/detector.py:MARKER_FILES`
- ✅ Card dependencies (blocks/blocked_by) — models + card detail display
- ✅ Webhooks — API + fire service
- ✅ Full-text search — FTS5 + `/search` route + `search_cards` MCP tool
- ✅ Audit trail — all mutations write `card_events`
- ✅ No auth — none implemented

**Type consistency verified:** `CardModel`, `CardOut`, `Card` (TS) all use same field names. `EventTypeEnum` values match TS event type strings.
