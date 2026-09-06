import os

class Config:
    API_ID = int(os.environ.get("API_ID", "123456"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_URI = os.environ.get("MONGO_URI", "")
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))
