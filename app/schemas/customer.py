from pydantic import BaseModel, EmailStr
from typing import Optional

class Contact(BaseModel):
    phone: str
    email: Optional[EmailStr] = None

class BillingAddress(BaseModel):
    street: str
    city: str
    state: str
    postcode: str
    country: str

class CustomerIn(BaseModel):
    name: str
    contact: Contact
    billingAddress: BillingAddress
    is_active: Optional[bool] = True

class CustomerOut(CustomerIn):
    id: str
