from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth.token_service import (
    get_current_customer,
    logout_customer,
    refresh_access_token,
)

from app.db.mongo import db

router = APIRouter()

address_collection = db["customer_addresses"]
customers_collection = db["customers"]


class CustomerProfileResponse(BaseModel):
    id: str
    name: str
    email: str
    description: Optional[str] = None
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class UpdateCustomerProfileRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class CustomerProfileMutationResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    customer: CustomerProfileResponse


# ==================================================
# CONSTANTS
# ==================================================

ADDRESS_TYPES = {
    "home",
    "work",
    "other",
}


# ==================================================
# HELPERS
# ==================================================

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_object_id(value: str, field_name: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}.",
        )

    return ObjectId(value)


def serialize_address(address: dict) -> dict:
    return {
        "id": str(address["_id"]),
        "customerId": str(address["customerId"]),
        "name": address.get("name"),
        "mobile": address.get("mobile"),
        "addressType": address.get("addressType", "home"),
        "addressLine1": address.get("addressLine1"),
        "addressLine2": address.get("addressLine2"),
        "landmark": address.get("landmark"),
        "city": address.get("city"),
        "state": address.get("state"),
        "pincode": address.get("pincode"),
        "isDefault": bool(address.get("isDefault", False)),
        "createdAt": address.get("createdAt"),
        "updatedAt": address.get("updatedAt"),
    }


# ============================================================
# HELPERS
# ============================================================


def serialize_customer_profile(customer: dict) -> CustomerProfileResponse:
    """
    Convert MongoDB customer document into the public profile response.
    """

    return CustomerProfileResponse(
        id=str(customer.get("id") or customer.get("_id")),
        name=customer.get("name") or "",
        email=customer.get("email") or "",
        mobile=customer.get("mobile"),
        description=customer.get("description"),
        isActive=customer.get("isActive", True),
        createdAt=customer.get("createdAt"),
        updatedAt=customer.get("updatedAt"),
    )


# ==================================================
# REQUEST SCHEMAS
# ==================================================

class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=1,
    )


class AddressCreateRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    mobile: str = Field(
        ...,
        min_length=10,
        max_length=15,
    )

    addressType: str = Field(
        default="home",
    )

    addressLine1: str = Field(
        ...,
        min_length=3,
        max_length=250,
    )

    addressLine2: Optional[str] = Field(
        default=None,
        max_length=250,
    )

    landmark: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    pincode: str = Field(
        ...,
        min_length=4,
        max_length=10,
    )

    isDefault: bool = False


class AddressUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    mobile: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=15,
    )

    addressType: Optional[str] = None

    addressLine1: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=250,
    )

    addressLine2: Optional[str] = Field(
        default=None,
        max_length=250,
    )

    landmark: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    city: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    state: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    pincode: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=10,
    )

    isDefault: Optional[bool] = None


# ==================================================
# REFRESH TOKEN
# ==================================================

@router.post("/refresh")
async def refresh_token(
    payload: RefreshTokenRequest,
):
    """
    Generate a new access token using refresh token.
    """

    try:
        result = refresh_access_token(
            refresh_token=payload.refresh_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get(
                "message",
                "Invalid or expired refresh token.",
            ),
        )

    return {
        "success": True,
        "message": "Token refreshed successfully.",
        "access_token": result["access_token"],
        "refresh_token": result.get(
            "refresh_token",
            payload.refresh_token,
        ),
        "token_type": "bearer",
    }


# ==================================================
# CURRENT USER
# ==================================================

@router.get("/me")
async def get_current_user(
    customer=Depends(get_current_customer),
):
    """
    Get currently authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return {
        "success": True,
        "user": {
            "id": str(customer["_id"]),
            "mobile": customer.get("mobile"),
            "name": customer.get("name"),
            "email": customer.get("email"),
        },
    }


# ==================================================
# GET ADDRESSES
# ==================================================

@router.get("/me/addresses")
async def get_my_addresses(
    customer=Depends(get_current_customer)
):
    """
    Get all addresses belonging to the authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    customer_id = customer["_id"]

    cursor = (
        db["customer_addresses"]
        .find(
            {
                "customerId": customer_id,
            }
        )
        .sort(
            [
                ("isDefault", -1),
                ("updatedAt", -1),
            ]
        )
    )

    addresses = await cursor.to_list(length=None)

    return {
        "success": True,
        "addresses": [
            serialize_address(address)
            for address in addresses
        ],
    }


