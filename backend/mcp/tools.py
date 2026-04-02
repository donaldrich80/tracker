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
