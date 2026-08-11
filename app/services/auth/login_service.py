from app.db.mongo import db

customers_collection = db["customers"]

async def login_customer(
    mobile: str,
):
    customer = await customers_collection.find_one(
        {
            "mobile": mobile,
            "isActive": True,
        }
    )

    if not customer:
        return None

    return customer