from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Topic(BaseModel):
    title: str
    due_at: datetime
    status: str


class TopicStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    closed = "closed"
