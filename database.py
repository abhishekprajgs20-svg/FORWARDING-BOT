from motor.motor_asyncio import AsyncIOMotorClient
from config import Config

class Database:
    def __init__(self, uri):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client["forwarding_bot"]
        self.users = self.db["users"]

    async def add_user(self, user_id: int):
        await self.users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

    async def remove_user(self, user_id: int):
        await self.users.delete_one({"user_id": user_id})

    async def is_user_authorized(self, user_id: int) -> bool:
        if user_id == Config.ADMIN_ID:
            return True
        user = await self.users.find_one({"user_id": user_id})
        return bool(user)

    async def get_all_users(self):
        cursor = self.users.find({})
        return [doc["user_id"] async for doc in cursor]

db = Database(Config.MONGO_URI)
