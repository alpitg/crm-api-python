import os
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

print("MongoDB URL:", MONGO_URL)

if MONGO_URL.startswith("mongodb+srv://"):
    client = AsyncIOMotorClient(
        MONGO_URL,
        tlsCAFile=certifi.where()
    )
else:
    client = AsyncIOMotorClient(MONGO_URL)

db = client["artisanstudios_db"]
