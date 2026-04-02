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