# ==================================================
# CREATE ADDRESS
# ==================================================

@router.post("/me/addresses", status_code=status.HTTP_201_CREATED)
async def create_address(
    payload: AddressCreateRequest,
    customer=Depends(get_current_customer)
):
    """
    Create a new address for the authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if payload.addressType not in ADDRESS_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid address type.",
        )

    customer_id = customer["_id"]

    existing_count = await address_collection.count_documents(
        {
            "customerId": customer_id,
        }
    )

    # First address should automatically become default.
    should_be_default = (
        payload.isDefault
        or existing_count == 0
    )

    now = utc_now()

    address = {
        "customerId": customer_id,
        "name": payload.name.strip(),
        "mobile": payload.mobile.strip(),
        "addressType": payload.addressType,
        "addressLine1": payload.addressLine1.strip(),
        "addressLine2": (
            payload.addressLine2.strip()
            if payload.addressLine2
            else None
        ),
        "landmark": (
            payload.landmark.strip()
            if payload.landmark
            else None
        ),
        "city": payload.city.strip(),
        "state": payload.state.strip(),
        "pincode": payload.pincode.strip(),
        "isDefault": should_be_default,
        "createdAt": now,
        "updatedAt": now,
    }

    # If this address becomes default,
    # remove default from all other addresses.
    if should_be_default:
        await address_collection.update_many(
            {
                "customerId": customer_id,
                "isDefault": True,
            },
            {
                "$set": {
                    "isDefault": False,
                    "updatedAt": now,
                }
            },
        )

    result = await address_collection.insert_one(address)

    address["_id"] = result.inserted_id

    return {
        "success": True,
        "message": "Address added successfully.",
        "address": serialize_address(address),
    }


# ==================================================
# UPDATE ADDRESS
# ==================================================

@router.patch("/me/addresses/{address_id}")
async def update_address(
    address_id: str,
    payload: AddressUpdateRequest,
    customer=Depends(get_current_customer)
):
    """
    Update an address belonging to the authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    object_id = validate_object_id(
        address_id,
        "address ID",
    )

    customer_id = customer["_id"]

    existing_address = await address_collection.find_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    if not existing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    update_data = payload.model_dump(
        exclude_unset=True,
    )

    if not update_data:
        return {
            "success": True,
            "message": "No changes provided.",
            "address": serialize_address(existing_address),
        }

    if (
        "addressType" in update_data
        and update_data["addressType"] not in ADDRESS_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid address type.",
        )

    # Trim string values.
    for key, value in update_data.items():
        if isinstance(value, str):
            update_data[key] = value.strip()

    now = utc_now()

    # If making this address default,
    # remove default from all other addresses.
    if update_data.get("isDefault") is True:
        await address_collection.update_many(
            {
                "customerId": customer_id,
                "_id": {
                    "$ne": object_id,
                },
                "isDefault": True,
            },
            {
                "$set": {
                    "isDefault": False,
                    "updatedAt": now,
                }
            },
        )

    update_data["updatedAt"] = now

    await address_collection.update_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        },
        {
            "$set": update_data,
        },
    )

    updated_address = await address_collection.find_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    return {
        "success": True,
        "message": "Address updated successfully.",
        "address": serialize_address(updated_address),
    }


# ==================================================
# DELETE ADDRESS
# ==================================================

