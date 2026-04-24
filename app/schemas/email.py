from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class EmailBase(BaseModel):
    sender: str
    subject: str
    raw_content: str
    received_at: Optional[datetime] = None

class EmailCreate(EmailBase):
    pass # 进关时不需要 ID 和分数

class Email(EmailBase):
    id: int
    priority_score: float = 0.0
    category: Optional[str] = None
    status: str = "pending"
    created_at: datetime

    class Config:
        from_attributes = True