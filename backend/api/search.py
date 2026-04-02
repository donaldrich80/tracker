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
