from typing import Any, Dict, Optional
from pydantic import BaseModel

# class PartyDetails[BaseModel]:
#     name: str
#     detail: str
#     phone: str

class InvoiceIn(BaseModel):
    generateInvoice: bool = False
    billDate: Optional[str]
    billFrom: Optional[Dict[str, Any]] # Optional[PartyDetails] = None
    billTo: Optional[Dict[str, Any]] # Optional[PartyDetails] = None
    paymentMode: Optional[str]
    paymentStatus: Optional[str] = "pending"
    