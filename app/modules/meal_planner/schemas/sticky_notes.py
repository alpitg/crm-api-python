from pydantic import BaseModel
from typing import Optional


class StickyNoteOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    color: str
    rotation: str