
from fastapi import APIRouter, HTTPException, status
from textwrap import dedent
import logging

from app.modules.website.quote.schemas.quote import (
    WebsiteQuoteIn,
    WebsiteQuoteResponse,
)
from app.modules.website.quote.services.quote_service import (
    QuotePersistenceError,
    QuoteServiceError,
    quote_service,
)
from app.services import mail_service

from config import settings

logger = logging.getLogger(__name__)

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
        result = await quote_service.create_quote(
            name=payload.name,
            phone=payload.phone,
            home_type=payload.homeType,
        )

        try: 

            body = dedent(f"""
                NEW HOME INTERIOR QUOTE REQUEST
                ========================================

                A customer has submitted a quote request through the website.

                CUSTOMER DETAILS
                ----------------------------------------
                Name          : {payload.name}
                Mobile        : {payload.phone}
                Home Type     : {payload.homeType}

                QUOTE DETAILS
                ----------------------------------------
                Quote ID      : {result["quoteId"]}
                Submitted At  : {result["createdAt"]}

                NEXT ACTION
                ----------------------------------------
                Please contact the customer to discuss their home interior
                requirements and provide a personalised quotation.

                ----------------------------------------
                This is an automated notification from your website.
            """).strip()

            mail_service.send_email(
                subject="Artisan studios - New Home Interior Quote Request",
                recipients=[settings.INQUIRY_EMAIL],
                body=body,
            )
        except Exception as exc:
            logger.error(
                "Failed to send quote request email notification: %s",
                str(exc),
            )


        return result

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
