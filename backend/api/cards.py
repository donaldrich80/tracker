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
