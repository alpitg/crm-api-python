from typing import Any, Dict
from pydantic import BaseModel

# class PartyDetails(BaseModel):
#     name: str
#     detail: str
#     phone: str

class InvoiceIn(BaseModel):
    billDate: str
    billFrom: Dict[str, Any] # Optional[PartyDetails] = None
    billTo: Dict[str, Any] # Optional[PartyDetails] = None
    paymentMode: str
    paymentStatus: str = "pending"