from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.database import get_db
from backend.models import ProjectModel
from backend.schemas import ProjectOut
from backend.scanner.detector import scan_projects

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(active: bool | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(ProjectModel)
    if active is not None:
        stmt = stmt.where(ProjectModel.active == active)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await db.get(ProjectModel, project_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")
    return p


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    p = await db.get(ProjectModel, project_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")
    for field in ("name", "description"):
        if field in data:
            setattr(p, field, data[field])
    await db.commit()
    await db.refresh(p)
    return p


@router.post("/projects/scan")
async def trigger_scan(db: AsyncSession = Depends(get_db)):
    projects = await scan_projects(db)
    return {"scanned": len(projects)}
