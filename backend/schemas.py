from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: str
    name: str
    path: str
    stack: list[str]
    git_branch: str | None
    git_dirty: bool
    git_last_commit: str | None
    description: str | None
    scanned_at: datetime | None
    active: bool

    model_config = {"from_attributes": True}


class CardCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "medium"
    tags: list[str] = []
    linked_files: list[str] = []
    acceptance: str | None = None
    blocks: list[str] = []
    blocked_by: list[str] = []


class CardUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_llm: str | None = None
    tags: list[str] | None = None
    linked_files: list[str] | None = None
    acceptance: str | None = None
    blocks: list[str] | None = None
    blocked_by: list[str] | None = None


class CardOut(BaseModel):
    id: str
    project_id: str
    title: str
    description: str | None
    status: str
    priority: str
    assigned_llm: str | None
    tags: list[str]
    linked_files: list[str]
    acceptance: str | None
    blocks: list[str]
    blocked_by: list[str]
    created_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class CardEventOut(BaseModel):
    id: str
    card_id: str
    type: str
    body: str | None
    actor: str | None
    meta: dict[str, Any] | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class LogCreate(BaseModel):
    body: str
    actor: str = "user"


class MilestoneCreate(BaseModel):
    body: str
    actor: str = "user"


class WebhookCreate(BaseModel):
    url: str
    events: list[str]


class WebhookOut(BaseModel):
    id: str
    url: str
    events: list[str]
    active: bool

    model_config = {"from_attributes": True}
