from __future__ import annotations
import os
import subprocess
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models import CardModel, ProjectModel


def _file_tree(path: str, max_depth: int = 3) -> str:
    lines: list[str] = []

    def walk(current: str, depth: int, prefix: str):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.scandir(current), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in ("node_modules", "__pycache__", ".git", "dist", "build", ".venv", "venv"):
                continue
            connector = "├── " if entry != entries[-1] else "└── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "│   " if entry != entries[-1] else "    "
                walk(entry.path, depth + 1, prefix + extension)

    lines.append(os.path.basename(path) + "/")
    walk(path, 1, "")
    return "\n".join(lines)


def _git_log(path: str, n: int = 10) -> str:
    try:
        result = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=path, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "No commits"
    except Exception:
        return "Git log unavailable"


def _read_linked_files(project_path: str, linked_files: list[str]) -> str:
    parts: list[str] = []
    for rel_path in linked_files:
        abs_path = os.path.join(project_path, rel_path)
        if not os.path.isfile(abs_path):
            parts.append(f"### {rel_path}\n(file not found)")
            continue
        try:
            with open(abs_path, encoding="utf-8", errors="ignore") as f:
                content = f.read(8000)  # cap at 8KB per file
            parts.append(f"### {rel_path}\n```\n{content}\n```")
        except OSError as e:
            parts.append(f"### {rel_path}\n(could not read: {e})")
    return "\n\n".join(parts)


async def build_context_bundle(card_id: str, db: AsyncSession) -> str:
    card = await db.get(CardModel, card_id)
    if not card:
        return "Card not found."

    project = await db.get(ProjectModel, card.project_id)
    if not project:
        return "Project not found."

    tree = _file_tree(project.path)
    log = _git_log(project.path)
    files_content = _read_linked_files(project.path, card.linked_files or [])

    return f"""# Context Bundle: {card.title}

## Card
- **ID:** {card.id}
- **Project:** {project.name} ({project.id})
- **Status:** {card.status}
- **Priority:** {card.priority}
- **Assigned to:** {card.assigned_llm or "unassigned"}

## Description
{card.description or "No description."}

## Acceptance Criteria
{card.acceptance or "No acceptance criteria defined."}

## Linked Files
{', '.join(card.linked_files) if card.linked_files else "None specified."}

## Project File Tree
```
{tree}
```

## Recent Git Log
```
{log}
```

## Linked File Contents
{files_content or "No linked files."}
"""
