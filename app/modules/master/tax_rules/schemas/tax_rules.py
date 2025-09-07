from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaxRuleIn(BaseModel):
    name: str                      # GST, VAT, Service Tax
    code: str                      # e.g. "GST18", "VAT20"
    percentage: float              # 18.0
    region: Optional[str] = None   # e.g. "IN", "EU", or state code
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: bool = True

class TaxRuleOut(TaxRuleIn):
    id: str
