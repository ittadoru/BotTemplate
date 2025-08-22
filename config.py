import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

DATABASE_URL = os.getenv("DATABASE_URL")

SUPPORT_GROUP_ID = int(os.getenv("SUPPORT_GROUP_ID"))
SUBSCRIBE_TOPIC_ID = int(os.getenv("SUBSCRIBE_TOPIC_ID"))
NEW_USER_TOPIC_ID = int(os.getenv("NEW_USER_TOPIC_ID"))

SHOP_ID = int(os.getenv("SHOP_ID"))
API_KEY = os.getenv("API_KEY")

DOMAIN = os.getenv("DOMAIN")

SUBSCRIPTION_YEARS_FOR_LIFETIME = 100
SUBSCRIPTION_LIFETIME_DAYS = SUBSCRIPTION_YEARS_FOR_LIFETIME * 365

BROADCAST_PROGRESS_UPDATE_INTERVAL = 7
BROADCAST_PER_MESSAGE_DELAY = 0.2