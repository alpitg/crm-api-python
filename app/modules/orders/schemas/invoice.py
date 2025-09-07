from typing import Any, Dict, List, Optional
from pydantic import BaseModel

# class PartyDetails[BaseModel]:
#     name: Optional[str] = None
#     detail: Optional[str] = None
#     phone: Optional[str] = None

class InvoiceIn(BaseModel):
    id: Optional[str] = None
    generateInvoice: Optional[bool] = True
    billDate: Optional[str] = None
    billFrom: Optional[Dict[str, Any]] = None  # Can be replaced with a detailed model if needed
    billTo: Optional[Dict[str, Any]] = None
    orderIds: Optional[List[str]] = None
    createdAt: Optional[str] = None
    paymentMode: Optional[str] = None
    paymentStatus: Optional[str] = "pending"
    totalAmount: Optional[float] = 0.0
    advancePaid: Optional[float] = 0.0
    balanceAmount: Optional[float] = None