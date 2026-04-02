import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal, create_tables
from backend.models import ProjectModel, CardModel


@pytest.fixture(autouse=True)
async def setup_db():
    await create_tables()
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="p1", name="P", path="/p"))
        db.add(CardModel(id="c1", project_id="p1", title="OAuth support", description="Add Google OAuth"))
        db.add(CardModel(id="c2", project_id="p1", title="Fix login bug", description="Login fails on timeout"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(__import__('sqlalchemy').text("DROP TABLE IF EXISTS cards_fts"))


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
