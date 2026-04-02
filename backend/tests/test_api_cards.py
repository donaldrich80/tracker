import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import Base, engine, AsyncSessionLocal
from backend.models import ProjectModel


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(ProjectModel(id="proj1", name="P1", path="/p1"))
        await db.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_create_and_list_cards(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "My card"})
    assert r.status_code == 201
    card_id = r.json()["id"]

    r2 = await client.get("/api/v1/projects/proj1/cards")
    assert r2.status_code == 200
    ids = [c["id"] for c in r2.json()]
    assert card_id in ids


async def test_get_card(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T", "priority": "high"})
    card_id = r.json()["id"]
    r2 = await client.get(f"/api/v1/cards/{card_id}")
    assert r2.status_code == 200
    assert r2.json()["priority"] == "high"


async def test_update_card_status(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T"})
    card_id = r.json()["id"]
    r2 = await client.patch(f"/api/v1/cards/{card_id}", json={"status": "in_progress"})
    assert r2.status_code == 200
    assert r2.json()["status"] == "in_progress"


async def test_delete_card(client):
    r = await client.post("/api/v1/projects/proj1/cards", json={"title": "T"})
    card_id = r.json()["id"]
    r2 = await client.delete(f"/api/v1/cards/{card_id}")
    assert r2.status_code == 204
    r3 = await client.get(f"/api/v1/cards/{card_id}")
    assert r3.status_code == 404
