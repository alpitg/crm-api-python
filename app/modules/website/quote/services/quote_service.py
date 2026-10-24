
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import PyMongoError

from app.db.mongo import db


# ============================================================
# COLLECTIONS
# ============================================================

quotes_collection = db["website_quotes"]


# ============================================================
# EXCEPTIONS
# ============================================================

class QuoteServiceError(Exception):
    """Raised when a quote request cannot be processed."""


class QuotePersistenceError(Exception):
    """Raised when a quote cannot be saved to the database."""


# ============================================================
# SERVICE
# ============================================================

class QuoteService:
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def create_quote(
        self,
        name: str,
        phone: str,
        home_type: str,
    ) -> dict[str, Any]:
        """
        Create and persist a home interior quote request.

        A successful response is returned only after MongoDB
        confirms that the quote document was inserted.
        """

        normalized_name = " ".join(name.split())
        normalized_phone = phone.strip()

        if len(normalized_name) < 2:
            raise QuoteServiceError(
                "Please provide a valid name."
            )

        if not normalized_phone.isdigit():
            raise QuoteServiceError(
                "Please provide a valid mobile number."
            )

        if (
            len(normalized_phone) != 10
            or normalized_phone[0] not in "6789"
        ):
            raise QuoteServiceError(
                "Please provide a valid 10-digit Indian mobile number."
            )

        allowed_home_types = {
            "1 BHK",
            "2 BHK",
            "3 BHK",
            "4+ BHK",
            "Villa",
        }

        if home_type not in allowed_home_types:
            raise QuoteServiceError(
                "Please select a valid home type."
            )

        now = self._now()

        quote_document = {
            "name": normalized_name,
            "phone": normalized_phone,
            "homeType": home_type,
            "status": "new",
            "source": "website",
            "createdAt": now,
            "updatedAt": now,
        }

        try:
            result = await quotes_collection.insert_one(
                quote_document
            )

        except PyMongoError as exc:
            raise QuotePersistenceError(
                "Unable to save the quote request."
            ) from exc

        return {
            "success": True,
            "message": (
                "Your quote request has been submitted successfully. "
                "Our design team will contact you shortly."
            ),
            "quoteId": str(result.inserted_id),
            "createdAt": now,
        }


# ============================================================
# INSTANCE
# ============================================================

quote_service = QuoteService()
