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
