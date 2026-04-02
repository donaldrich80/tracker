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
