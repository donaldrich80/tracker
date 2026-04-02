import pytest
import respx
import httpx
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


async def test_register_and_list_webhook(client):
    r = await client.post("/api/v1/webhooks", json={"url": "http://example.com/hook", "events": ["card.log"]})
    assert r.status_code == 201
    r2 = await client.get("/api/v1/webhooks")
    assert len(r2.json()) == 1


async def test_delete_webhook(client):
    r = await client.post("/api/v1/webhooks", json={"url": "http://x.com/h", "events": ["card.log"]})
    wid = r.json()["id"]
    r2 = await client.delete(f"/api/v1/webhooks/{wid}")
    assert r2.status_code == 204
    r3 = await client.get("/api/v1/webhooks")
    assert r3.json() == []
