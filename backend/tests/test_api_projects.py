import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from backend.main import app
from backend.database import Base, engine


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_list_projects_empty(client):
    r = await client.get("/api/v1/projects")
    assert r.status_code == 200
    assert r.json() == []


async def test_scan_projects(client):
    with patch("backend.api.projects.scan_projects", new_callable=AsyncMock) as mock_scan:
        mock_scan.return_value = []
        r = await client.post("/api/v1/projects/scan")
        assert r.status_code == 200
        assert mock_scan.called
