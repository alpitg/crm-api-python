
from fastapi import APIRouter, HTTPException, status

from app.modules.website.quote.schemas.quote import (
    WebsiteQuoteIn,
    WebsiteQuoteResponse,
)
from app.modules.website.quote.services.quote_service import (
    QuotePersistenceError,
    QuoteServiceError,
    quote_service,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# CREATE WEBSITE QUOTE
# ============================================================

@router.post(
    "",
    response_model=WebsiteQuoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_website_quote(
    payload: WebsiteQuoteIn,
):
    """
    Submit a home interior quote request.

    Request body:
        {
            "name": "Rahul Sharma",
            "phone": "9876543210",
            "homeType": "2 BHK"
        }

    Success response:
        {
            "success": true,
            "message": "Your quote request has been submitted successfully.",
            "quoteId": "...",
            "createdAt": "..."
        }
    """

    try:
        return await quote_service.create_quote(
            name=payload.name,
            phone=payload.phone,
            home_type=payload.homeType,
        )

    except QuoteServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except QuotePersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "We couldn't submit your quote request right now. "
                "Please try again later."
            ),
        ) from exc
