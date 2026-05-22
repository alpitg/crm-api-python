from pydantic import BaseModel
from typing import Optional

class StickyNoteIn(BaseModel):
    title: str
    description: str


class StickyNoteOut(BaseModel):
    id: int
    title: str
    description: str
    isPinned: bool = False