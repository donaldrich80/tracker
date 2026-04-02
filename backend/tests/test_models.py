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
