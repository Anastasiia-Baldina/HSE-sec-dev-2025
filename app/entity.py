from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from app.constants import STATUS_CLOSED, STATUS_IN_PROGRESS, STATUS_OPEN


class Topic(BaseModel):
    title: str
    due_at: datetime
    status: str


class TopicStatus(str, Enum):
    open = STATUS_OPEN
    in_progress = STATUS_IN_PROGRESS
    closed = STATUS_CLOSED
