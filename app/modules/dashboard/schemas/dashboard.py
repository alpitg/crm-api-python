from pydantic import BaseModel

class DashboardStatOut(BaseModel):
    icon: str
    value: int
    label: str