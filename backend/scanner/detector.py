from __future__ import annotations
import os
import re
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.models import ProjectModel
from backend.scanner.git_info import read_git_info

MARKER_FILES = {
    "package.json": "node",
    "pyproject.toml": "python",
    "setup.py": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "Dockerfile": "docker",
    "docker-compose.yml": "compose",
    "docker-compose.yaml": "compose",
}


def is_project_dir(path: str) -> bool:
    if not os.path.isdir(os.path.join(path, ".git")):
        return False
    return any(os.path.exists(os.path.join(path, f)) for f in MARKER_FILES)


def detect_stack(path: str) -> list[str]:
    seen: set[str] = set()
    for filename, tag in MARKER_FILES.items():
        if os.path.exists(os.path.join(path, filename)) and tag not in seen:
            seen.add(tag)
    return sorted(seen)


def _read_description(path: str) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        readme = os.path.join(path, name)
        if os.path.isfile(readme):
            try:
                with open(readme, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            return line[:300]
            except OSError:
                pass
    return None


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


async def scan_projects(db: AsyncSession, projects_root: str | None = None) -> list[ProjectModel]:
    root = projects_root or os.getenv("PROJECTS_ROOT", "/projects")
    if not os.path.isdir(root):
        return []

    found_ids: set[str] = set()
    results: list[ProjectModel] = []

    for entry in sorted(os.scandir(root), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        if not is_project_dir(entry.path):
            continue

        proj_id = _slug(entry.name)
        found_ids.add(proj_id)

        git = read_git_info(entry.path)
        stack = detect_stack(entry.path)
        description = _read_description(entry.path)

        existing = await db.get(ProjectModel, proj_id)
        if existing:
            existing.name = entry.name
            existing.path = entry.path
            existing.stack = stack
            existing.git_branch = git["branch"]
            existing.git_dirty = git["dirty"]
            existing.git_last_commit = git["last_commit"]
            existing.description = description
            existing.scanned_at = datetime.now(timezone.utc)
            existing.active = True
            results.append(existing)
        else:
            proj = ProjectModel(
                id=proj_id,
                name=entry.name,
                path=entry.path,
                stack=stack,
                git_branch=git["branch"],
                git_dirty=git["dirty"],
                git_last_commit=git["last_commit"],
                description=description,
                scanned_at=datetime.now(timezone.utc),
                active=True,
            )
            db.add(proj)
            results.append(proj)

    # Mark missing projects inactive
    stmt = select(ProjectModel).where(ProjectModel.active == True)  # noqa: E712
    existing_active = (await db.execute(stmt)).scalars().all()
    for p in existing_active:
        if p.id not in found_ids:
            p.active = False

    await db.commit()
    return results
