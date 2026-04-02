import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, JSON, String, Text
from backend.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class StatusEnum(str, enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    blocked = "blocked"


class PriorityEnum(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class EventTypeEnum(str, enum.Enum):
    log = "log"
    milestone = "milestone"
    status_change = "status_change"
    assignment = "assignment"


class ProjectModel(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    path = Column(String, nullable=False)
    stack = Column(JSON, default=list, nullable=False)
    git_branch = Column(String)
    git_dirty = Column(Boolean, default=False)
    git_last_commit = Column(String)
    description = Column(Text)
    scanned_at = Column(DateTime)
    active = Column(Boolean, default=True, nullable=False)


class CardModel(Base):
    __tablename__ = "cards"
    id = Column(String, primary_key=True, default=_uuid)
    project_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.todo, nullable=False)
    priority = Column(SAEnum(PriorityEnum), default=PriorityEnum.medium, nullable=False)
    assigned_llm = Column(String)
    tags = Column(JSON, default=list, nullable=False)
    linked_files = Column(JSON, default=list, nullable=False)
    acceptance = Column(Text)
    blocks = Column(JSON, default=list, nullable=False)
    blocked_by = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=_now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)


class CardEventModel(Base):
    __tablename__ = "card_events"
    id = Column(String, primary_key=True, default=_uuid)
    card_id = Column(String, nullable=False)
    type = Column(SAEnum(EventTypeEnum), nullable=False)
    body = Column(Text)
    actor = Column(String)
    meta = Column(JSON)
    created_at = Column(DateTime, default=_now)


class WebhookModel(Base):
    __tablename__ = "webhooks"
    id = Column(String, primary_key=True, default=_uuid)
    url = Column(String, nullable=False)
    events = Column(JSON, default=list, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
