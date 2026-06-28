import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration - CORRECT FORMAT
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 6407498844))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@smyard")
DISCUSSION_GROUP_ID = os.getenv("DISCUSSION_GROUP_ID", "-1002777496302")
DISCUSSION_GROUP = os.getenv("DISCUSSION_GROUP", "@smyardchat")
print(f"✅ Discussion Group: {DISCUSSION_GROUP}"
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "-1002861193688")
print(f"✅ Stock Channel ID: {STOCK_CHANNEL_ID}")
ESCROW_LOG_CHANNEL_ID = os.getenv("ESCROW_LOG_CHANNEL_ID", "-1002872620027")  # Add to .env
print(f"✅ Escrow Log Channel ID: {ESCROW_LOG_CHANNEL_ID}")

# Button Templates
BUTTON_TEMPLATES = [
    {"text": "?? Screenshots", "url": "https://t.me/smyardsgallary/116"},
    {"text": "?? Place Order???? Start Escrow", "url": "https://t.me/Escrow_Log/7"},
    {"text": "?? Official Website", "url": "https://smyards.com"},
    {"text": "?? Contact Admin", "url": "https://t.me/smyards"},
    {"text": "?? Browse Listed Accounts", "url": "https://t.me/+I4O0K7h-jgs4ZDI0"},
    {"text": "?? Sell your own SM Account", "url": "https://t.me/c/2861193688/6"},
    {"text": "?? Feedback & Successful Transactions", "url": "https://t.me/Escrow_Log"}
]

# Platform Options
PLATFORMS = ["YouTube", "Instagram", "Facebook", "TikTok", "Twitter", "Telegram", "Other"]
ACCOUNT_TYPES = ["Monetized Channel", "Verified Account", "Personal Account", "Business Page", "Group"]