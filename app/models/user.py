from app.db.mongo import db
from bson import ObjectId

collection = db["users"]

async def create_user(user_data: dict):
    result = await collection.insert_one(user_data)
    user_data["id"] = str(result.inserted_id)
    return user_data

async def get_user_by_email(email: str):
    user = await collection.find_one({"email": email})
    if user:
        user["id"] = str(user["_id"])
    return user
