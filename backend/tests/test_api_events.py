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
