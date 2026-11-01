from asyncio import gather
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.db.mongo import db
from app.modules.leads.leads_route import to_lead_out
from app.modules.leads.schemas.leads import LeadOut, LeadStatus
from app.utils.auth_utils import authenticate

router = APIRouter(
    dependencies=[Depends(authenticate)]  # ✅ applies to all routes
)
leads_collection = db["leads"]
followups_collection = db["lead_followups"]

WINDOW_DAYS = 7

# "Qualified" = has reached the qualified stage or beyond (and not lost)
QUALIFIED_STATUSES = [
    LeadStatus.qualified.value,
    LeadStatus.proposal.value,
    LeadStatus.won.value,
]
# "Open pipeline" = deals still in progress
OPEN_STATUSES = [
    LeadStatus.new.value,
    LeadStatus.contacted.value,
    LeadStatus.qualified.value,
    LeadStatus.proposal.value,
]
EMPTY_WINDOW = {"total": 0, "qualified": 0, "won": 0, "openValue": 0}


# ---------- Response models ----------
class StatOut(BaseModel):
    value: float
    changePercent: Optional[float] = None  # None when there is no previous data


class LeadsStatsOut(BaseModel):
    totalLeads: StatOut
    qualifiedLeads: StatOut
    conversionRate: StatOut  # percentage, won / total leads
    pipelineValue: StatOut  # sum of value for open leads


class PipelineStageOut(BaseModel):
    status: LeadStatus
    count: int
    value: float


class FollowUpOut(BaseModel):
    id: str
    title: str
    leadId: str
    leadName: Optional[str] = None
    dueAt: datetime
    isOverdue: bool


class LeadsDashboardOut(BaseModel):
    stats: LeadsStatsOut
    pipeline: List[PipelineStageOut]
    followUps: List[FollowUpOut]
    followUpsPending: int
    recentLeads: List[LeadOut]


# ---------- Helpers ----------
def pct_change(current: float, previous: float) -> Optional[float]:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def rate(part: float, total: float) -> float:
    return round(part / total * 100, 1) if total else 0.0


def as_utc(value: datetime) -> datetime:
    # Mongo returns naive datetimes unless the client is tz-aware
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# ---------- Routes ----------
@router.get("", response_model=LeadsDashboardOut)
async def get_leads_dashboard(
    recentLimit: int = Query(8, ge=1, le=20),
    followUpLimit: int = Query(5, ge=1, le=20),
):
    """
    One call for the whole CRM dashboard.

    changePercent compares leads created in the last 7 days with the 7 days
    before that. The headline values (value) are all-time / current totals.
    """
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=WINDOW_DAYS)
    previous_start = now - timedelta(days=WINDOW_DAYS * 2)

    by_status_pipeline = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "value": {"$sum": "$value"},
            }
        }
    ]

    by_window_pipeline = [
        {"$match": {"createdAt": {"$gte": previous_start}}},
        {
            "$group": {
                "_id": {
                    "$cond": [{"$gte": ["$createdAt", current_start]}, "current", "previous"]
                },
                "total": {"$sum": 1},
                "qualified": {
                    "$sum": {"$cond": [{"$in": ["$status", QUALIFIED_STATUSES]}, 1, 0]}
                },
                "won": {"$sum": {"$cond": [{"$eq": ["$status", "won"]}, 1, 0]}},
                "openValue": {
                    "$sum": {"$cond": [{"$in": ["$status", OPEN_STATUSES]}, "$value", 0]}
                },
            }
        },
    ]

    status_rows, window_rows, recent_docs, followup_docs, pending_count = await gather(
        leads_collection.aggregate(by_status_pipeline).to_list(length=None),
        leads_collection.aggregate(by_window_pipeline).to_list(length=None),
        leads_collection.find()
        .sort([("createdAt", -1), ("_id", -1)])
        .limit(recentLimit)
        .to_list(length=recentLimit),
        followups_collection.find({"isDone": {"$ne": True}})
        .sort("dueAt", 1)
        .limit(followUpLimit)
        .to_list(length=followUpLimit),
        followups_collection.count_documents({"isDone": {"$ne": True}}),
    )

    # ----- Pipeline (all statuses, zero-filled, in funnel order) -----
    by_status = {row["_id"]: row for row in status_rows}
    pipeline = [
        PipelineStageOut(
            status=status,
            count=by_status.get(status.value, {}).get("count", 0),
            value=by_status.get(status.value, {}).get("value", 0),
        )
        for status in LeadStatus
    ]

    # ----- Stats -----
    total_leads = sum(stage.count for stage in pipeline)
    qualified_total = sum(by_status.get(s, {}).get("count", 0) for s in QUALIFIED_STATUSES)
    won_total = by_status.get("won", {}).get("count", 0)
    open_value = sum(by_status.get(s, {}).get("value", 0) for s in OPEN_STATUSES)

    windows = {row["_id"]: row for row in window_rows}
    current = windows.get("current", EMPTY_WINDOW)
    previous = windows.get("previous", EMPTY_WINDOW)

    stats = LeadsStatsOut(
        totalLeads=StatOut(
            value=total_leads,
            changePercent=pct_change(current["total"], previous["total"]),
        ),
        qualifiedLeads=StatOut(
            value=qualified_total,
            changePercent=pct_change(current["qualified"], previous["qualified"]),
        ),
        conversionRate=StatOut(
            value=rate(won_total, total_leads),
            changePercent=pct_change(
                rate(current["won"], current["total"]),
                rate(previous["won"], previous["total"]),
            ),
        ),
        pipelineValue=StatOut(
            value=open_value,
            changePercent=pct_change(current["openValue"], previous["openValue"]),
        ),
    )

    # ----- Follow-ups -----
    follow_ups = []
    for doc in followup_docs:
        due_at = as_utc(doc["dueAt"])
        follow_ups.append(
            FollowUpOut(
                id=str(doc["_id"]),
                title=doc.get("title", ""),
                leadId=str(doc.get("leadId", "")),
                leadName=doc.get("leadName"),
                dueAt=due_at,
                isOverdue=due_at < now,
            )
        )

    return LeadsDashboardOut(
        stats=stats,
        pipeline=pipeline,
        followUps=follow_ups,
        followUpsPending=pending_count,
        recentLeads=[to_lead_out(doc) for doc in recent_docs],
    )