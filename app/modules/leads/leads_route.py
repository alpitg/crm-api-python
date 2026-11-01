import asyncio
import re
from math import ceil
from datetime import datetime, timezone
from textwrap import dedent

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from pymongo import ReturnDocument
import logging

from app.db.mongo import db
from app.modules.leads.schemas.leads import (
    GetLeadsParams,
    LeadIn,
    LeadOut,
    PaginatedLeads,
)
from app.services import mail_service
from app.utils.auth_utils import authenticate

from config import settings

logger = logging.getLogger(__name__)

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)

public_router = APIRouter()


collection = db["leads"]

# Fields the client may sort by (frontend name -> Mongo field)
SORT_FIELDS = {
    "createdAt": "createdAt",
    "createdOn": "createdAt",  # alias used by the current frontend
    "value": "value",
    "name": "name",
    "status": "status",
}


# ---------- Helpers ----------
def to_object_id(id: str) -> ObjectId:
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return ObjectId(id)


def to_lead_out(doc: dict) -> LeadOut:
    return LeadOut(
        id=str(doc["_id"]),
        name=doc.get("name", ""),
        company=doc.get("company"),
        email=doc.get("email"),
        mobile=doc.get("mobile"),
        source=doc.get("source"),
        status=doc.get("status", "new"),
        value=doc.get("value", 0),
        owner=doc.get("owner"),
        description=doc.get("description"),
        isActive=doc.get("isActive", True),
        createdAt=doc.get("createdAt"),
        updatedAt=doc.get("updatedAt"),
    )


def parse_sort(sort: str | None) -> list[tuple[str, int]]:
    """Accepts "createdAt desc", "value asc", or the legacy "newest" / "oldest"."""
    field, direction = "createdAt", -1  # default: newest first

    if sort in ("newest", "oldest"):
        direction = -1 if sort == "newest" else 1
    elif sort:
        parts = sort.split()
        field = SORT_FIELDS.get(parts[0], "createdAt")
        if len(parts) > 1 and parts[1].lower() == "asc":
            direction = 1
        else:
            direction = -1

    # _id as tie-breaker keeps pagination stable when values repeat
    return [(field, direction), ("_id", direction)]


# ---------- Routes ----------
@router.post("/search", response_model=PaginatedLeads)
async def search_leads(filters: GetLeadsParams = Body(...)):
    page = filters.page or 1
    page_size = filters.pageSize or 10
    skip = (page - 1) * page_size

    # Build query dynamically
    query: dict = {}
    if filters.searchText:
        text = filters.searchText.strip()
        pattern = {"$regex": re.escape(text), "$options": "i"}
        conditions = [
            {"name": pattern},
            {"company": pattern},
            {"email": pattern},
            {"mobile": pattern},
        ]
        if ObjectId.is_valid(text):  # allow searching by lead id
            conditions.append({"_id": ObjectId(text)})
        query["$or"] = conditions

    if filters.status:
        query["status"] = filters.status.value

    total_leads = await collection.count_documents(query)

    cursor = (
        collection.find(query)
        .sort(parse_sort(filters.sort))
        .skip(skip)
        .limit(page_size)
    )
    items = [to_lead_out(lead) async for lead in cursor]

    return PaginatedLeads(
        total=total_leads,
        page=page,
        pageSize=page_size,
        pages=ceil(total_leads / page_size) if total_leads > 0 else 1,
        items=items,
    )


@router.get("/details/{id}", response_model=LeadOut)
async def get_lead(id: str):
    lead = await collection.find_one({"_id": to_object_id(id)})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return to_lead_out(lead)


@public_router.post("", response_model=LeadOut)
# @router.post("", response_model=LeadOut)
async def create_lead(payload: LeadIn):
    now = datetime.now(timezone.utc)
    lead = {
        **payload.model_dump(mode="json"),  # stores status as its string value
        "createdAt": now,
        "updatedAt": now,
    }
    result = await collection.insert_one(lead)
    lead["_id"] = result.inserted_id


    try: 

        body = dedent(f"""
            NEW HOME INTERIOR QUOTE REQUEST
            ========================================

            A customer has submitted a quote request through the website.

            CUSTOMER DETAILS
            ----------------------------------------
            Name          : {payload.name}
            Mobile        : {payload.mobile}
            Quote Details : {payload.quoteDetails}

            QUOTE DETAILS
            ----------------------------------------
            Quote ID      : {lead["_id"]}
            Submitted At  : {lead["createdAt"]}

            NEXT ACTION
            ----------------------------------------
            Please contact the customer to discuss their home interior
            requirements and provide a personalised quotation.

            ----------------------------------------
            This is an automated notification from your website.
        """).strip()

        # Send email notification in a separate thread to avoid blocking the main thread
        asyncio.create_task(
            asyncio.to_thread(
                mail_service.send_email,
                subject="Artisan Studios - New Home Interior Quote Request",
                recipients=[
                    email.strip()
                    for email in settings.INQUIRY_EMAIL.split(",")
                    if email.strip()
                ],
                body=body,
            )
        )
    except Exception as exc:
        logger.error(
            "Failed to send quote request email notification: %s",
            str(exc),
        )


    return to_lead_out(lead)


@router.put("/details/{id}", response_model=LeadOut)
async def update_lead(id: str, payload: LeadIn):
    updated_lead = await collection.find_one_and_update(
        {"_id": to_object_id(id)},
        {
            "$set": {
                **payload.model_dump(mode="json"),
                "updatedAt": datetime.now(timezone.utc),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not updated_lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return to_lead_out(updated_lead)


@router.delete("/details/{id}")
async def delete_lead(id: str):
    result = await collection.delete_one({"_id": to_object_id(id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}