@router.delete("/me/addresses/{address_id}")
async def delete_address(
    address_id: str,
    customer=Depends(get_current_customer)
):
    """
    Delete an address belonging to the authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    object_id = validate_object_id(
        address_id,
        "address ID",
    )

    customer_id = customer["_id"]

    address = await address_collection.find_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    was_default = bool(
        address.get("isDefault", False)
    )

    await address_collection.delete_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    # If default address was deleted,
    # automatically promote another address.
    if was_default:
        next_address = await address_collection.find_one(
            {
                "customerId": customer_id,
            },
            sort=[
                ("updatedAt", -1),
            ],
        )

        if next_address:
            await address_collection.update_one(
                {
                    "_id": next_address["_id"],
                    "customerId": customer_id,
                },
                {
                    "$set": {
                        "isDefault": True,
                        "updatedAt": utc_now(),
                    }
                },
            )

    return {
        "success": True,
        "message": "Address deleted successfully.",
    }


# ==================================================
# SET DEFAULT ADDRESS
# ==================================================

@router.post("/me/addresses/{address_id}/default")
async def set_default_address(
    address_id: str,
    customer=Depends(get_current_customer)
):
    """
    Set an address as the customer's default address.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    object_id = validate_object_id(
        address_id,
        "address ID",
    )

    customer_id = customer["_id"]

    address = await address_collection.find_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found.",
        )

    now = utc_now()

    # Remove default from all customer addresses.
    await address_collection.update_many(
        {
            "customerId": customer_id,
            "_id": {
                "$ne": object_id,
            },
        },
        {
            "$set": {
                "isDefault": False,
                "updatedAt": now,
            }
        },
    )

    # Set requested address as default.
    await address_collection.update_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        },
        {
            "$set": {
                "isDefault": True,
                "updatedAt": now,
            }
        },
    )

    updated_address = await address_collection.find_one(
        {
            "_id": object_id,
            "customerId": customer_id,
        }
    )

    return {
        "success": True,
        "message": "Default address updated successfully.",
        "address": serialize_address(updated_address),
    }





# ============================================================
# GET PROFILE
# ============================================================


@router.get(
    "/profile",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def get_customer_profile(
    current_customer: dict = Depends(get_current_customer),
):
    """
    Get the currently authenticated customer's profile.
    """

    customer_id = current_customer.get("id")

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer authentication.",
        )

    customer = await customers_collection.find_one(
        {"id": customer_id}
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found.",
        )

    return serialize_customer_profile(customer)


# ============================================================
# UPDATE PROFILE
# ============================================================


@router.patch(
    "/profile",
    response_model=CustomerProfileMutationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_customer_profile(
    payload: UpdateCustomerProfileRequest,
    current_customer: dict = Depends(get_current_customer),
):
    """
    Update the currently authenticated customer's profile.
    """

    customer_id = current_customer.get("id")

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer authentication.",
        )

    customer = await customers_collection.find_one(
        {"id": customer_id}
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found.",
        )

    # ========================================================
    # BUILD UPDATE
    # ========================================================

    update_data = {}

    if payload.name is not None:
        update_data["name"] = payload.name.strip()

    if payload.description is not None:
        update_data["description"] = payload.description.strip()

    # ========================================================
    # NOTHING TO UPDATE
    # ========================================================

    if not update_data:
        return CustomerProfileMutationResponse(
            success=True,
            message="No profile changes were provided.",
            customer=serialize_customer_profile(customer),
        )

    # ========================================================
    # UPDATED AT
    # ========================================================

    update_data["updatedAt"] = datetime.now(timezone.utc)

    # ========================================================
    # UPDATE CUSTOMER
    # ========================================================

    await customers_collection.update_one(
        {"id": customer_id},
        {
            "$set": update_data,
        },
    )

    # ========================================================
    # GET UPDATED CUSTOMER
    # ========================================================

    updated_customer = await customers_collection.find_one(
        {"id": customer_id}
    )

    if not updated_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found after update.",
        )

    return CustomerProfileMutationResponse(
        success=True,
        message="Profile updated successfully.",
        customer=serialize_customer_profile(updated_customer),
    )



# ==================================================
# LOGOUT
# ==================================================

@router.post("/logout")
async def logout(
    customer=Depends(get_current_customer),
):
    """
    Logout currently authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    await logout_customer(
        customer_id=str(customer["_id"]),
    )

    return {
        "success": True,
        "message": "Logged out successfully.",
    }