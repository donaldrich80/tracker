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
