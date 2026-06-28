# -*- coding: utf-8 -*-
import sys
import io
import traceback

# Force UTF-8 encoding for stdout/stderr
if sys.version_info[0] < 3:
    reload(sys)
    sys.setdefaultencoding('utf-8')
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import os
import sqlite3
import json
import logging
from datetime import datetime
from telegram import (
    ParseMode, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputMediaPhoto
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    Filters,
    CallbackContext
)

# Enable logging - AT THE VERY TOP AFTER IMPORTS
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reduce noise from other loggers
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Create file handler for detailed logs
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE_PATH = os.path.join(BASE_DIR, 'bot_debug.log')

file_handler = logging.FileHandler(LOG_FILE_PATH, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

print("=" * 60)
print("?? Debug logging enabled. Check bot_debug.log for details")
print("=" * 60)

# ===== CONFIGURATION =====
from dotenv import load_dotenv
import hashlib
import hmac
import uuid
import threading
from flask import Flask, request as flask_request

print("=" * 60)
print("🆔 SMYARDS BOT - COMPLETE VERSION")
print("=" * 60)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 6407498844))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@smyard")
SCREENSHOT_CHANNEL_ID = os.getenv("SCREENSHOT_CHANNEL_ID", "@smyardsgallary")
DISCUSSION_GROUP_ID = os.getenv("DISCUSSION_GROUP_ID", "-1002777496302")
STOCK_CHANNEL_ID = os.getenv("STOCK_CHANNEL_ID", "-1002861193688")
ESCROW_LOG_CHANNEL_ID = os.getenv("ESCROW_LOG_CHANNEL_ID", "-1002872620027")
MAX_SCREENSHOTS = 10

# Payment addresses (add to your .env file)
COINBASE_ADDRESS = os.getenv("COINBASE_ADDRESS", "")
BINANCE_ADDRESS = os.getenv("BINANCE_ADDRESS", "")
BTC_ADDRESS = os.getenv("BTC_ADDRESS", "")
ETH_ADDRESS = os.getenv("ETH_ADDRESS", "")
USDT_ADDRESS = os.getenv("USDT_ADDRESS", "")
USDC_ADDRESS = os.getenv("USDC_ADDRESS", "")

# Cryptomus payment config
CRYPTOMUS_MERCHANT_ID = os.getenv("CRYPTOMUS_MERCHANT_ID", "99cb6194-bd15-448d-b16a-163d236a25f8")
CRYPTOMUS_API_KEY = os.getenv("CRYPTOMUS_API_KEY", "4e4283c5e7979c9087010ee9ce20f9a597acd7d2")
CRYPTOMUS_WEBHOOK_URL = os.getenv("CRYPTOMUS_WEBHOOK_URL", "https://smyards-production.up.railway.app/cryptomus-webhook")

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not found!")
    exit(1)

print(f"✅ Token: {BOT_TOKEN[:15]}...")
print(f"✅ Owner ID: {OWNER_ID}")
print(f"✅ Main Channel: {CHANNEL_ID}")
print(f"✅ Max Screenshots: {MAX_SCREENSHOTS}")
print("=" * 60)

# Platform Options
PLATFORMS = ["YouTube", "TikTok", "Instagram", "Facebook"]

# YouTube Account Types
YOUTUBE_TYPES = ["Monetized Channel", "Aged Channel", "Gaming Channel", "Organic Channel", "3-Features Enabled Channel"]

# Other platform account types
DEFAULT_TYPES = ["Verified Account", "Personal Account", "Business Account"]

# Database setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_NAME = os.path.join(BASE_DIR, "listings.db")

# ===== CUSTOMER CONVERSATION STATES =====
# Admin states (0-15)
(
    MAIN_MENU, CREATE_PLATFORM, CREATE_TYPE, 
    CREATE_DETAILS, CREATE_PRICE, CREATE_SELLER_CONTACT,
    SCREENSHOT_ASK, SCREENSHOT_UPLOAD, CREATE_CONFIRM,
    MARK_SOLD, ENTER_PRODUCT_ID, ENTER_TXID, ENTER_PAYMENT_METHOD,
    ENTER_ORDER_NUMBER, ADMIN_RELIST_MENU, ADMIN_MARK_SOLD
) = range(16)

# Customer states (15-31)
(
    CUSTOMER_MENU, BUYER_ESCROW_INFO, BUYER_ENTER_PRODUCT_ID,
    BUYER_CONFIRM_PRODUCT, BUYER_PAYMENT_METHODS, BUYER_PAYMENT_INSTRUCTIONS,
    BUYER_CONFIRM_PAYMENT, SELLER_INFO, SELLER_PLATFORM,
    SELLER_TYPE, SELLER_DETAILS, SELLER_PRICE, SELLER_CONTACT,
    SELLER_SCREENSHOTS, SELLER_CONFIRM,
    CUSTOMER_MANAGE_LISTINGS, CUSTOMER_CONFIRM_SOLD
) = range(15, 32)

# Browse / Search states (32-38)
(
    BROWSE_MENU, BROWSE_PLATFORM_LIST, BROWSE_LISTING_DETAIL,
    BROWSE_FILTER_MENU, BROWSE_FILTER_PRICE, BROWSE_FILTER_SUBS,
    BROWSE_SEARCH_KEYWORD
) = range(32, 39)

# Order Management states - Stage 1 (39-42)
(
    ADMIN_ORDERS_PANEL, ADMIN_ORDER_DETAIL, CUSTOMER_MY_ORDERS, CUSTOMER_ORDER_DETAIL
) = range(39, 43)

# Group link states - Stage 2 (43-44)
(
    ADMIN_ADD_GROUP_LINK, ADMIN_CONFIRM_GROUP_LINK
) = range(43, 45)





# ===== DATABASE FUNCTIONS =====   
def init_database():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL,
        account_type TEXT NOT NULL,
        subscribers INTEGER,
        views INTEGER,
        niche TEXT,
        features TEXT,
        monetization TEXT,
        region TEXT,
        status TEXT,
        price REAL NOT NULL,
        screenshots TEXT,
        seller_contact TEXT,
        status_flag TEXT DEFAULT 'draft',
        published_time DATETIME,
        channel_message_id TEXT,         -- Will hold comma-separated historical IDs
        screenshot_message_id TEXT,
        discussion_message_id TEXT,
        stock_message_id TEXT,
        created_by INTEGER NOT NULL,
        last_bumped_at DATETIME,         -- TRACKS BUMP TIME
        bump_cooldown_days INTEGER DEFAULT 3, -- CUSTOMIZABLE COOLDOWN
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        role TEXT DEFAULT 'owner',
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customer_listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id TEXT UNIQUE NOT NULL,
        platform TEXT NOT NULL,
        account_type TEXT NOT NULL,
        subscribers INTEGER,
        views INTEGER,
        niche TEXT,
        features TEXT,
        monetization TEXT,
        region TEXT,
        status TEXT,
        price REAL NOT NULL,
        screenshots TEXT,
        seller_contact TEXT,
        customer_id INTEGER NOT NULL,
        customer_username TEXT,
        status_flag TEXT DEFAULT 'pending',
        admin_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT UNIQUE NOT NULL,
        product_id TEXT NOT NULL,
        customer_id INTEGER NOT NULL,
        customer_username TEXT,
        platform TEXT NOT NULL,
        total_price REAL NOT NULL,
        escrow_fee REAL NOT NULL,
        amount_to_pay REAL NOT NULL,
        payment_method TEXT NOT NULL,
        payment_address TEXT NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        admin_notified INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('SELECT 1 FROM admins WHERE user_id = ?', (OWNER_ID,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO admins (user_id, username, role) VALUES (?, ?, ?)', 
                       (OWNER_ID, "Owner", "owner"))
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DATABASE_NAME}")
	# Call migration to add new order management columns
    add_orders_table_columns()
    
    # Run migrations for safety...
    
    # Run migrations for safety if upgrading an existing live DB file
    run_db_migrations()
    
    # Add seller_contact column if it doesn't exist
    add_seller_contact_column()

def run_db_migrations():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(listings)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'last_bumped_at' not in columns:
            cursor.execute("ALTER TABLE listings ADD COLUMN last_bumped_at DATETIME")
        if 'bump_cooldown_days' not in columns:
            cursor.execute("ALTER TABLE listings ADD COLUMN bump_cooldown_days INTEGER DEFAULT 3")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Migration error: {e}")
    
def add_seller_contact_column():
    """Add seller_contact column to database if it doesn't exist"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Check if seller_contact column exists
        cursor.execute("PRAGMA table_info(listings)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'seller_contact' not in columns:
            print("➡️ Adding seller_contact column to listings table...")
            cursor.execute("ALTER TABLE listings ADD COLUMN seller_contact TEXT")
            conn.commit()
            print("✅ seller_contact column added")
        
        conn.close()
    except Exception as e:
        print(f"⚠️ Error adding seller_contact column: {e}")

def add_seller_telegram_id_to_listings():
    """Add seller_telegram_id field to track actual seller for notifications."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(listings)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'seller_telegram_id' not in columns:
            cursor.execute("ALTER TABLE listings ADD COLUMN seller_telegram_id INTEGER")
            logger.info("✅ Added seller_telegram_id to listings table")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding seller_telegram_id: {e}")

def add_transactions_log_table():
    """Add transactions_log table for completed transactions."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            product_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            seller_name TEXT NOT NULL,
            buyer_name TEXT NOT NULL,
            price REAL NOT NULL,
            txid TEXT,
            status TEXT DEFAULT 'completed',
            completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ transactions_log table ready")
    except Exception as e:
        logger.error(f"Error creating transactions_log table: {e}")

def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Allow dict-like access
    return conn

def is_admin(user_id):
    """Check if user is admin"""
    if user_id == OWNER_ID:
        return True
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def generate_order_number(platform):
    """Generate unique order number"""
    platform_codes = {
        'YouTube': 'YT',
        'TikTok': 'TT', 
        'Instagram': 'IG',
        'Facebook': 'FB'
    }
    
    platform_code = platform_codes.get(platform, 'ORD')
    
    conn = get_connection()
    cursor = conn.cursor()
    # FIXED: Safe SQL query with parameter
    cursor.execute("SELECT COUNT(*) FROM orders WHERE order_number LIKE ?", (f"{platform_code}#%",))
    count = cursor.fetchone()[0] + 1
    conn.close()
    
    return f"{platform_code}#{count:04d}"

def calculate_escrow_fee(price):
    """Calculate escrow fee (5% with $5 minimum)"""
    fee = price * 0.05
    return max(fee, 5.0)

def format_number(val):
    """Formats a number with commas (e.g., 4700 -> 4,700)"""
    if val is None or str(val).lower() == 'n/a':
        return 'N/A'
    try:
        # Remove existing commas first, then convert to float/int
        clean_val = str(val).replace(',', '')
        return f"{int(float(clean_val)):,}"
    except (ValueError, TypeError):
        return str(val)


# ===== CRYPTOMUS PAYMENT INTEGRATION =====

def create_cryptomus_invoice(order_id, amount_usd, product_id):
    """Create a Cryptomus payment invoice and return the payment URL."""
    import base64, json as _json
    
    payload = {
        "amount": f"{amount_usd:.2f}",
        "currency": "USD",
        "order_id": order_id,
        "url_callback": CRYPTOMUS_WEBHOOK_URL,
        "url_return": "https://t.me/smyards_bot",
        "url_success": "https://t.me/smyards_bot",
        "is_payment_multiple": False,
        "lifetime": 3600,
        "to_currency": "USDT",
        "additional_data": product_id,
    }

    payload_json = _json.dumps(payload)
    payload_b64 = base64.b64encode(payload_json.encode()).decode()
    sign = hashlib.md5(f"{payload_b64}{CRYPTOMUS_API_KEY}".encode()).hexdigest()

    headers = {
        "merchant": CRYPTOMUS_MERCHANT_ID,
        "sign": sign,
        "Content-Type": "application/json",
    }

    try:
        import requests as _requests
        resp = _requests.post(
            "https://api.cryptomus.com/v1/payment",
            json=payload,
            headers=headers,
            timeout=15
        )
        data = resp.json()
        if data.get("state") == 0:
            return data["result"]["url"]
        else:
            logger.error(f"Cryptomus invoice error: {data}")
            return None
    except Exception as e:
        logger.error(f"Cryptomus API request failed: {e}")
        return None


def verify_cryptomus_webhook(data: dict) -> bool:
    """Verify that the webhook actually came from Cryptomus."""
    import base64, json as _json
    received_sign = data.get("sign")
    if not received_sign:
        return False
    payload = {k: v for k, v in data.items() if k != "sign"}
    payload_json = _json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.b64encode(payload_json.encode()).decode()
    expected_sign = hashlib.md5(f"{payload_b64}{CRYPTOMUS_API_KEY}".encode()).hexdigest()
    return hmac.compare_digest(received_sign, expected_sign)


# Flask app for receiving Cryptomus webhooks
flask_app = Flask(__name__)
_bot_instance = None  # set in main()

@flask_app.route("/cryptomus-webhook", methods=["POST"])
def cryptomus_webhook():
    """Receive and handle Cryptomus payment confirmation webhooks."""
    import json as _json
    try:
        data = flask_request.get_json(force=True)
        logger.info(f"Cryptomus webhook received: {data}")
        if not verify_cryptomus_webhook(data):
            logger.warning("Cryptomus webhook verification failed!")
            return "FORBIDDEN", 403
        status = data.get("status", "")
        order_id = data.get("order_id", "")
        amount = data.get("amount", "0")
        currency = data.get("currency", "")
        payment_currency = data.get("payment_currency", "")
        if status in ("paid", "paid_over"):
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE orders SET payment_status = 'confirmed', 
                    payment_confirmed_at = CURRENT_TIMESTAMP,
                    payment_method = ? WHERE order_number = ?""",
                    (payment_currency or currency, order_id)
                )
                conn.commit()
                cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_id,))
                order = cursor.fetchone()
                if order:
                    cursor.execute("PRAGMA table_info(orders)")
                    columns = [col[1] for col in cursor.fetchall()]
                    order_dict = dict(zip(columns, order))
            finally:
                conn.close()

            if _bot_instance and order:
                order_db_id = order_dict.get('id', 0)
                
                # ===== NOTIFY ADMIN WITH "ADD GROUP LINK" BUTTON =====
                try:
                    keyboard = [[InlineKeyboardButton("🔗 Add Group Link", callback_data=f"add_group_link_{order_db_id}")]]
                    
                    admin_text = (
                        f"✅ <b>PAYMENT CONFIRMED!</b>\n\n"
                        f"🆔 Order: <code>{order_id}</code>\n"
                        f"💵 Amount: {amount} {currency}\n"
                        f"💳 Paid in: {payment_currency}\n"
                        f"📦 Product: <code>{order_dict.get('product_id', 'N/A')}</code>\n"
                        f"👤 Buyer: @{order_dict.get('customer_username', 'N/A')}\n\n"
                        f"✅ Escrow fee received!\n"
                        f"➡️ Click below to add the deal group link."
                    )
                    
                    _bot_instance.send_message(
                        chat_id=OWNER_ID,
                        text=admin_text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="HTML"
                    )
                    logger.info(f"✅ Admin notified of payment confirmation for {order_id}")
                except Exception as e:
                    logger.error(f"Failed to notify admin of payment: {e}")

                # ===== NOTIFY SELLER =====
                seller_id = order_dict.get('seller_id')
                logger.info(f"[WEBHOOK] Notifying seller. seller_id={seller_id}, OWNER_ID={OWNER_ID}")
                
                if seller_id and seller_id != OWNER_ID:
                    try:
                        seller_text = (
                            f"✅ <b>PAYMENT CONFIRMED FOR YOUR LISTING!</b>\n\n"
                            f"📦 <b>Product:</b> <code>{order_dict.get('product_id')}</code>\n"
                            f"🆔 <b>Order:</b> <code>{order_id}</code>\n"
                            f"💰 <b>Account Price:</b> ${order_dict.get('total_price', 0):,.2f}\n"
                            f"👤 <b>Buyer:</b> @{order_dict.get('customer_username', 'N/A')}\n\n"
                            f"🔗 The deal group link will be shared shortly!\n"
                            f"⏳ Admin is setting up the secure transaction group..."
                        )
                        
                        _bot_instance.send_message(
                            chat_id=seller_id,
                            text=seller_text,
                            parse_mode="HTML"
                        )
                        logger.info(f"[WEBHOOK] ✅ Seller {seller_id} notified of payment confirmation")
                    except Exception as e:
                        logger.error(f"[WEBHOOK] ❌ Failed to notify seller {seller_id}: {e}", exc_info=True)
                else:
                    logger.warning(f"[WEBHOOK] No seller notification: seller_id={seller_id} (admin listing or NULL)")

        return "OK", 200
    except Exception as e:
        logger.error(f"Cryptomus webhook error: {e}")
        return "ERROR", 500


def run_flask():
    """Run Flask in a background thread alongside the Telegram bot."""
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=False, use_reloader=False)

def execute_bump_logic(listing_id, bot):
    """Re-posts a listing to the top of the main channel and updates the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE listing_id = ?", (listing_id,))
    listing = cursor.fetchone()
    conn.close()

    if not listing:
        logger.error(f"Bump failed: listing {listing_id} not found.")
        return False

    # Check cooldown
    if listing['last_bumped_at']:
        last_bump = datetime.strptime(listing['last_bumped_at'].split(".")[0], "%Y-%m-%d %H:%M:%S")
        delta = datetime.utcnow() - last_bump
        allowed_seconds = (listing['bump_cooldown_days'] or 3) * 86400
        if delta.total_seconds() < allowed_seconds:
            logger.warning(f"Bump rejected for {listing_id}: cooldown not expired.")
            return False

    try:
        screenshots = json.loads(listing['screenshots']) if listing['screenshots'] else []
        has_screenshots = len(screenshots) > 0

        subs = format_number(listing['subscribers'])
        views = format_number(listing['views'])
        price = listing['price']
        price_str = str(int(float(price))) if str(price).replace('.', '', 1).isdigit() else str(price)

        post_text = (
            f"<b>🎯 NEW ACCOUNT FOR SALE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>📋 BASIC INFO</b>\n"
            f"• 📱 <b>Platform:</b> {listing['platform']}\n"
            f"• 👤 <b>Type:</b> {listing['account_type']}\n"
            f"• 🌍 <b>Region:</b> {listing['region'] or 'USA'}\n\n"
            f"<b>📊 STATISTICS</b>\n"
            f"• 👥 <b>Subscribers:</b> {subs}\n"
            f"• 👀 <b>Views:</b> {views}\n"
            f"• ✅ <b>Status:</b> {listing['status'] or 'No Strikes'}\n\n"
            f"<b>⚙️ FEATURES</b>\n"
            f"• 🗃️ <b>Niche:</b> {listing['niche'] or 'Mixed'}\n"
            f"• 🔧 <b>Features:</b> {listing['features'] or 'N/A'}\n"
            f"• 💲 <b>Monetization:</b> {listing['monetization'] or 'Enabled'}\n\n"
            f"<b>💰 PRICING</b>\n"
            f"• 💵 <b>Price:</b> ${price_str}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        reply_markup = generate_buttons(
            listing_id=listing['listing_id'],
            seller_contact=listing['seller_contact'],
            stock_message_id=listing['stock_message_id']
        )

        if has_screenshots:
            media_group = []
            for i, photo_id in enumerate(screenshots):
                if i == 0:
                    media_group.append(InputMediaPhoto(media=photo_id, caption=post_text, parse_mode='HTML'))
                else:
                    media_group.append(InputMediaPhoto(media=photo_id))
            bot.send_media_group(chat_id=CHANNEL_ID, media=media_group, timeout=60)
            new_message = bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"<b>🆔 Product ID:</b> <code>{listing['listing_id']}</code>",
                parse_mode='HTML',
                reply_markup=reply_markup,
                timeout=20
            )
        else:
            new_message = bot.send_message(
                chat_id=CHANNEL_ID,
                text=post_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )

        new_msg_id = new_message.message_id
        old_ids = listing['channel_message_id'] or ''
        updated_ids = f"{old_ids},{new_msg_id}".strip(',')

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE listings SET channel_message_id = ?, last_bumped_at = CURRENT_TIMESTAMP WHERE listing_id = ?",
            (updated_ids, listing_id)
        )
        conn.commit()
        conn.close()

        logger.info(f"Bump successful for {listing_id} -> new message ID: {new_msg_id}")
        return True

    except Exception as e:
        logger.error(f"Bump failed for {listing_id}: {e}")
        logger.error(traceback.format_exc())
        return False




    
    
    # ===== EXISTING CUSTOMER FUNCTIONS =====
def customer_view_listings_menu(update, context):
    """Displays active inventory items registered directly under the caller's unique ID."""
    user_id = update.effective_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, platform, price, last_bumped_at, bump_cooldown_days, status_flag 
        FROM listings WHERE created_by = ? AND status_flag = 'published'
        ORDER BY created_at DESC
    """, (user_id,))
    user_items = cursor.fetchall()
    conn.close()
    
    if not user_items:
        text = "📭 **You don't have any active listings on the platform currently.**"
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="customer_main")]]
        update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')
        return CUSTOMER_MENU

    text = "📋 **Your Registered Inventory Assets:**\nSelect an option below to manage optimization properties:"
    keyboard = []
    
    for item in user_items:
        # Calculate scheduling metrics via timestamp conversions
        available = True
        cooldown_msg = ""
        
        if item['last_bumped_at']:
            last_bump = datetime.strptime(item['last_bumped_at'].split(".")[0], "%Y-%m-%d %H:%M:%S")
            delta = datetime.utcnow() - last_bump
            allowed_seconds = item['bump_cooldown_days'] * 86400
            
            if delta.total_seconds() < allowed_seconds:
                available = False
                remaining = allowed_seconds - delta.total_seconds()
                days = int(remaining // 86400)
                hours = int((remaining % 86400) // 3600)
                cooldown_msg = f" (⏳ {days}d {hours}h)"

        bump_status_icon = "🟢" if available else "⏳"
        keyboard.append([
            InlineKeyboardButton(f"{item['listing_id']} - Manage Item", callback_data=f"manage_item_{item['listing_id']}"),
            InlineKeyboardButton(f"{bump_status_icon} Bump{cooldown_msg}", callback_data=f"bump_item_{item['listing_id']}")
        ])
        
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="customer_main")])
    update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')
    return CUSTOMER_MANAGE_LISTINGS


def customer_manage_item_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    
    # 1. Open the Action Menu
    if data.startswith("manage_item_"):
        listing_id = data.replace("manage_item_", "")
        context.user_data["targeted_id"] = listing_id
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status_flag FROM listings WHERE listing_id = ?", (listing_id,))
        live_item = cursor.fetchone()
        conn.close()
        
        # If it is a published live listing, show the tools
        if live_item and live_item['status_flag'] == 'published':
            text = f"⚙️ **Inventory Management Panel:** `[{listing_id}]` \n\nSelect an action below:"
            keyboard = [
                [InlineKeyboardButton("⚡ Bump to Top", callback_data=f"bump_item_{listing_id}")],
                [InlineKeyboardButton("❌ Mark Asset As Sold (External)", callback_data="customer_trigger_sold")],
                [InlineKeyboardButton("🔙 Return to Listings", callback_data="return_listings_view")]
            ]
        else:
            # If it is still pending admin approval
            text = f"⏳ **Status View:** `[{listing_id}]`\n\nThis listing is currently Pending Admin Approval. It will be manageable once it goes live."
            keyboard = [[InlineKeyboardButton("🔙 Return to Listings", callback_data="return_listings_view")]]
            
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        return CUSTOMER_MENU

    # 2. Trigger the Bump Sequence
    elif data.startswith("bump_item_"):
        listing_id = data.replace("bump_item_", "")
        
        if execute_bump_logic(listing_id, context.bot):
            query.answer("🚀 Successfully bumped to the top!", show_alert=True)
        else:
            query.answer("❌ Error: Could not bump listing.", show_alert=True)
        
        return show_user_listings(update, context)

    # 3. Ask for Confirmation to Mark Sold
    elif data == "customer_trigger_sold":
        listing_id = context.user_data.get("targeted_id")
        text = f"⚠️ **CRITICAL WARNING:** Are you absolutely certain you want to mark `{listing_id}` as **SOLD**?\n\nThis permanently locks the active feed buttons and cannot be reversed."
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Mark as Sold!", callback_data="customer_confirm_sold_execution")],
            [InlineKeyboardButton("❌ Cancel", callback_data="return_listings_view")]
        ]
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        return CUSTOMER_MENU


def process_sold_state_modification(listing_id, bot, transaction_type="admin", escrow_log_url=None):
    """Iterates historically linked channel records to update structural states uniformly."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE listing_id = ?", (listing_id,))
    listing = cursor.fetchone()
    conn.close()
    
    if not listing:
        return False

    # 1. Structure Action Buttons conditionally
    if transaction_type == "admin" and escrow_log_url:
        sold_keyboard = [[InlineKeyboardButton("🤝 Sold via Escrow Service - View Proof", url=escrow_log_url)]]
    else:
        # Fallback for external user declarations (Unclickable status button)
        sold_keyboard = [[InlineKeyboardButton("🔄 Youtube Channel IS SOLD/Removed", callback_data="dead_button_trigger")]]
        
    reply_markup = InlineKeyboardMarkup(sold_keyboard)
    
    # 2. Update the Action Menu in the Main Channel (Does not break the photo album)
    if listing['channel_message_id']:
        try:
            bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=int(listing['channel_message_id']),
                text=f"🔄 <b>STATUS UPDATE:</b> Channel <code>{listing_id}</code> Has Been Successfully SOLD.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Failed cleaning main post instance {listing_id}: {e}")

    # 3. (Stock channel sync removed — browsing now happens inside the bot)

    # 4. Commit status conversions permanently into active DB layers
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE listings SET status_flag = 'sold' WHERE listing_id = ?", (listing_id,))
    conn.commit()
    conn.close()
    
    return True
        

# --- CUSTOMER EXECUTION SWITCH ENTRYPOINT ---
def customer_confirm_sold_callback(update, context):
    """Processes user-initiated self-service termination logic maps."""
    query = update.callback_query
    query.answer()
    
    listing_id = context.user_data.get("targeted_id")
    
    # Fire processing adjustments down external pipelines
    if process_sold_state_modification(listing_id, context.bot, transaction_type="external"):
        query.edit_message_text(f"✅ **Listing `{listing_id}` has been successfully marked as sold and locked.**", parse_mode='MARKDOWN')
    else:
        query.edit_message_text("❌ **An error occurred preventing the listing from updating.**")
        
    return CUSTOMER_MENU
    
    


        
        
        
        
# ===== EXISTING ADMIN FUNCTIONS =====
# == BUTTON GENERATION ==

def generate_buttons(listing_id, seller_contact=None, stock_message_id=None, **kwargs):
    """Generates the unified button layout for main channel posts.
    Browsing now happens inside the bot instead of a separate stock channel."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # --- URL VARIABLES ---
    ADMIN_URL = "https://t.me/smyards"          # Where "Contact Admin" goes
    FEEDBACK_URL = "https://t.me/Escrow_Log/9"  # Where "Feedback" goes
    BOT_USERNAME = "smyardbot"                  # The bot username for deep links
    # ---------------------------------------------------------------

    # Format the seller contact link safely
    if seller_contact and str(seller_contact).lower() != "none" and not str(seller_contact).startswith('http'):
        seller_url = f"https://t.me/{str(seller_contact).replace('@', '')}"
    else:
        # Fallback to Admin URL if no seller contact is provided
        seller_url = seller_contact if (seller_contact and str(seller_contact).lower() != "none") else ADMIN_URL

    keyboard = [
        # Row 1 (Small buttons side-by-side)
        [
            InlineKeyboardButton("📞 Contact Seller", url=seller_url),
            InlineKeyboardButton("👨‍💼 Contact Admin", url=ADMIN_URL)
        ],
        # Row 2 (Wide) - AUTOMATED DEEP LINK TO ESCROW
        [
            InlineKeyboardButton("🛍 Place Order▪️🤝 Start Escrow", url=f"https://t.me/{BOT_USERNAME}?start=buy_{listing_id}")
        ],
        # Row 3 (Wide - Browse listings inside the bot)
        [
            InlineKeyboardButton("🛒 Browse Listed Channels", url=f"https://t.me/{BOT_USERNAME}?start=browse")
        ],
        # Row 4 (Wide) - NEW AUTOMATED DEEP LINK
        [
            InlineKeyboardButton("💰 Sell your own Youtube Channel", url=f"https://t.me/{BOT_USERNAME}?start=sell")
        ],
        # Row 5 (Wide)
        [
            InlineKeyboardButton("🤝 Feedback & Successful Transactions", url=FEEDBACK_URL)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
    
    
def publish_to_main_channel(listing, screenshots, bot):
    """Publish listing to main channel as an album with details in the caption and buttons below"""
    try:
        from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
        
        # Ensure numbers are safely formatted with commas
        subs_raw = listing.get('subscribers', 0)
        views_raw = listing.get('views', 0)
        price_raw = listing.get('price', 0)
        
        subs_formatted = f"{int(float(subs_raw)):,}" if str(subs_raw).replace('.', '').isdigit() else subs_raw
        views_formatted = f"{int(float(views_raw)):,}" if str(views_raw).replace('.', '').isdigit() else views_raw
        price_formatted = f"{int(float(price_raw)):,}" if str(price_raw).replace('.', '').isdigit() else price_raw
        
        listing_id = listing.get('listing_id', 'N/A')

        post_text = f"""<b>🎯 NEW ACCOUNT FOR SALE</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📋 BASIC INFO</b>
- 📱 <b>Platform:</b> {listing.get('platform', 'N/A')}
- 👤 <b>Type:</b> {listing.get('account_type', 'N/A')}
- 🌍 <b>Region:</b> {listing.get('region', 'USA')}

<b>📊 STATISTICS</b>
- 👥 <b>Subscribers:</b> {subs_formatted}
- 👀 <b>Views:</b> {views_formatted}
- ✅ <b>Status:</b> {listing.get('status', 'No Strikes')}

<b>⚙️ FEATURES</b>
- 🗃️ <b>Niche:</b> {listing.get('niche', 'Mixed')}
- 🔧 <b>Features:</b> {listing.get('features', 'N/A')}
- 💲 <b>Monetization:</b> {listing.get('monetization', 'Enabled')}

<b>💰 PRICING</b>
- 💵 <b>Price:</b> ${price_formatted}

━━━━━━━━━━━━━━━━━━━━━━"""

        # Send Media Group (Album)
        if screenshots and len(screenshots) > 0:
            media_group = []
            for i, photo_file_id in enumerate(screenshots):
                if i == 0:
                    media_group.append(InputMediaPhoto(media=photo_file_id, caption=post_text, parse_mode='HTML'))
                else:
                    media_group.append(InputMediaPhoto(media=photo_file_id))
            
            # The bot waits for the images to finish uploading
            bot.send_media_group(chat_id=CHANNEL_ID, media=media_group, timeout=60)
        else:
            bot.send_message(chat_id=CHANNEL_ID, text=post_text, parse_mode='HTML', timeout=20)

        # Generate the full unified button set (Contact Seller, Contact Admin,
        # Place Order, Browse Listings, Sell, Feedback)
        reply_markup = generate_buttons(
            listing_id=listing_id,
            seller_contact=listing.get('seller_contact')
        )

        # Companion button message
        button_text = (
            f"<b>🆔 Product ID:</b> <code>{listing_id}</code>\n\n"
            f"ℹ️ <i>Click the options below to interact directly with our secure automated escrow service.</i>"
        )
        
        button_message = bot.send_message(
            chat_id=CHANNEL_ID,
            text=button_text,
            parse_mode='HTML',
            reply_markup=reply_markup,
            timeout=20
        )

        return button_message.message_id
        
    except Exception as e:
        import traceback
        print(f"\n❌ MAIN CHANNEL CRASHED: {e}")
        print(traceback.format_exc())
        return None


def admin_button_callback(update, context):
    """Handle admin button callbacks - UPDATED WITH NEW ROUTING"""
    query = update.callback_query
    query.answer()
    data = query.data
    
    # NEW ROUTING SECTION - Check these first
    if data == "admin_settings":
        return admin_settings(update, context)
    elif data == "admin_back_main":
        return admin_start(update, context)
    
    # EXISTING ROUTING - Keep all the original logic
    if data == "new_listing":
        keyboard = []
        for platform in PLATFORMS:
            keyboard.append([InlineKeyboardButton(platform, callback_data=f"platform_{platform}")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
        
        query.edit_message_text(
            text="📝 CREATE NEW LISTING\n━━━━━━━━━━━━━━━━━━━━━━\nSelect Platform:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CREATE_PLATFORM
    
    elif data.startswith("platform_"):
        platform = data.replace("platform_", "")
        context.user_data["listing"] = {"platform": platform}
        
        if platform == "YouTube":
            account_types = YOUTUBE_TYPES
        else:
            account_types = DEFAULT_TYPES
        
        keyboard = []
        for acc_type in account_types:
            keyboard.append([InlineKeyboardButton(acc_type, callback_data=f"type_{acc_type}")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_platform")])
        
        query.edit_message_text(
            text=f"Platform: {platform}\nSelect Account Type:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CREATE_TYPE
    
    elif data.startswith("type_"):
        acc_type = data.replace("type_", "")
        context.user_data["listing"]["account_type"] = acc_type
        
        query.edit_message_text(
            text=f"📝 Enter Listing Details:\n\n"
            f"Platform: {context.user_data['listing']['platform']}\n"
            f"Type: {acc_type}\n\n"
            f"Send details (one per line):\n"
            f"Subscribers: [number]\n"
            f"Views: [number]\n"
            f"Niche: [text]\n"
            f"Features: [text]\n"
            f"Monetization: [Enabled/Disabled]\n"
            f"Region: [text]\n"
            f"Status: [text]"
        )
        return CREATE_DETAILS
    
    elif data == "view_listings":
        return admin_view_listings(update, context)
        
    elif data.startswith("admin_hub_"):
        return admin_item_hub_callback(update, context)
        
    elif data.startswith("admin_run_"):
        return admin_hub_execution_callback(update, context)
    
    elif data == "back_main":
        return admin_start(update, context)
    
    elif data == "back_platform":
        keyboard = []
        for platform in PLATFORMS:
            keyboard.append([InlineKeyboardButton(platform, callback_data=f"platform_{platform}")])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_main")])
        
        query.edit_message_text(
            text="Select Platform:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CREATE_PLATFORM
    
    elif data == "add_screenshots":
        context.user_data["screenshots"] = []
        query.edit_message_text(
            text=f"📸 Send up to {MAX_SCREENSHOTS} screenshots\n\n"
            f"• Send photos one by one\n"
            f"• Maximum: {MAX_SCREENSHOTS} screenshots\n"
            f"• Type 'done' when finished\n"
            f"• Type 'cancel' to abort\n\n"
            f"Ready for screenshot 1:"
        )
        return SCREENSHOT_UPLOAD
    
    elif data == "skip_screenshots":
        context.user_data["screenshots"] = []
        return admin_show_final_preview_from_callback(query, context)
    
    elif data == "back_to_price":
        query.edit_message_text("💰 Enter Price (USD):\n\nExample: 150\n\nType 'cancel' to abort.")
        return CREATE_PRICE
    
    elif data == "back_to_seller_contact":
        query.edit_message_text(
            "📞 Enter Seller Contact Link:\n\n"
            "Examples:\n• https://t.me/username\n• https://wa.me/1234567890\n\n"
            "Type 'skip' to leave blank, 'cancel' to abort."
        )
        return CREATE_SELLER_CONTACT
    
    elif data in ["save_draft", "publish_now", "edit_again", "cancel_create"]:
        return admin_handle_confirmation(update, context)

    elif data.startswith("payment_"):
        return admin_handle_payment_method(update, context)
    
    elif data == "cancel_sale":
        query.edit_message_text("❌ Sale marking cancelled.")
        return admin_start(update, context)
		
    elif data == "admin_orders_panel":
        return admin_orders_panel(update, context)
    
    elif data.startswith("admin_order_"):
        return admin_view_order_detail(update, context)
    
    elif data.startswith("confirm_order_payment_"):
        query.answer("Payment confirmation feature coming in Stage 2", show_alert=True)
        return MAIN_MENU
    
    elif data.startswith("add_group_link_"):
        return admin_add_group_link(update, context)
    
    elif data.startswith("mark_completed_"):
        return admin_mark_order_completed(update, context)
    
    elif data.startswith("admin_listings_page_"):
        return admin_view_listings(update, context)
    
    # If no match found, stay in main menu
    return MAIN_MENU

# Routes for new admin listing management
def admin_button_callback_updated(update, context):
    """UPDATED: Handle new admin listing management callbacks."""
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data.startswith("admin_manage_listing_"):
        return admin_manage_listing(update, context)
    elif data.startswith("admin_bump_listing_"):
        listing_id = int(data.replace("admin_bump_listing_", ""))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT listing_id FROM listings WHERE id = ?", (listing_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            execute_bump_logic(result[0], context.bot)
            query.answer("🚀 Listing bumped to top!", show_alert=True)
        else:
            query.answer("❌ Listing not found", show_alert=True)
        return admin_view_listings(update, context)
    elif data.startswith("admin_mark_sold_listing_"):
        listing_id = int(data.replace("admin_mark_sold_listing_", ""))
        context.user_data['admin_marking_sold_id'] = listing_id
        
        query.edit_message_text(
            "📝 <b>Mark Listing as SOLD</b>\n\n"
            "Please enter the seller name (for privacy, only first part will be shown):\n\n"
            "Type 'cancel' to abort."
        )
        return ADMIN_MARK_SOLD
    elif data.startswith("admin_delete_listing_"):
        return admin_delete_listing(update, context)
    elif data == "confirm_delete_listing":
        return confirm_delete_listing(update, context)
    elif data == "admin_view_listings_reset":
        return admin_view_listings_reset(update, context)
    
    # Call original handler for other callbacks
    return admin_button_callback(update, context)    
    
def admin_handle_confirmation(update, context):
    """Handle confirmation callbacks - SIMPLIFIED WORKING VERSION"""
    query = update.callback_query
    query.answer()
    data = query.data
    
    logger.info(f"✅ Confirmation callback received: {data}")
    
    if data == "save_draft":
        # Save as draft
        listing = context.user_data["listing"]
        screenshots = context.user_data.get("screenshots", [])
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO listings (
                listing_id, platform, account_type, price, seller_contact, 
                status_flag, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing.get('listing_id'),
            listing.get('platform'),
            listing.get('account_type'),
            listing.get('price'),
            listing.get('seller_contact'),
            'draft',
            update.effective_user.id
        ))
        conn.commit()
        conn.close()
        
        query.edit_message_text(f"✅ Saved as draft: {listing.get('listing_id')}")
        return admin_start(update, context)
    
    elif data == "publish_now":
        logger.info("🟢 PUBLISH NOW clicked - Starting clean unified publish process")
        
        # 1. Gather listing data from context
        listing = context.user_data.get("listing")
        screenshots = context.user_data.get("screenshots", [])
        
        if not listing:
            query.edit_message_text("❌ Error: Listing data not found in session.")
            return
            
        try:
            # 2. Post ONE unified album post to the MAIN CHANNEL
            logger.info("➡️ Step 1: Posting album to main channel...")
            
            main_message_id = publish_to_main_channel(
                listing=listing, 
                screenshots=screenshots, 
                bot=context.bot
            )
            
            if not main_message_id:
                raise Exception("Main channel posting failed.")
            
            # 3. Post the compact entry to the STOCK CHANNEL
            logger.info("➡️ Step 2: Posting to stock channel...")
            stock_message_id = admin_create_stock_post(
                listing=listing, 
                bot=context.bot, 
                main_message_id=main_message_id
            )
            
            # 4. Save the exact message references into the Database
            logger.info("➡️ Step 3: Saving to database...")
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO listings (
                    listing_id, platform, account_type, subscribers, views,
                    niche, features, monetization, region, status, price,
                    screenshots, seller_contact, status_flag, channel_message_id, 
                    stock_message_id, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing.get('listing_id'), listing.get('platform'), listing.get('account_type'),
                listing.get('subscribers', 0), listing.get('views', 0),
                listing.get('niche', 'Mixed'), listing.get('features', 'N/A'),
                listing.get('monetization', 'Enabled'), listing.get('region', 'USA'),
                listing.get('status', 'No Strikes'), listing.get('price'),
                json.dumps(screenshots), listing.get('seller_contact'), 'published',
                str(main_message_id), str(stock_message_id) if stock_message_id else None,
                update.effective_user.id
            ))
            conn.commit()
            conn.close()
            
            # Send confirmation UI to admin panel
            success_msg = f"✅ **PUBLISHED SUCCESSFULLY!**\n\n🆔 ID: `{listing.get('listing_id')}`\n📱 Platform: {listing.get('platform')}\n🛍 Now visible in the in-bot browse menu!"
            query.edit_message_text(success_msg, parse_mode='MARKDOWN')
            logger.info("✅ Finished execution sequence smoothly.")
            
        except Exception as e:
            logger.error(f"❌ Error during execution flow: {e}")
            import traceback
            logger.error(traceback.format_exc())
            query.edit_message_text(f"❌ Error during publishing: {str(e)[:100]}")
        
        # Clean session memory state
        context.user_data.clear()
        return admin_start(update, context)
    
    elif data == "edit_again":
        query.edit_message_text("✏️ Send corrected details:")
        return CREATE_DETAILS
    
    elif data == "cancel_create":
        query.edit_message_text("❌ Creation cancelled.")
        context.user_data.clear()
        return admin_start(update, context)
    
    return MAIN_MENU

def clean_number_input(value):
    """Clean number input from user"""
    if not value:
        return 0
    
    if isinstance(value, (int, float)):
        return int(value)
    
    # Remove any non-digit characters except minus sign
    value_str = str(value)
    cleaned = ''.join(char for char in value_str if char.isdigit())
    
    if cleaned:
        return int(cleaned)
    return 0    

def admin_handle_details(update, context):
    """Handle listing details input"""
    text = update.message.text
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Creation cancelled.")
        return admin_start(update, context)
    
    details = {}
    for line in text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if 'subscriber' in key:
                details['subscribers'] = clean_number_input(value)  # Use cleaner
            elif 'view' in key:
                details['views'] = clean_number_input(value)  # Use cleaner
            elif 'niche' in key:
                details['niche'] = value
            elif 'feature' in key:
                details['features'] = value
            elif 'monetiz' in key:
                details['monetization'] = value
            elif 'region' in key:
                details['region'] = value
            elif 'status' in key:
                details['status'] = value
    
    context.user_data["listing"].update(details)
    
    update.message.reply_text("💰 Enter Price (USD):\n\nExample: 150\n\nType 'cancel' to abort.")
    return CREATE_PRICE

def admin_handle_price(update, context):
    """Handle price input and generate sequential listing ID"""
    text = update.message.text
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Creation cancelled.")
        return admin_start(update, context)
    
    try:
        price = float(text)
        context.user_data["listing"]["price"] = price
        
        platform = context.user_data["listing"]["platform"]
        
        # Custom platform codes
        platform_codes = {
            'YouTube': 'YT',
            'TikTok': 'TT', 
            'Instagram': 'IG',
            'Facebook': 'FB'
        }
        
        platform_code = platform_codes.get(platform, platform[:2].upper())
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Find the highest existing number for this platform prefix and increment
        cursor.execute("SELECT listing_id FROM listings WHERE listing_id LIKE ?", (f"{platform_code}-%",))
        existing = cursor.fetchall()
        max_num = 0
        for (eid,) in existing:
            parts = eid.split('-')
            if len(parts) == 2 and parts[1].isdigit():
                max_num = max(max_num, int(parts[1]))
        listing_id = f"{platform_code}-{max_num + 1:03d}"
        logger.info(f"Generated listing ID: {listing_id}")
        
        conn.close()
        
        context.user_data["listing"]["listing_id"] = listing_id
        
        update.message.reply_text(
            f"✅ Generated Product ID: **{listing_id}**\n\n"
            "📞 Enter Seller Contact Link:\n\n"
            "This link will be shown in the 'Contact Seller' button.\n"
            "Examples:\n"
            "• https://t.me/username (Telegram)\n"
            "• https://wa.me/1234567890 (WhatsApp)\n"
            "• https://example.com/contact\n\n"
            "Type 'skip' to leave blank, 'cancel' to abort.",
            parse_mode='MARKDOWN'
        )
        return CREATE_SELLER_CONTACT
        
    except ValueError:
        update.message.reply_text("❌ Invalid price. Enter a number (e.g., 150):")
        return CREATE_PRICE
    except Exception as e:
        logger.error(f"Error in admin_handle_price: {e}")
        update.message.reply_text("❌ Error generating listing ID. Please try again.")
        return CREATE_PRICE

def admin_handle_seller_contact(update, context):
    """Handle seller contact input"""
    text = update.message.text.strip()
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Creation cancelled.")
        return admin_start(update, context)
    
    if text.lower() == 'skip':
        context.user_data["listing"]["seller_contact"] = None
        update.message.reply_text("ℹ️ No seller contact provided.")
    else:
        # Store the contact link
        context.user_data["listing"]["seller_contact"] = text
    
    # Now ask about screenshots
    keyboard = [
        [InlineKeyboardButton("✅ Yes, add screenshots", callback_data="add_screenshots")],
        [InlineKeyboardButton("➡️ No, skip for now", callback_data="skip_screenshots")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_seller_contact")]
    ]
    
    update.message.reply_text(
        "📸 Add Screenshots?\n\n"
        f"You can add up to {MAX_SCREENSHOTS} screenshots of the account.\n"
        "Customers will see them when they click the 'Screenshots' button.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SCREENSHOT_ASK
    
def admin_handle_screenshot_upload(update, context):
    """Handle screenshot photo uploads"""
    if 'screenshots' not in context.user_data:
        context.user_data['screenshots'] = []
    
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['screenshots'].append(photo.file_id)
        
        count = len(context.user_data['screenshots'])
        
        if count >= MAX_SCREENSHOTS:
            update.message.reply_text(f"✅ Maximum {MAX_SCREENSHOTS} screenshots reached!")
            return admin_show_final_preview(update, context)
        else:
            update.message.reply_text(
                f"📸 Screenshot {count} received!\n"
                f"Send another photo or type 'done' to finish."
            )
    elif update.message.text:
        text = update.message.text.lower()
        if text == 'done':
            return admin_show_final_preview(update, context)
        elif text == 'cancel':
            update.message.reply_text("❌ Creation cancelled.")
            return admin_start(update, context)
        else:
            update.message.reply_text("Please send photos or type 'done' to finish.")
    
    return SCREENSHOT_UPLOAD


def admin_handle_txid(update, context):
    """Handle TXid input"""
    txid = update.message.text.strip()
    
    if txid.lower() == 'cancel':
        update.message.reply_text("❌ Cancelled.")
        return admin_start(update, context)
    
    context.user_data["sold_listing"]["txid"] = txid
    
    # Show payment method options
    keyboard = [
        [InlineKeyboardButton("💳 Crypto (ETH)", callback_data="payment_eth")],
        [InlineKeyboardButton("₿ Crypto (BTC)", callback_data="payment_btc")],
        [InlineKeyboardButton("💵 Crypto (USDT)", callback_data="payment_usdt")],
        [InlineKeyboardButton("💸 PayPal", callback_data="payment_paypal")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_sale")]
    ]
    
    update.message.reply_text(
        "💳 Select Payment Method:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ENTER_PAYMENT_METHOD

def admin_handle_payment_method(update, context):
    """Handle payment method selection - FIXED: Now asks for order number"""
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data == "cancel_sale":
        query.edit_message_text("❌ Sale marking cancelled.")
        return admin_start(update, context)
    
    # Map callback data to display names
    payment_methods = {
        "payment_eth": "Crypto (ETH)",
        "payment_btc": "Crypto (BTC)",
        "payment_usdt": "Crypto (USDT)",
        "payment_paypal": "PayPal",
        "payment_bank": "Bank Transfer"
    }
    
    payment_method = payment_methods.get(data, "Crypto (ETH)")
    context.user_data["sold_listing"]["payment_method"] = payment_method
    
    # Ask for order number instead of completing sale
    query.edit_message_text(
        f"💳 Payment Method: {payment_method}\n\n"
        f"📝 Enter Order Number:\n\n"
        f"Example: YT#1059, IG#1258, FB#1236, TT#1025\n\n"
        f"This order number will be shown in the escrow log post.\n\n"
        f"Type 'cancel' to abort."
    )
    
    # Set order_number to None initially
    context.user_data["sold_listing"]["order_number"] = None
    
    # Now we need to handle the order number input
    return ENTER_ORDER_NUMBER

def admin_handle_order_number(update, context):
    """Handle order number input - NEW FUNCTION"""
    order_number = update.message.text.strip().upper()
    
    if order_number.lower() == 'cancel':
        update.message.reply_text("❌ Cancelled.")
        return admin_start(update, context)
    
    # Validate order number format
    if not any(prefix in order_number for prefix in ['YT#', 'IG#', 'FB#', 'TT#']):
        update.message.reply_text(
            "❌ Invalid order number format.\n"
            "Must be: YT#xxxx, IG#xxxx, FB#xxxx, or TT#xxxx\n\n"
            "Please enter a valid order number or type 'cancel':"
        )
        return ENTER_ORDER_NUMBER
    
    context.user_data["sold_listing"]["order_number"] = order_number
    
    # Complete the sale
    return admin_complete_sale(update, context)

def admin_complete_sale(update, context):
    """Complete the sale marking process"""
    query = None
    if update.callback_query:
        query = update.callback_query
        query.answer()
    
    sold_data = context.user_data.get("sold_listing", {})
    
    if not sold_data:
        if query:
            query.edit_message_text("❌ Error: Sale data missing.")
        else:
            update.message.reply_text("❌ Error: Sale data missing.")
        return admin_start(update, context)
    
    try:
        escrow_message_id = admin_create_escrow_log_post(sold_data, context.bot)
        
        if escrow_message_id:
            main_updated = admin_update_main_post_as_sold(sold_data, context.bot, escrow_message_id)
            stock_updated = admin_update_stock_post_as_sold(sold_data, context.bot, escrow_message_id)
            
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE listings SET status_flag = 'sold' WHERE listing_id = ?",
                (sold_data["listing_id"],)
            )
            conn.commit()
            conn.close()
            
            # Build success message
            success_msg = f"✅ Successfully marked as SOLD!\n\n"
            success_msg += f"🆔 Product: {sold_data['listing_id']}\n"
            success_msg += f"🛍 Order #: {sold_data.get('order_number', 'N/A')}\n"
            success_msg += f"💰 Price: ${sold_data['price']}\n"
            success_msg += f"💳 Payment: {sold_data['payment_method']}\n\n"
            success_msg += f"📝 Escrow log: ✅ Posted\n"
            
            if query:
                query.edit_message_text(success_msg)
            else:
                update.message.reply_text(success_msg)
    except Exception as e:
        if query:
            query.edit_message_text(f"❌ Error completing sale: {e}")
        else:
            update.message.reply_text(f"❌ Error completing sale: {e}")
            
    return admin_start(update, context)

# admin_mark_sold_with_transaction - asks for seller/buyer names
def admin_handle_sold_seller_name(update, context):
    """Handle seller name input for transaction logging."""
    text = update.message.text.strip()
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Cancelled.")
        return MAIN_MENU
    
    context.user_data['tx_seller_name'] = text
    
    update.message.reply_text(
        "👤 <b>Enter Buyer Name:</b>\n\n"
        "Example: John, Alice, etc.\n\n"
        "Type 'cancel' to abort."
    )
    return ENTER_ORDER_NUMBER  # Reuse state for buyer name

# admin_handle_sold_buyer_name
def admin_handle_sold_buyer_name(update, context):
    """Handle buyer name input for transaction logging."""
    text = update.message.text.strip()
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Cancelled.")
        return MAIN_MENU
    
    context.user_data['tx_buyer_name'] = text
    
    update.message.reply_text(
        "📝 <b>Enter Transaction ID (TXid):</b>\n\n"
        "This should be a blockchain transaction link or ID.\n"
        "Example: https://etherscan.io/tx/0x123abc...\n\n"
        "Type 'skip' if no TXid, or 'cancel' to abort."
    )
    return ENTER_TXID    

# Updated ENTER_TXID handler to save transaction log
def admin_handle_txid_with_transaction_log(update, context):
    """Handle TXid and save to transaction log."""
    txid = update.message.text.strip()
    
    if txid.lower() == 'cancel':
        update.message.reply_text("❌ Cancelled.")
        context.user_data.pop('tx_seller_name', None)
        context.user_data.pop('tx_buyer_name', None)
        return MAIN_MENU
    
    if txid.lower() == 'skip':
        txid = None
    
    listing_id = context.user_data.get('admin_marking_sold_id')
    seller_name = context.user_data.get('tx_seller_name', 'Unknown')
    buyer_name = context.user_data.get('tx_buyer_name', 'Unknown')
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id, platform, price FROM listings WHERE id = ?", (listing_id,))
    listing = cursor.fetchone()
    
    if listing:
        l_id, platform, price = listing
        order_num = f"{platform[:2].upper()}#TXN{listing_id}"
        
        # Create transaction log entry
        cursor.execute("""
            INSERT INTO transactions_log 
            (order_number, product_id, platform, seller_name, buyer_name, price, txid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order_num, l_id, platform, seller_name, buyer_name, price, txid))
        
        conn.commit()
        update.message.reply_text(
            f"✅ <b>Transaction Logged!</b>\n\n"
            f"Order: <code>{order_num}</code>\n"
            f"Product: <code>{l_id}</code>\n"
            f"Seller: {seller_name}\n"
            f"Buyer: {buyer_name}\n"
            f"Amount: ${price:,.2f}\n\n"
            f"This transaction is now visible in the platform transaction log.",
            parse_mode=ParseMode.HTML
        )
    else:
        update.message.reply_text("❌ Listing not found.")
    
    conn.close()
    
    # Clean up
    context.user_data.pop('admin_marking_sold_id', None)
    context.user_data.pop('tx_seller_name', None)
    context.user_data.pop('tx_buyer_name', None)
    
    return MAIN_MENU

# Update admin_button_callback to route new states
def route_admin_mark_sold_flow(update, context):
    """Route admin mark sold to transaction logging flow."""
    if update.message and update.message.text:
        text = update.message.text.strip()
        
        if 'tx_seller_name' not in context.user_data:
            return admin_handle_sold_seller_name(update, context)
        elif 'tx_buyer_name' not in context.user_data:
            return admin_handle_sold_buyer_name(update, context)
        else:
            return admin_handle_txid_with_transaction_log(update, context)
    
    return MAIN_MENU


def helper_get_tg_url(channel_id, message_id):
    """Helper to cleanly format Telegram links for both public and private channels"""
    ch_str = str(channel_id).strip()
    if ch_str.startswith('-100'):
        return f"https://t.me/c/{ch_str[4:]}/{message_id}"
    elif ch_str.startswith('@'):
        return f"https://t.me/{ch_str[1:]}/{message_id}"
    return f"https://t.me/{ch_str}/{message_id}"

def admin_show_final_preview(update, context):
    """Show final preview before saving"""
    listing = context.user_data["listing"]
    screenshots = context.user_data.get("screenshots", [])
    
    preview = admin_format_preview(listing, len(screenshots))
    
    keyboard = [
        [InlineKeyboardButton("✅ Save as Draft", callback_data="save_draft")],
        [InlineKeyboardButton("▶️ Publish Now", callback_data="publish_now")],
        [InlineKeyboardButton("✏️ Edit Again", callback_data="edit_again")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_create")]
    ]
    
    # Safe fallback if triggered from a CallbackQuery instead of a text message
    send_msg = update.message.reply_text if update.message else update.callback_query.message.reply_text
    
    send_msg(
        preview,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    return CREATE_CONFIRM

def admin_format_preview(listing, screenshot_count=0):
    """Format listing for preview with Emoji-Based Sections"""
    screenshot_info = f"📸 Screenshots: {screenshot_count} uploaded" if screenshot_count > 0 else "📸 Screenshots: None"
    
    price = str(listing.get('price', 'N/A'))
    if price.replace('.', '', 1).isdigit():
        price = str(int(float(price)))
    
    return f"""
<b>🎯 NEW ACCOUNT FOR SALE</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📋 BASIC INFO</b>
• 📱 <b>Platform:</b> {listing.get('platform', 'N/A').upper()}
• 👤 <b>Type:</b> {listing.get('account_type', 'N/A')}
• 🌍 <b>Region:</b> {listing.get('region', 'USA')}

<b>📊 STATISTICS</b>
• 👥 <b>Subscribers:</b> {listing.get('subscribers', 'N/A')}
• 👀 <b>Views:</b> {listing.get('views', 'N/A')}
• ✅ <b>Status:</b> {listing.get('status', 'No Strikes')}

<b>⚙️ FEATURES</b>
• 🗃️ <b>Niche:</b> {listing.get('niche', 'Mixed')}
• 🔧 <b>Features:</b> {listing.get('features', 'N/A')}
• 💲 <b>Monetization:</b> {listing.get('monetization', 'Enabled')}

<b>💰 PRICING</b>
• 💵 <b>Price:</b> ${price}
• 🆔 <b>Product ID:</b> <code>{listing.get('listing_id', 'N/A')}</code>

━━━━━━━━━━━━━━━━━━━━━━
{screenshot_info}
━━━━━━━━━━━━━━━━━━━━━━
"""

def admin_debug_command(update, context):
    """Debug command to show current settings"""
    update.message.reply_text(
        f"🔧 DEBUG INFO:\n"
        f"Main Channel: {CHANNEL_ID}\n"
        f"Screenshot Channel ID: {SCREENSHOT_CHANNEL_ID}\n"
        f"Discussion Group ID: {DISCUSSION_GROUP_ID}\n"
        f"Owner ID: {OWNER_ID}"
    )
   
def admin_update_main_post_as_sold(sold_data, bot, escrow_message_id):
    """Update main channel post to show SOLD status"""
    try:
        channel_message_id = sold_data.get('channel_message_id')
        if not channel_message_id or str(channel_message_id).lower() == 'none':
            return True
            
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT platform, account_type, subscribers, views, price
            FROM listings WHERE listing_id = ?
        """, (sold_data.get('listing_id'),))
        listing_details = cursor.fetchone()
        conn.close()
        
        if not listing_details:
            return False
        
        platform, account_type, subscribers, views, price = listing_details
        escrow_url = helper_get_tg_url(ESCROW_LOG_CHANNEL_ID, escrow_message_id)
        
        price_str = str(price)
        if price_str.replace('.', '', 1).isdigit():
            price_str = str(int(float(price_str)))
        
        subs_formatted = f"{int(subscribers):,}" if subscribers and str(subscribers).isdigit() else "N/A"
        views_formatted = f"{int(views):,}" if views and str(views).isdigit() else "N/A"
        
        platform_colors = {'youtube': '🔴', 'instagram': '🟣', 'tiktok': '⚫', 'facebook': '🔵'}
        platform_emoji = platform_colors.get(platform.lower(), '🟢')
        
        sold_text = f"""
<b>🆔 Product ID:</b> <code>{sold_data.get('listing_id')}</code>
━━━━━━━━━━━━━━━━━━━━━━
<b>✅ SOLD ANNOUNCEMENT</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>{platform} Channel - SOLD</b>

{platform_emoji} <b>{platform} Channel</b>▪️<b>{account_type}</b>▪️<b>{subs_formatted} Subs</b> <b>{views_formatted} Views</b>

<b>Order #:</b> <code>{sold_data.get('order_number', 'N/A')}</code>
<b>Sold For:</b> ${price_str}
<b>Transaction Proof:</b> <a href="{escrow_url}">View Escrow Log</a>

━━━━━━━━━━━━━━━━━━━━━━
This listing has been sold via escrow.
"""
        keyboard = [[InlineKeyboardButton("✅ SOLD - View Transaction Proof", url=escrow_url)]]
        
        chat_id = CHANNEL_ID if isinstance(CHANNEL_ID, str) and CHANNEL_ID.startswith('@') else int(CHANNEL_ID)
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=int(channel_message_id),
            text=sold_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=int(channel_message_id),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return True
        
    except Exception as e:
        logger.error(f"Error updating main post as sold: {e}")
        return False

def admin_view_listings(update, context):
    """Admin paginated list of all listings with platform filtering (like customer browse)."""
    query = update.callback_query
    
    # Get page and platform from callback data
    page = 0
    platform_filter = None
    
    if query and query.data.startswith("admin_listings_page_"):
        parts = query.data.replace("admin_listings_page_", "").split("_")
        page = int(parts[0])
        if len(parts) > 1:
            platform_filter = "_".join(parts[1:])
        context.user_data['listings_page'] = page
        context.user_data['admin_platform_filter'] = platform_filter
    elif query and query.data.startswith("admin_platform_"):
        platform_filter = query.data.replace("admin_platform_", "")
        page = 0
        context.user_data['listings_page'] = page
        context.user_data['admin_platform_filter'] = platform_filter
    else:
        platform_filter = context.user_data.get('admin_platform_filter')
        page = context.user_data.get('listings_page', 0)
    
    PAGE_SIZE = 10
    offset = page * PAGE_SIZE
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Build query with platform filter
    if platform_filter:
        cursor.execute("SELECT COUNT(*) FROM listings WHERE platform = ?", (platform_filter,))
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id, listing_id, platform, account_type, subscribers, price, 
                   status_flag, created_at
            FROM listings
            WHERE platform = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (platform_filter, PAGE_SIZE, offset))
    else:
        cursor.execute("SELECT COUNT(*) FROM listings")
        total = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT id, listing_id, platform, account_type, subscribers, price, 
                   status_flag, created_at
            FROM listings
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (PAGE_SIZE, offset))
    
    listings = cursor.fetchall()
    
    # Get platform counts
    cursor.execute("""
        SELECT platform, COUNT(*) FROM listings GROUP BY platform
    """)
    platform_counts = dict(cursor.fetchall())
    conn.close()
    
    if not listings and not platform_filter:
        text = "📋 <b>ADMIN ACCOUNTS MARKET</b>\n\n📭 No listings found."
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")]]
        if query:
            query.answer()
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return MAIN_MENU
    
    # If no platform filter, show platform selection
    if not platform_filter:
        text = "📋 <b>ADMIN ACCOUNTS MARKET</b>\n\nSelect a platform or view all:"
        keyboard = []
        for plat in PLATFORMS:
            count = platform_counts.get(plat, 0)
            emoji = {"YouTube": "🔴", "Instagram": "🟣", "TikTok": "⚫", "Facebook": "🔵"}.get(plat, "🟢")
            keyboard.append([InlineKeyboardButton(f"{emoji} {plat} ({count})", callback_data=f"admin_platform_{plat}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")])
        
        if query:
            query.answer()
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return MAIN_MENU
    
    # Show listings for platform
    text = f"📋 <b>ACCOUNTS MARKET - {platform_filter}</b> (Page {page + 1})\n\n"
    keyboard = []
    
    for listing in listings:
        lid, listing_id, platform, acc_type, subs, price, status, created = listing
        status_badge = "✅" if status == "published" else "❌"
        subs_fmt = format_number(subs)
        price_fmt = f"${price:,.0f}" if price else "$0"
        
        text += (
            f"{status_badge} <b>{listing_id}</b> | {platform}\n"
            f"👤 {acc_type} | 👥 {subs_fmt} subs | {price_fmt}\n\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(f"Manage {listing_id}", callback_data=f"admin_manage_listing_{lid}")
        ])
    
    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"admin_listings_page_{page-1}_{platform_filter}"))
    if offset + PAGE_SIZE < total:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_listings_page_{page+1}_{platform_filter}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Platforms", callback_data="admin_view_listings_reset")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")])
    
    if query:
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    return MAIN_MENU

def admin_item_hub_callback(update, context):
    query = update.callback_query
    query.answer()
    listing_id = query.data.replace("admin_hub_", "")
    context.user_data["product_id"] = listing_id
    text = f"⚙️ **Managing:** `{listing_id}`\nChoose an action:"
    keyboard = [
        [InlineKeyboardButton("⚡ Bump to Top", callback_data=f"admin_run_bump_{listing_id}")],
        [InlineKeyboardButton("💰 Mark as Sold", callback_data=f"admin_run_sold_{listing_id}")],
        [InlineKeyboardButton("⬅️ Back to List", callback_data="view_listings")]
    ]
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return MAIN_MENU

def admin_hub_execution_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    
    if data.startswith("admin_run_bump_"):
        listing_id = data.replace("admin_run_bump_", "")
        execute_bump_logic(listing_id, context.bot)
        query.message.reply_text(f"🚀 `{listing_id}` bumped successfully!")
        return admin_view_listings(update, context)
        
    elif data.startswith("admin_run_sold_"):
        listing_id = data.replace("admin_run_sold_", "")
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT listing_id, platform, price, channel_message_id, stock_message_id, 
                      subscribers, views, account_type, status_flag 
               FROM listings WHERE listing_id = ?""",
            (listing_id,)
        )
        listing = cursor.fetchone()
        conn.close()
        
        if not listing:
            query.message.reply_text("❌ Error: Listing not found in database.")
            return MAIN_MENU
            
        (l_id, platform, price, channel_message_id, stock_message_id,
         subscribers, views, account_type, status_flag) = listing
        
        context.user_data["sold_listing"] = {
            "listing_id": l_id,
            "platform": platform,
            "price": price,
            "channel_message_id": channel_message_id,
            "stock_message_id": stock_message_id,
            "subscribers": subscribers,
            "views": views,
            "account_type": account_type,
            "current_status": status_flag
        }
        
        query.message.reply_text(
            f"✅ **Selected for Sale:** {l_id}\n"
            f"📱 **Platform:** {platform}\n"
            f"💰 **Price:** ${price}\n\n"
            f"📄 **Please enter the Transaction ID (TXid) or Escrow link:**\n\n"
            f"Type 'cancel' to abort.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ENTER_TXID
        
        
        
        
        
        
        

# ===== CUSTOMER HANDLERS =====
def customer_start(update, context):
    """REORGANIZED Customer Dashboard"""
    query = update.callback_query
    user = update.effective_user
    
    dashboard_text = (
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        f"What would you like to do?"
    )
    
    keyboard = [
        [InlineKeyboardButton("📦 Accounts Market", callback_data="browse_menu")],
        [InlineKeyboardButton("🛍 Buy an Account (via Escrow)", callback_data="buyer_start")],
        [InlineKeyboardButton("💰 Sell Your Account", callback_data="seller_start")],
        [InlineKeyboardButton("📋 My Listings", callback_data="view_my_listings")],
        [InlineKeyboardButton("🛒 My Orders", callback_data="customer_my_orders")],
        [InlineKeyboardButton("👤 Profile & Feedback", callback_data="user_profile_feedback")],
        [InlineKeyboardButton("📊 Transactions/Feedback Log", callback_data="transactions_log")],
        [InlineKeyboardButton("💬 Join Community", url="https://t.me/smyardchat")],
        [InlineKeyboardButton("🎧 Support & FAQ", callback_data="customer_support")],
    ]
    
    if query:
        query.answer()
        query.edit_message_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    else:
        update.message.reply_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    return CUSTOMER_MENU

    
# ===== IN-BOT BROWSE & SEARCH SYSTEM =====

def browse_menu(update, context):
    """Main browse entry — shows platform categories with live counts."""
    query = update.callback_query
    context.user_data.pop('browse_filters', None)  # reset filters when entering fresh

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT platform, COUNT(*) FROM listings
        WHERE status_flag = 'published'
        GROUP BY platform
    """)
    counts = dict(cursor.fetchall())
    conn.close()

    text = (
        "🛍 <b>Browse Listed Channels</b>\n\n"
        "Pick a platform to explore available accounts, or use search to "
        "filter by price, subscribers, and more.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = []
    for plat in PLATFORMS:
        count = counts.get(plat, 0)
        emoji = {"YouTube": "🔴", "Instagram": "🟣", "TikTok": "⚫", "Facebook": "🔵"}.get(plat, "🟢")
        keyboard.append([InlineKeyboardButton(f"{emoji} {plat} ({count})", callback_data=f"browse_platform_{plat}")])

    keyboard.append([InlineKeyboardButton("🔍 Search / Filter", callback_data="browse_filter_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")])

    if query:
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    return BROWSE_MENU

def _build_listing_query(filters):
    """Builds a WHERE clause + params list from active filters dict."""
    where = ["status_flag = 'published'"]
    params = []

    if filters.get('platform'):
        where.append("platform = ?")
        params.append(filters['platform'])
    if filters.get('min_price') is not None:
        where.append("price >= ?")
        params.append(filters['min_price'])
    if filters.get('max_price') is not None:
        where.append("price <= ?")
        params.append(filters['max_price'])
    if filters.get('min_subs') is not None:
        where.append("subscribers >= ?")
        params.append(filters['min_subs'])
    if filters.get('monetized_only'):
        where.append("monetization = 'Enabled'")
    if filters.get('keyword'):
        where.append("(niche LIKE ? OR features LIKE ? OR account_type LIKE ?)")
        kw = f"%{filters['keyword']}%"
        params.extend([kw, kw, kw])

    where_clause = " AND ".join(where)
    return where_clause, params

def browse_listings(update, context, page=0):
    """Shows a paginated list of listings matching current filters (newest/bumped first)."""
    query = update.callback_query
    filters = context.user_data.get('browse_filters', {})
    where_clause, params = _build_listing_query(filters)

    PAGE_SIZE = 5
    offset = page * PAGE_SIZE

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM listings WHERE {where_clause}", params)
    total = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT listing_id, platform, account_type, subscribers, price, monetization
        FROM listings
        WHERE {where_clause}
        ORDER BY COALESCE(last_bumped_at, created_at) DESC
        LIMIT ? OFFSET ?
    """, params + [PAGE_SIZE, offset])
    rows = cursor.fetchall()
    conn.close()

    context.user_data['browse_page'] = page

    if not rows:
        text = "🔍 <b>No listings match your filters.</b>\n\nTry adjusting your search criteria."
        keyboard = [
            [InlineKeyboardButton("🔧 Adjust Filters", callback_data="browse_filter_menu")],
            [InlineKeyboardButton("🔙 Back to Browse", callback_data="browse_menu")]
        ]
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return BROWSE_PLATFORM_LIST

    plat_label = filters.get('platform', 'All Platforms')
    text = f"🛍 <b>{plat_label} Listings</b> ({total} found)\n\nTap a listing to view full details:"

    keyboard = []
    for r in rows:
        subs_fmt = format_number(r['subscribers'])
        price_fmt = f"${int(float(r['price'])):,}" if str(r['price']).replace('.', '', 1).isdigit() else f"${r['price']}"
        mon_icon = "✅" if r['monetization'] == 'Enabled' else "▫️"
        btn_text = f"{r['listing_id']} | {subs_fmt} subs | {price_fmt} {mon_icon}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"browse_view_{r['listing_id']}")])

    # Pagination row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"browse_page_{page-1}"))
    if offset + PAGE_SIZE < total:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"browse_page_{page+1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔧 Filters", callback_data="browse_filter_menu")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Browse", callback_data="browse_menu")])

    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return BROWSE_PLATFORM_LIST

def browse_platform_callback(update, context):
    """Handle platform selection from the browse menu."""
    query = update.callback_query
    platform = query.data.replace("browse_platform_", "")
    filters = context.user_data.get('browse_filters', {})
    filters['platform'] = platform
    context.user_data['browse_filters'] = filters
    return browse_listings(update, context, page=0)

def browse_page_callback(update, context):
    """Handle pagination button clicks."""
    query = update.callback_query
    page = int(query.data.replace("browse_page_", ""))
    return browse_listings(update, context, page=page)

def browse_view_listing(update, context):
    """Show full details of a single listing with screenshots and buttons."""
    query = update.callback_query
    listing_id = query.data.replace("browse_view_", "")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, platform, account_type, subscribers, views, price, 
               monetization, niche, features, region, status, channel_message_id
        FROM listings WHERE listing_id = ? AND status_flag = 'published'
    """, (listing_id,))
    listing = cursor.fetchone()
    conn.close()

    if not listing:
        query.answer("This listing is no longer available.", show_alert=True)
        return browse_listings(update, context, page=context.user_data.get('browse_page', 0))

    (l_id, platform, account_type, subscribers, views, price, monetization, 
     niche, features, region, status, channel_msg_id) = listing

    subs_fmt = format_number(subscribers)
    views_fmt = format_number(views)
    price_fmt = f"${int(float(price)):,}" if str(price).replace('.', '', 1).isdigit() else f"${price}"

    text = (
        f"🎯 <b>{platform} ACCOUNT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>Product ID:</b> <code>{l_id}</code>\n"
        f"👤 <b>Type:</b> {account_type}\n"
        f"🌍 <b>Region:</b> {region or 'N/A'}\n\n"
        f"👥 <b>Subscribers:</b> {subs_fmt}\n"
        f"👀 <b>Views:</b> {views_fmt}\n"
        f"✅ <b>Status:</b> {status or 'N/A'}\n\n"
        f"🗃️ <b>Niche:</b> {niche or 'Mixed'}\n"
        f"🔧 <b>Features:</b> {features or 'N/A'}\n"
        f"💲 <b>Monetization:</b> {monetization or 'N/A'}\n\n"
        f"💵 <b>Price:</b> {price_fmt}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("🛍 Place Order ▪️ Start Escrow", callback_data=f"buy_from_browse_{l_id}")],
    ]
    
    # Add More Info button with link to main channel post
    if channel_msg_id:
        try:
            channel_link = helper_get_tg_url(CHANNEL_ID, int(channel_msg_id))
            keyboard.append([InlineKeyboardButton("ℹ️ More Info & Screenshots", url=channel_link)])
        except:
            pass
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Listings", callback_data=f"browse_page_{context.user_data.get('browse_page', 0)}")])

    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return BROWSE_LISTING_DETAIL

def buy_from_browse_callback(update, context):
    """Start the escrow purchase for a listing selected from the browse menu.
    Uses the same Cryptomus auto-invoice flow as the channel post deep link."""
    query = update.callback_query
    listing_id = query.data.replace("buy_from_browse_", "")
    query.answer()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM listings WHERE listing_id = ? AND status_flag = 'published'", (listing_id,))
    listing = cursor.fetchone()
    conn.close()

    if not listing:
        query.edit_message_text("❌ This listing is no longer available.")
        return browse_menu(update, context)

    price = float(listing["price"])
    escrow_fee = calculate_escrow_fee(price)
    platform = listing["platform"]
    order_number = generate_order_number(platform)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO orders
        (order_number, listing_id, buyer_id, buyer_username, escrow_fee, payment_status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (
        order_number,
        listing_id,
        update.effective_user.id,
        update.effective_user.username or str(update.effective_user.id),
        escrow_fee
    ))
    conn.commit()
    conn.close()

    query.edit_message_text("⏳ Generating your secure payment link, please wait...")
    payment_url = create_cryptomus_invoice(order_number, escrow_fee, listing_id)

    if not payment_url:
        query.message.reply_text("❌ Could not generate payment link. Please contact @smyards for assistance.")
        return BROWSE_LISTING_DETAIL

    text = (
        f"🏁 <b>Escrow Order Initiated!</b>\n\n"
        f"📦 <b>Product ID:</b> <code>{listing_id}</code>\n"
        f"🆔 <b>Order Number:</b> <code>{order_number}</code>\n"
        f"💵 <b>Account Price:</b> ${price:,.0f}\n"
        f"🔐 <b>Escrow Fee (5%, min $5):</b> <b>${escrow_fee:.2f} USDT</b>\n"
        f"───────────────────────\n\n"
        f"To open a secure private group with the seller and admin, "
        f"please pay the escrow fee using the button below.\n\n"
        f"✅ Payment is confirmed <b>automatically</b> — no need to notify us manually."
    )
    keyboard = [
        [InlineKeyboardButton(f"💳 Pay ${escrow_fee:.2f} USDT via Cryptomus", url=payment_url)],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")]
    ]
    query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return CUSTOMER_MENU


def browse_filter_menu(update, context):
    """Shows the filter/search options."""
    query = update.callback_query
    filters = context.user_data.get('browse_filters', {})

    active_summary = []
    if filters.get('platform'):
        active_summary.append(f"Platform: {filters['platform']}")
    if filters.get('min_price') is not None or filters.get('max_price') is not None:
        lo = filters.get('min_price', 0)
        hi = filters.get('max_price', '∞')
        active_summary.append(f"Price: ${lo}–${hi}")
    if filters.get('min_subs') is not None:
        active_summary.append(f"Min Subs: {filters['min_subs']:,}")
    if filters.get('monetized_only'):
        active_summary.append("Monetized only")
    if filters.get('keyword'):
        active_summary.append(f"Keyword: \"{filters['keyword']}\"")

    summary_text = "\n".join(f"• {s}" for s in active_summary) if active_summary else "No filters applied yet."

    text = (
        f"🔍 <b>Search & Filter</b>\n\n"
        f"<b>Active filters:</b>\n{summary_text}\n\n"
        f"Choose what to filter by:"
    )

    keyboard = [
        [InlineKeyboardButton("💵 Set Price Range", callback_data="browse_set_price")],
        [InlineKeyboardButton("👥 Min Subscribers", callback_data="browse_set_subs")],
        [InlineKeyboardButton(
            ("✅ " if filters.get('monetized_only') else "▫️ ") + "Monetized Only",
            callback_data="browse_toggle_monetized"
        )],
        [InlineKeyboardButton("🔤 Search Keyword", callback_data="browse_set_keyword")],
        [InlineKeyboardButton("✅ Apply Filters", callback_data="browse_apply_filters")],
        [InlineKeyboardButton("♻️ Clear All Filters", callback_data="browse_clear_filters")],
        [InlineKeyboardButton("🔙 Back to Browse", callback_data="browse_menu")]
    ]

    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return BROWSE_FILTER_MENU


def browse_toggle_monetized(update, context):
    query = update.callback_query
    filters = context.user_data.get('browse_filters', {})
    filters['monetized_only'] = not filters.get('monetized_only', False)
    context.user_data['browse_filters'] = filters
    return browse_filter_menu(update, context)


def browse_clear_filters(update, context):
    query = update.callback_query
    context.user_data['browse_filters'] = {}
    query.answer("Filters cleared!")
    return browse_filter_menu(update, context)


def browse_apply_filters(update, context):
    """Apply filters and show results."""
    return browse_listings(update, context, page=0)


def browse_set_price_prompt(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "💵 <b>Set Price Range</b>\n\n"
        "Send the range as: <code>min-max</code>\n"
        "Example: <code>50-300</code>\n\n"
        "Or send just a number for minimum only (e.g. <code>100</code>).",
        parse_mode=ParseMode.HTML
    )
    context.user_data['awaiting_filter'] = 'price'
    return BROWSE_FILTER_PRICE


def browse_set_subs_prompt(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "👥 <b>Set Minimum Subscribers</b>\n\n"
        "Send a number, e.g. <code>1000</code>",
        parse_mode=ParseMode.HTML
    )
    context.user_data['awaiting_filter'] = 'subs'
    return BROWSE_FILTER_SUBS


def browse_set_keyword_prompt(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "🔤 <b>Search Keyword</b>\n\n"
        "Send a keyword to search in niche, features, or account type "
        "(e.g. <code>gaming</code>, <code>monetized</code>).",
        parse_mode=ParseMode.HTML
    )
    context.user_data['awaiting_filter'] = 'keyword'
    return BROWSE_SEARCH_KEYWORD


def browse_handle_filter_input(update, context):
    """Handles text input for price range, subs, or keyword filters."""
    text = update.message.text.strip()
    awaiting = context.user_data.get('awaiting_filter')
    filters = context.user_data.get('browse_filters', {})

    if awaiting == 'price':
        try:
            if '-' in text:
                lo, hi = text.split('-', 1)
                filters['min_price'] = float(lo.strip())
                filters['max_price'] = float(hi.strip())
            else:
                filters['min_price'] = float(text.strip())
                filters.pop('max_price', None)
        except ValueError:
            update.message.reply_text("❌ Invalid format. Send like <code>50-300</code>", parse_mode=ParseMode.HTML)
            return BROWSE_FILTER_PRICE

    elif awaiting == 'subs':
        try:
            filters['min_subs'] = int(text.replace(',', '').strip())
        except ValueError:
            update.message.reply_text("❌ Invalid number. Send digits only, e.g. 1000")
            return BROWSE_FILTER_SUBS

    elif awaiting == 'keyword':
        filters['keyword'] = text.strip()

    context.user_data['browse_filters'] = filters
    context.user_data.pop('awaiting_filter', None)

    keyboard = [
        [InlineKeyboardButton("✅ Apply Filters", callback_data="browse_apply_filters")],
        [InlineKeyboardButton("🔧 Set More Filters", callback_data="browse_filter_menu")]
    ]
    update.message.reply_text(
        "✅ Filter saved! Apply now or add more filters.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return BROWSE_FILTER_MENU


def show_user_listings(update, context):   
    query = update.callback_query
    user_id = update.effective_user.id
    
    # --- SQLITE DATABASE FETCH ---
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        # FIX: Only pull from customer_listings if it is strictly 'pending'
        cursor.execute("""
            SELECT listing_id, account_type, status_flag 
            FROM customer_listings WHERE customer_id = ? AND status_flag = 'pending'
            UNION
            SELECT listing_id, account_type, status_flag 
            FROM listings WHERE created_by = ?
        """, (user_id, user_id))
        
        user_listings = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Database error fetching user listings: {e}")
        user_listings = []
    # -----------------------------
    
    if not user_listings:
        text = (
            "📦 <b>Your Listings</b>\n\n"
            "You don't have any YouTube channels currently listed for sale.\n\n"
            "Click below to start a new listing!"
        )
        keyboard = [
            [InlineKeyboardButton("➕ Create New Listing", callback_data="start_sell_flow")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")]
        ]
    else:
        text = "📦 <b>Your Active Listings</b>\n\nSelect a channel below to manage it:"
        keyboard = []
        
        for listing in user_listings:
            l_id = listing['listing_id']
            # FIX: Pulling account_type ("Monetized") instead of Niche
            acc_type = listing['account_type'] if listing['account_type'] else "Channel"
            status = listing['status_flag'].upper() if listing['status_flag'] else "UNKNOWN"
            
            btn_text = f"🆔 {l_id} | {acc_type} ({status})"
            # FIX: Pointing strictly to the new management hub router
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"manage_item_{l_id}")])
            
        keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.answer()
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    return CUSTOMER_MENU



def transactions_log(update, context):
    """Platform Transactions/Feedback Log - PLACEHOLDER"""
    query = update.callback_query
    query.answer()
    
    text = (
        f"📊 <b>Platform Transactions Log</b>\n\n"
        f"<b>Recent Transactions:</b>\n"
        f"(Platform-wide trusted transaction history)\n\n"
        f"✅ User123 → User456: YouTube Channel\n"
        f"   Rating: ⭐⭐⭐⭐⭐ Quick & Professional\n\n"
        f"✅ User789 → User012: Instagram Account\n"
        f"   Rating: ⭐⭐⭐⭐ Smooth Transaction\n\n"
        f"<b>This builds trust in the platform.</b>\n"
        f"(Full implementation coming soon)"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="open_dashboard")]]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return CUSTOMER_MENU	

# transactions_log view
def transactions_log_view(update, context):
    """Show paginated transaction log."""
    query = update.callback_query if update.callback_query else None
    
    page = 0
    if query and query.data.startswith("txlog_page_"):
        page = int(query.data.replace("txlog_page_", ""))
        context.user_data['txlog_page'] = page
    else:
        page = context.user_data.get('txlog_page', 0)
    
    PAGE_SIZE = 10
    offset = page * PAGE_SIZE
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM transactions_log")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT id, order_number, product_id, platform, seller_name, buyer_name, price, txid
        FROM transactions_log
        ORDER BY completed_at DESC
        LIMIT ? OFFSET ?
    """, (PAGE_SIZE, offset))
    transactions = cursor.fetchall()
    conn.close()
    
    if not transactions:
        text = "📊 <b>PLATFORM TRANSACTIONS LOG</b>\n\n📭 No transactions yet."
        keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="open_dashboard")]]
        
        if query:
            query.answer()
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return CUSTOMER_MENU
    
    text = f"📊 <b>PLATFORM TRANSACTIONS LOG</b> (Page {page + 1})\n\n"
    
    platform_emojis = {'YouTube': '📺', 'Instagram': '📷', 'TikTok': '🎵', 'Facebook': '👤'}
    
    for tx_id, order_num, product_id, platform, seller_name, buyer_name, price, txid in transactions:
        emoji = platform_emojis.get(platform, '📱')
        
        # Obfuscate names for privacy
        seller_display = seller_name[:3] + "***" if len(seller_name) > 3 else seller_name
        buyer_display = buyer_name[:3] + "***" if len(buyer_name) > 3 else buyer_name
        
        text += (
            f"✅ <b>Successful Transaction via Escrow</b>\n"
            f"{emoji} <b>Platform:</b> {platform}\n"
            f"🆔 <b>Account ID:</b> <code>{product_id}</code>\n"
            f"🛍 <b>Order:</b> <code>{order_num}</code>\n"
            f"👤 <b>Seller:</b> {seller_display}\n"
            f"👤 <b>Buyer:</b> {buyer_display}\n"
            f"💰 <b>Price:</b> ${price:,.2f}\n"
            f"🔒 <b>Warranty Active</b> ✅\n"
            f"🛍 <b>Account Delivered</b> ✅\n"
        )
        
        if txid:
            text += f"📄 <b>TXid:</b> <a href='{txid}'>View Transaction</a>\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Pagination
    keyboard = []
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ Previous", callback_data=f"txlog_page_{page-1}"))
    if offset + PAGE_SIZE < total:
        nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"txlog_page_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="open_dashboard")])
    
    if query:
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    return CUSTOMER_MENU

def buyer_start(update, context):
    """Start buyer flow"""
    query = update.callback_query
    query.answer()
    
    text = """🛡️ **SMYARDS ESCROW SYSTEM - HOW IT WORKS**

✅ **100% Secure Transactions:**
1. You choose the account you want to buy
2. You pay the escrow fee (5% of price, minimum $5)
3. We hold the payment securely
4. Seller transfers the account to you
5. You confirm receipt
6. We release payment to seller

🛡️ **Your Protection:**
• No risk of scams
• Escrow agent mediates the transaction
• Money-back guarantee if seller fails to deliver
• 24/7 support throughout the process

💰 **Escrow Fee:**
• 5% of the total price
• Minimum $5 fee
• Covers transaction security & support

Click below to enter the Product ID of the account you want to buy:"""
    
    keyboard = [
        [InlineKeyboardButton("🔢 Enter Product ID", callback_data="enter_product_id")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_customer")]
    ]
    
    query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return BUYER_ESCROW_INFO

def buyer_enter_product_id(update, context):
    """Ask for product ID"""
    query = update.callback_query
    query.answer()
    
    text = """🔢 **Enter Product ID**

Please enter the **Product ID** of the account you want to purchase.

You can find the Product ID on the account listing in the main channel @smyard.

**Example:** `YT-088` or `IG-102`

Type the Product ID below:"""
    
    query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN)
    return BUYER_ENTER_PRODUCT_ID

def handle_buyer_product_id(update, context):
    """Handle product ID input from buyer — show full details and escrow fee for confirmation."""
    product_id = update.message.text.strip().upper()
    
    if product_id.lower() == 'cancel':
        update.message.reply_text("❌ Operation cancelled.")
        return customer_start(update, context)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM listings WHERE listing_id = ?",
            (product_id,)
        )
        listing = cursor.fetchone()
        conn.close()
        
        if not listing:
            update.message.reply_text(
                f"❌ **Product not found:** `{product_id}`\n\n"
                "Please check the Product ID and try again.\n"
                "Enter another Product ID or type 'cancel':",
                parse_mode=ParseMode.MARKDOWN
            )
            return BUYER_ENTER_PRODUCT_ID
        
        status_clean = str(listing['status_flag']).strip().lower()
        if status_clean != 'published':
            update.message.reply_text(
                f"❌ This listing is not available for purchase.\n"
                "Enter another Product ID or type 'cancel':",
                parse_mode=ParseMode.MARKDOWN
            )
            return BUYER_ENTER_PRODUCT_ID
        
        price = float(listing['price']) if listing['price'] else 0.0
        escrow_fee = calculate_escrow_fee(price)
        
        subs_fmt = format_number(listing['subscribers'])
        views_fmt = format_number(listing['views'])
        price_fmt = f"${price:,.0f}"
        fee_fmt = f"${escrow_fee:.2f}"

        # Store order info for next step
        context.user_data['pending_order'] = {
            'listing_id': listing['listing_id'],
            'platform': listing['platform'],
            'price': price,
            'escrow_fee': escrow_fee,
            'order_number': generate_order_number(listing['platform'])
        }

        text = (
            f"🎯 <b>{listing['platform']} ACCOUNT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>📋 BASIC INFO</b>\n"
            f"• 🆔 <b>Product ID:</b> <code>{listing['listing_id']}</code>\n"
            f"• 👤 <b>Type:</b> {listing['account_type']}\n"
            f"• 🌍 <b>Region:</b> {listing['region'] or 'N/A'}\n\n"
            f"<b>📊 STATISTICS</b>\n"
            f"• 👥 <b>Subscribers:</b> {subs_fmt}\n"
            f"• 👀 <b>Views:</b> {views_fmt}\n"
            f"• ✅ <b>Status:</b> {listing['status'] or 'N/A'}\n\n"
            f"<b>⚙️ FEATURES</b>\n"
            f"• 🗃️ <b>Niche:</b> {listing['niche'] or 'Mixed'}\n"
            f"• 🔧 <b>Features:</b> {listing['features'] or 'N/A'}\n"
            f"• 💲 <b>Monetization:</b> {listing['monetization'] or 'N/A'}\n\n"
            f"<b>💰 PRICING & ESCROW</b>\n"
            f"• 💵 <b>Account Price:</b> {price_fmt}\n"
            f"• 🔐 <b>Escrow Fee (5%, min $5):</b> <b>{fee_fmt} USDT</b>\n\n"
            f"<b>🛡️ How Escrow Works:</b>\n"
            f"1. You pay the escrow fee\n"
            f"2. Admin creates a private group with you, seller, and themselves\n"
            f"3. Seller transfers the account to you\n"
            f"4. You confirm receipt of the account\n"
            f"5. Admin releases funds to the seller\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        keyboard = [
            [InlineKeyboardButton(f"💳 Pay Escrow Fee ({fee_fmt})", callback_data=f"confirm_pay_escrow_{product_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_escrow_info")]
        ]
        
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return BUYER_PAYMENT_METHODS
        
    except Exception as e:
        logger.error(f"Error in handle_buyer_product_id: {e}", exc_info=True)
        update.message.reply_text("❌ An error occurred. Please try again or contact @smyards")
        return BUYER_ENTER_PRODUCT_ID

def notify_seller_on_order_created(seller_telegram_id, order_number, product_id, price, escrow_fee, buyer_username, context):
    """Notify seller when order created - uses seller_telegram_id field."""
    if not seller_telegram_id:
        logger.warning(f"[SELLER NOTIFY] ❌ seller_telegram_id is NULL for order {order_number}")
        return
    
    if seller_telegram_id == OWNER_ID:
        logger.info(f"[SELLER NOTIFY] Skipping admin-owned listing (seller_id = OWNER_ID)")
        return
    
    try:
        logger.info(f"[SELLER NOTIFY] Sending to seller_telegram_id={seller_telegram_id}")
        
        text = (
            f"🛍 <b>NEW ORDER PLACED ON YOUR LISTING!</b>\n\n"
            f"📦 <b>Product ID:</b> <code>{product_id}</code>\n"
            f"🆔 <b>Order Number:</b> <code>{order_number}</code>\n"
            f"💰 <b>Account Price:</b> ${price:,.2f}\n"
            f"🛡️ <b>Escrow Fee:</b> ${escrow_fee:.2f}\n"
            f"👤 <b>Buyer:</b> @{buyer_username}\n\n"
            f"⏳ <b>Status:</b> Waiting for buyer to complete escrow fee payment...\n\n"
            f"Once payment is confirmed, you'll receive an invitation to the secure deal group."
        )
        
        context.bot.send_message(
            chat_id=int(seller_telegram_id),
            text=text,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"[SELLER NOTIFY] ✅ SUCCESS! Message sent to seller_telegram_id={seller_telegram_id}")
        
    except ValueError as e:
        logger.error(f"[SELLER NOTIFY] ❌ ValueError (bad seller_telegram_id={seller_telegram_id}): {e}")
    except Exception as e:
        logger.error(f"[SELLER NOTIFY] ❌ Exception: {type(e).__name__}: {e}", exc_info=True)
		
def confirm_pay_escrow(update, context):
    """DEBUG VERSION - with proper seller_telegram_id tracking."""
    query = update.callback_query
    query.answer()
    
    product_id = query.data.replace("confirm_pay_escrow_", "")
    pending = context.user_data.get('pending_order', {})
    
    if not pending or pending.get('listing_id') != product_id:
        query.edit_message_text("❌ Order info expired. Please enter the product ID again.")
        return BUYER_ENTER_PRODUCT_ID
    
    listing_id = pending['listing_id']
    platform = pending['platform']
    price = pending['price']
    escrow_fee = pending['escrow_fee']
    order_number = pending['order_number']
    user = update.effective_user
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        logger.info(f"[ORDER-DEBUG] Fetching listing {listing_id}...")
        
        cursor.execute("""
            SELECT created_by, seller_contact, platform, seller_telegram_id 
            FROM listings WHERE listing_id = ?
        """, (listing_id,))
        listing_result = cursor.fetchone()
        
        if listing_result:
            created_by, seller_contact, _, seller_telegram_id = listing_result
            logger.info(f"[ORDER-DEBUG] ✅ Listing found! created_by={created_by}, seller_telegram_id={seller_telegram_id}")
        else:
            seller_telegram_id = None
            seller_contact = None
            logger.warning(f"[ORDER-DEBUG] ❌ Listing {listing_id} NOT FOUND!")
        
        conn.close()

        # Save order with seller_telegram_id
        conn = get_connection()
        cursor = conn.cursor()
        logger.info(f"[ORDER-DEBUG] Saving order with seller_telegram_id={seller_telegram_id}...")
        
        cursor.execute("""
            INSERT OR IGNORE INTO orders
            (order_number, product_id, customer_id, customer_username, platform,
             total_price, escrow_fee, amount_to_pay, payment_method, payment_address,
             payment_status, seller_id, order_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, 'pending')
        """, (
            order_number, listing_id, user.id,
            user.username or str(user.id), platform,
            price, escrow_fee, escrow_fee,
            "cryptomus", "auto-generated",
            seller_telegram_id
        ))
        conn.commit()
        
        cursor.execute("SELECT id FROM orders WHERE order_number = ?", (order_number,))
        order_row = cursor.fetchone()
        conn.close()
        order_db_id = order_row[0] if order_row else 0

        # Notify admin
        notify_admin_on_order_created(
            order_number, listing_id, price, escrow_fee,
            user.username or str(user.id), "seller", order_db_id, context
        )

        # Notify seller using seller_telegram_id
        if seller_telegram_id:
            notify_seller_on_order_created(
                seller_telegram_id, order_number, listing_id, price, escrow_fee,
                user.username or str(user.id), context
            )
        else:
            logger.warning(f"[ORDER-DEBUG] No seller_telegram_id to notify for order {order_number}")

        query.edit_message_text("⏳ Generating your secure payment link, please wait...")

        payment_url = create_cryptomus_invoice(order_number, escrow_fee, listing_id)

        if not payment_url:
            query.edit_message_text(
                "❌ Could not generate payment link right now.\n\n"
                "Please contact @smyards for assistance.",
                parse_mode=ParseMode.HTML
            )
            return CUSTOMER_MENU

        text = (
            f"🏁 <b>Ready to Pay!</b>\n\n"
            f"🆔 <b>Order Number:</b> <code>{order_number}</code>\n"
            f"📦 <b>Product ID:</b> <code>{listing_id}</code>\n"
            f"💵 <b>Escrow Fee:</b> <b>${escrow_fee:.2f} USDT</b>\n\n"
            f"Click the button below to pay securely via Cryptomus.\n\n"
            f"✅ Payment is confirmed <b>automatically</b> — no need to notify us manually."
        )

        keyboard = [
            [InlineKeyboardButton(f"💳 Pay ${escrow_fee:.2f} USDT via Cryptomus", url=payment_url)],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")]
        ]

        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        context.user_data.pop('pending_order', None)
        return CUSTOMER_MENU

    except Exception as e:
        logger.error(f"[ORDER-DEBUG] ❌ CRITICAL ERROR: {e}", exc_info=True)
        query.edit_message_text("❌ An error occurred. Please contact @smyards for assistance.")
        return CUSTOMER_MENU

    except Exception as e:
        logger.error(f"[ORDER-DEBUG] ❌ CRITICAL ERROR in confirm_pay_escrow: {e}", exc_info=True)
        query.edit_message_text("❌ An error occurred. Please contact @smyards for assistance.")
        return CUSTOMER_MENU
		
def handle_payment_method(update, context):
    """Handle payment method selection and show instructions"""
    query = update.callback_query
    query.answer()
    
    payment_methods = {
        "pay_coinbase": "Coinbase", "pay_binance": "Binance",
        "pay_btc": "Bitcoin (BTC)", "pay_eth": "Ethereum (ETH)",
        "pay_usdt": "USDT", "pay_usdc": "USDC"
    }
    
    method_key = query.data
    method_name = payment_methods.get(method_key, "Unknown")
    
    payment_addresses = {
        "pay_coinbase": COINBASE_ADDRESS, "pay_binance": BINANCE_ADDRESS,
        "pay_btc": BTC_ADDRESS, "pay_eth": ETH_ADDRESS,
        "pay_usdt": USDT_ADDRESS, "pay_usdc": USDC_ADDRESS
    }
    
    address = payment_addresses.get(method_key, "")
    
    if not address:
        query.edit_message_text(
            "⚠️ Payment method temporarily unavailable. Please choose another method or contact admin @smyards",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_to_payment_methods")]])
        )
        return BUYER_PAYMENT_METHODS
    
    context.user_data["buy_order"]["payment_method"] = method_name
    context.user_data["buy_order"]["payment_address"] = address
    
    price = context.user_data["buy_order"]["price"]
    escrow_fee = calculate_escrow_fee(price)
    
    network_clean = method_name.split('(')[-1].replace(')', '') if '(' in method_name else method_name
    
    text = f"""💳 **Payment Instructions - {method_name}**

📋 **Order Summary:**
• 🆔 Product ID: `{context.user_data['buy_order']['product_id']}`
• 📱 Platform: {context.user_data['buy_order']['platform']}
• 💵 Account Price: ${price:,.2f}
• 🛡️ Escrow Fee: ${escrow_fee:,.2f}

💰 **Amount to Pay:** **${escrow_fee:,.2f}**

📝 **Send Payment to:**
`{address}`

**Important Instructions:**
1. Send exactly **${escrow_fee:,.2f}** 2. Use the network: **{network_clean}**
3. Do NOT send from an exchange (use personal wallet)
4. After sending, click "✅ Confirm Payment" below
5. We'll verify your payment within 15 minutes

⚠️ **Note:** Include the Product ID in the payment memo: `{context.user_data['buy_order']['product_id']}`"""

    keyboard = [
        [InlineKeyboardButton("✅ I've Paid - Confirm Payment", callback_data="confirm_payment")],
        [InlineKeyboardButton("⬅️ Choose Different Method", callback_data="back_to_payment_methods")]
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return BUYER_PAYMENT_INSTRUCTIONS

def confirm_payment(update, context):
    """Handle payment confirmation"""
    query = update.callback_query
    query.answer()
    
    platform = context.user_data["buy_order"]["platform"]
    order_number = generate_order_number(platform)
    price = context.user_data["buy_order"]["price"]
    escrow_fee = calculate_escrow_fee(price)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO orders (
            order_number, product_id, customer_id, customer_username,
            platform, total_price, escrow_fee, amount_to_pay,
            payment_method, payment_address, payment_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        order_number, context.user_data["buy_order"]["product_id"],
        update.effective_user.id, update.effective_user.username,
        platform, price, escrow_fee, escrow_fee,
        context.user_data["buy_order"]["payment_method"],
        context.user_data["buy_order"]["payment_address"], 'pending'
    ))
    conn.commit()
    conn.close()
    
    admin_text = f"""🆕 **NEW ORDER PLACED!**

📋 **Order Details:**
• 🆔 **Order Number:** `{order_number}`
• 🆔 **Product ID:** `{context.user_data['buy_order']['product_id']}`
• 👤 **Customer:** @{update.effective_user.username} (ID: {update.effective_user.id})
• 📱 **Platform:** {platform}
• 💵 **Account Price:** ${price:,.2f}
• 🛡️ **Escrow Fee:** ${escrow_fee:,.2f}
• 💳 **Payment Method:** {context.user_data['buy_order']['payment_method']}
• ⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Action Required:**
1. Verify payment received
2. Contact seller
3. Create group chat with buyer & seller
4. Process the transaction"""

    keyboard = [[
        InlineKeyboardButton("✅ Verify Payment", callback_data=f"verify_payment_{order_number}"),
        InlineKeyboardButton("📞 Contact Buyer", url=f"https://t.me/{update.effective_user.username}" if update.effective_user.username else f"tg://user?id={update.effective_user.id}")
    ]]
    
    context.bot.send_message(
        chat_id=OWNER_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    text = f"""✅ **Order Submitted Successfully!**

📋 **Your Order Details:**
• 🆔 **Order Number:** `{order_number}`
• 🆔 **Product ID:** `{context.user_data['buy_order']['product_id']}`
• 📱 **Platform:** {platform}
• 💵 **Amount Paid:** ${escrow_fee:,.2f}
• 💳 **Payment Method:** {context.user_data['buy_order']['payment_method']}

📞 **Next Steps:**
1. We've notified our escrow agent (@smyards)
2. They will verify your payment within 15 minutes
3. Once verified, they'll contact the seller
4. You'll be added to a secure group chat with the seller and agent
5. Complete the transaction safely

▶️ **Please wait for our agent to contact you.**
You can also contact us @smyards if you have any questions."""

    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_customer")]]), parse_mode=ParseMode.MARKDOWN)
    
    if "buy_order" in context.user_data:
        del context.user_data["buy_order"]
    
    return CUSTOMER_MENU

 


 
    
# ===== CUSTOMER SUBMISSION HANDLER =====    
def seller_start(update, context):
    """Start seller flow"""
    query = update.callback_query
    query.answer()
    
    text = """💰 **SELL YOUR ACCOUNT**

✅ **Why Sell With SMYARDS:**
• Reach thousands of serious buyers
• Secure escrow protection
• Get paid quickly & safely
• Professional listing presentation

📋 **How It Works:**
1. Submit your account details
2. Our team reviews & approves
3. Your account gets listed on @smyard
4. Buyers contact you via our system
5. We handle secure payment via escrow
6. You get paid after successful transfer

⏰ **Approval Time:** 2-12 hours
💰 **Commission:** 5% escrow fee (paid by buyer)
🛡️ **Security:** 100% protected transactions

Ready to list your account?"""
    
    keyboard = [
        [InlineKeyboardButton("📝 List Your Account Now", callback_data="seller_list_account")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_customer")]
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return SELLER_INFO

def seller_list_account(update, context):
    """Start listing process for seller"""
    query = update.callback_query
    query.answer()
    
    keyboard = [[InlineKeyboardButton(platform, callback_data=f"customer_platform_{platform}")] for platform in PLATFORMS]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_seller_info")])
    
    query.edit_message_text(
        text="📱 **Select Platform**\n\nChoose the platform of the account you want to sell:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return SELLER_PLATFORM

def customer_platform_callback(update, context):
    """Handle platform selection for customer seller"""
    query = update.callback_query
    query.answer()
    
    platform = query.data.replace("customer_platform_", "")
    context.user_data["customer_listing"] = {"platform": platform}
    
    account_types = YOUTUBE_TYPES if platform == "YouTube" else DEFAULT_TYPES
    
    keyboard = [[InlineKeyboardButton(acc_type, callback_data=f"customer_type_{acc_type}")] for acc_type in account_types]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_to_seller_platform")])
    
    query.edit_message_text(
        text=f"**Platform:** {platform}\n\n**Select Account Type:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    return SELLER_TYPE

def customer_type_callback(update, context):
    """Handle type selection for customer seller"""
    query = update.callback_query
    query.answer()
    
    acc_type = query.data.replace("customer_type_", "")
    context.user_data["customer_listing"]["account_type"] = acc_type
    
    text = f"""📝 **Enter Account Details**

**Platform:** {context.user_data['customer_listing']['platform']}
**Type:** {acc_type}

Please send the details in this format (one per line):

**Subscribers:** [number]
**Views:** [number]
**Niche:** [text]
**Features:** [text]
**Monetization:** [Enabled/Disabled]
**Region:** [text]
**Status:** [text - e.g., "No Strikes"]

**Example:**
Subscribers: 15000
Views: 250000
Niche: Gaming
Features: Monetization enabled, Custom URL
Monetization: Enabled
Region: USA
Status: No Strikes

Type 'cancel' to cancel."""

    query.edit_message_text(text=text, parse_mode=ParseMode.MARKDOWN)
    return SELLER_DETAILS

def handle_customer_details(update, context):
    """Handle customer seller details input - HARDENED PARSING"""
    text = update.message.text
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Listing cancelled.")
        return customer_start(update, context)
    
    if "customer_listing" not in context.user_data:
        context.user_data["customer_listing"] = {}
    
    details = {}
    lines_processed = 0
    
    for line in text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = [part.strip() for part in line.split(':', 1)]
            key_lower = key.lower()
            
            if 'sub' in key_lower:
                try: details['subscribers'] = int(value.replace(',', ''))
                except: details['subscribers'] = value
                lines_processed += 1
            elif 'view' in key_lower:
                try: details['views'] = int(value.replace(',', ''))
                except: details['views'] = value
                lines_processed += 1
            elif 'niche' in key_lower:
                details['niche'] = value
                lines_processed += 1
            elif 'feature' in key_lower:
                details['features'] = value
                lines_processed += 1
            elif 'monetiz' in key_lower:
                details['monetization'] = value
                lines_processed += 1
            elif 'region' in key_lower or 'country' in key_lower:
                details['region'] = value
                lines_processed += 1
            elif 'status' in key_lower:
                details['status'] = value
                lines_processed += 1
    
    context.user_data["customer_listing"].update(details)
    
    if lines_processed < 3: 
        update.message.reply_text(
            "⚠️ **Please provide more details.**\n\n"
            "Ensure you are using the correct format with colons (e.g., `Subscribers: 1000`).\n"
            "Provide at least 3 fields to continue.\n\n"
            "Type 'cancel' to cancel.",
            parse_mode=ParseMode.MARKDOWN
        )
        return SELLER_DETAILS
    
    update.message.reply_text(
        "💰 **Enter Your Asking Price (USD)**\n\n"
        "Enter the price you want to sell your account for.\n"
        "**Example:** 500\n\n"
        "Type 'cancel' to cancel.",
        parse_mode=ParseMode.MARKDOWN
    )
    return SELLER_PRICE

def handle_customer_price(update, context):
    """Handle customer seller price input"""
    text = update.message.text
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Listing cancelled.")
        return customer_start(update, context)
    
    try:
        price = float(text)
        context.user_data["customer_listing"]["price"] = price
        
        platform = context.user_data["customer_listing"]["platform"]
        # Assign final YT-xxx ID at submission time (no temp CYT- prefix)
        platform_codes = {'YouTube': 'YT', 'TikTok': 'TT', 'Instagram': 'IG', 'Facebook': 'FB'}
        platform_code = platform_codes.get(platform, platform[:2].upper())

        conn = get_connection()
        cursor = conn.cursor()
        # Check both tables to avoid ID conflicts with pending customer listings
        cursor.execute("SELECT listing_id FROM listings WHERE listing_id LIKE ?", (f"{platform_code}-%",))
        existing_main = [r[0] for r in cursor.fetchall()]
        cursor.execute("SELECT listing_id FROM customer_listings WHERE listing_id LIKE ?", (f"{platform_code}-%",))
        existing_customer = [r[0] for r in cursor.fetchall()]
        conn.close()

        max_num = 0
        for eid in existing_main + existing_customer:
            parts = eid.split('-')
            if len(parts) == 2 and parts[1].isdigit():
                max_num = max(max_num, int(parts[1]))

        listing_id = f"{platform_code}-{max_num + 1:03d}"
        context.user_data["customer_listing"]["listing_id"] = listing_id
        
        update.message.reply_text(
            "📞 **Enter Your Contact Information**\n\n"
            "This is how buyers will contact you.\n"
            "**Examples:**\n"
            "• https://t.me/yourusername\n"
            "• https://wa.me/1234567890\n"
            "• your@email.com\n\n"
            "Type 'skip' to use Telegram only, or 'cancel' to cancel.",
            parse_mode=ParseMode.MARKDOWN
        )
        return SELLER_CONTACT
        
    except ValueError:
        update.message.reply_text("❌ Invalid price. Please enter a number (e.g., 500):")
        return SELLER_PRICE

def handle_customer_contact(update, context):
    """Handle customer seller contact input"""
    text = update.message.text.strip()
    
    if text.lower() == 'cancel':
        update.message.reply_text("❌ Listing cancelled.")
        return customer_start(update, context)
    
    if text.lower() == 'skip':
        context.user_data["customer_listing"]["seller_contact"] = f"https://t.me/{update.effective_user.username}" if update.effective_user.username else f"tg://user?id={update.effective_user.id}"
    else:
        context.user_data["customer_listing"]["seller_contact"] = text
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, add screenshots", callback_data="customer_add_screenshots")],
        [InlineKeyboardButton("➡️ No, skip screenshots", callback_data="customer_skip_screenshots")]
    ]
    
    update.message.reply_text(
        f"📸 **Add Screenshots**\n\n"
        f"You can add up to {MAX_SCREENSHOTS} screenshots of your account.\n"
        f"Screenshots help buyers verify your account and increase sales.\n\n"
        f"Would you like to add screenshots now?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELLER_SCREENSHOTS

def customer_add_screenshots(update, context):
    """Start screenshot upload for customer"""
    query = update.callback_query
    query.answer()
    
    context.user_data["customer_screenshots"] = []
    
    query.edit_message_text(
        f"📸 **Upload Screenshots**\n\n"
        f"You can upload up to {MAX_SCREENSHOTS} screenshots.\n"
        f"Send photos one by one.\n\n"
        f"**When finished, type 'done'**\n"
        f"**To cancel, type 'cancel'**\n\n"
        f"Ready for screenshot 1:"
    )
    return SELLER_SCREENSHOTS

def handle_customer_screenshot_upload(update, context):
    """Handle customer screenshot upload"""
    if 'customer_screenshots' not in context.user_data:
        context.user_data['customer_screenshots'] = []
    
    if update.message.photo:
        photo = update.message.photo[-1]
        context.user_data['customer_screenshots'].append(photo.file_id)
        
        count = len(context.user_data['customer_screenshots'])
        
        if count >= MAX_SCREENSHOTS:
            update.message.reply_text(f"✅ Maximum {MAX_SCREENSHOTS} screenshots reached!")
            return show_customer_preview(update, context)
        else:
            update.message.reply_text(f"📸 Screenshot {count} received!\nSend another photo or type 'done' to finish.")
    elif update.message.text:
        text = update.message.text.lower()
        if text == 'done':
            return show_customer_preview(update, context)
        elif text == 'cancel':
            update.message.reply_text("❌ Listing cancelled.")
            return customer_start(update, context)
        else:
            update.message.reply_text("Please send photos or type 'done' to finish.")
    
    return SELLER_SCREENSHOTS

def show_customer_preview(update, context):
    """Show preview for customer seller"""
    listing = context.user_data["customer_listing"]
    screenshots = context.user_data.get("customer_screenshots", [])
    
    price_formatted = f"${listing.get('price', 0):,.2f}"
    
    text = f"""📋 **LISTING PREVIEW**

✅ **Your account is ready for submission!**

📋 **Account Details:**
• 🆔 **Listing ID:** `{listing.get('listing_id')}`
• 📱 **Platform:** {listing.get('platform')}
• 👤 **Type:** {listing.get('account_type')}
• 🌍 **Region:** {listing.get('region', 'USA')}
• 👥 **Subscribers:** {listing.get('subscribers', 'N/A')}
• 👀 **Views:** {listing.get('views', 'N/A')}
• ✅ **Status:** {listing.get('status', 'No Strikes')}
• 🗃️ **Niche:** {listing.get('niche', 'Mixed')}
• 🔧 **Features:** {listing.get('features', 'N/A')}
• 💲 **Monetization:** {listing.get('monetization', 'Enabled')}
• 💰 **Price:** {price_formatted}
• 📞 **Contact:** {listing.get('seller_contact', 'Via Telegram')}
• 📸 **Screenshots:** {len(screenshots)} uploaded

⏰ **What Happens Next:**
1. You submit this listing
2. Our team reviews it (2-12 hours)
3. If approved, it gets listed on @smyard
4. You'll be notified when it's live
5. Buyers can then contact you

**Ready to submit?**"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Submit for Review", callback_data="customer_submit_listing")],
        [InlineKeyboardButton("✏️ Edit Again", callback_data="customer_edit_again")],
        [InlineKeyboardButton("❌ Cancel", callback_data="customer_cancel_listing")]
    ]
    
    if update.message:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        query = update.callback_query
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    return SELLER_CONFIRM

def customer_skip_screenshots(update, context):
    """Skip screenshots for customer"""
    query = update.callback_query
    query.answer()
    
    context.user_data["customer_screenshots"] = []
    return show_customer_preview(update, context)

def customer_submit_listing(update, context):
    """Submit customer listing for review"""
    query = update.callback_query
    query.answer()
    
    listing = context.user_data.get("customer_listing", {})
    screenshots = context.user_data.get("customer_screenshots", [])
    
    # Save to database securely
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO customer_listings (
                listing_id, platform, account_type, subscribers, views,
                niche, features, monetization, region, status, price,
                screenshots, seller_contact, customer_id, customer_username,
                status_flag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing.get('listing_id'),
            listing.get('platform'),
            listing.get('account_type'),
            listing.get('subscribers', 0),
            listing.get('views', 0),
            listing.get('niche', 'Mixed'),
            listing.get('features', 'N/A'),
            listing.get('monetization', 'Enabled'),
            listing.get('region', 'USA'),
            listing.get('status', 'No Strikes'),
            listing.get('price'),
            json.dumps(screenshots),
            listing.get('seller_contact'),
            update.effective_user.id,
            update.effective_user.username,
            'pending'
        ))
        conn.commit()
    finally:
        conn.close()
    
    # Notify admin
    admin_text = f"""🆕 **NEW CUSTOMER LISTING FOR REVIEW**

📋 **Listing Details:**
• 🆔 **Listing ID:** `{listing.get('listing_id')}`
• 👤 **Seller:** @{update.effective_user.username} (ID: {update.effective_user.id})
• 📱 **Platform:** {listing.get('platform')}
• 👤 **Type:** {listing.get('account_type')}
• 👥 **Subscribers:** {listing.get('subscribers', 'N/A')}
• 👀 **Views:** {listing.get('views', 'N/A')}
• 💰 **Price:** ${listing.get('price', 0):,.2f}
• 📸 **Screenshots:** {len(screenshots)} uploaded
• 📞 **Contact:** {listing.get('seller_contact')}
• ⏰ **Submitted:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Approve this listing to publish it on @smyard**"""

    keyboard = [[
        InlineKeyboardButton("✅ Approve & Publish", callback_data=f"approve_listing_{listing.get('listing_id')}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_listing_{listing.get('listing_id')}")
    ]]
    
    context.bot.send_message(
        chat_id=OWNER_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Confirm to customer
    text = f"""✅ **Listing Submitted Successfully!**

📋 **Your Listing Details:**
• 🆔 **Listing ID:** `{listing.get('listing_id')}`
• 📱 **Platform:** {listing.get('platform')}
• 💰 **Price:** ${listing.get('price', 0):,.2f}
• 📸 **Screenshots:** {len(screenshots)} uploaded

⏰ **What Happens Next:**
1. Our team will review your listing
2. Approval time: 2-12 hours
3. You'll be notified when it's approved
4. Once approved, it will be listed on @smyard
5. Buyers can then contact you

📞 **Need help?** Contact @smyards

Thank you for choosing SMYARDS!"""
    
    keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_customer")]]
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    
    # Clear customer data elegantly
    context.user_data.pop("customer_listing", None)
    context.user_data.pop("customer_screenshots", None)
    
    return CUSTOMER_MENU

	
	
	
	
    
    
# ===== ADMIN APPROVAL HANDLERS =====
def approve_customer_listing(update, context):
    """Approve and publish a customer listing - FIXED FOR UNIFIED PIPELINE"""
    query = update.callback_query
    query.answer()
    
    listing_id = query.data.replace("approve_listing_", "")
    logger.info(f"Admin approving customer listing: {listing_id}")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_listings WHERE listing_id = ?", (listing_id,))
        customer_listing = cursor.fetchone()
        
        if not customer_listing:
            query.edit_message_text("❌ Listing not found.")
            return
        
        # Get column names
        cursor.execute("PRAGMA table_info(customer_listings)")
        columns = [col[1] for col in cursor.fetchall()]
        listing_dict = dict(zip(columns, customer_listing))
        
        # Convert screenshots
        screenshots = json.loads(listing_dict.get('screenshots', '[]'))
        
        # ID was already assigned at submission time — reuse it directly
        new_listing_id = listing_id
        logger.info(f"Approving customer listing with pre-assigned ID: {new_listing_id}")
        
        # Prepare listing data
        listing_data = {
            'listing_id': new_listing_id,
            'platform': listing_dict.get('platform'),
            'account_type': listing_dict.get('account_type'),
            'price': listing_dict.get('price'),
            'subscribers': listing_dict.get('subscribers'),
            'views': listing_dict.get('views'),
            'niche': listing_dict.get('niche'),
            'features': listing_dict.get('features'),
            'monetization': listing_dict.get('monetization'),
            'region': listing_dict.get('region'),
            'status': listing_dict.get('status'),
            'seller_contact': listing_dict.get('seller_contact')
        }
        
        # --- NEW UNIFIED PUBLISHING PIPELINE ---
        
        # 1. Publish to main channel directly (handles album + caption + buttons)
        main_message_id = publish_to_main_channel(
            listing=listing_data, 
            screenshots=screenshots, 
            bot=context.bot
        )
        
        if not main_message_id:
            raise Exception("Failed to publish to main channel")
            
        # 2. Stock channel posting deprecated — browsing now happens in-bot
        stock_message_id = admin_create_stock_post(
            listing=listing_data, 
            bot=context.bot, 
            main_message_id=main_message_id
        )
        
        # 3. Save to main listings table
        cursor.execute('''
            INSERT INTO listings (
                listing_id, platform, account_type, subscribers, views,
                niche, features, monetization, region, status, price,
                screenshots, seller_contact, status_flag, channel_message_id, 
                screenshot_message_id, discussion_message_id, stock_message_id, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            new_listing_id, listing_dict.get('platform'), listing_dict.get('account_type'),
            listing_dict.get('subscribers', 0), listing_dict.get('views', 0),
            listing_dict.get('niche', 'Mixed'), listing_dict.get('features', 'N/A'),
            listing_dict.get('monetization', 'Enabled'), listing_dict.get('region', 'USA'),
            listing_dict.get('status', 'No Strikes'), listing_dict.get('price'),
            json.dumps(screenshots), listing_dict.get('seller_contact'), 'published',
            str(main_message_id), 
            None,  # screenshot_message_id obsolete
            None,  # discussion_message_id obsolete
            str(stock_message_id) if stock_message_id else None, 
            listing_dict.get('customer_id')
        ))
        
        # Update customer listing status
        cursor.execute("UPDATE customer_listings SET status_flag = 'approved' WHERE listing_id = ?", (listing_id,))
        conn.commit()
        
        # Notify seller
        try:
            seller_text = f"""✅ **Your Listing Has Been Approved!**\n\n🎉 Congratulations! Your account has been listed on @smyard.\n\n📋 **Listing Details:**\n• 🆔 **New Product ID:** `{new_listing_id}`\n• 📱 **Platform:** {listing_dict.get('platform')}\n• 💰 **Price:** ${float(listing_dict.get('price', 0)):,.2f}\n• 🌐 **View Listing:** https://t.me/{str(CHANNEL_ID).replace('@', '')}/{main_message_id}\n\nThank you for choosing SMYARDS! 🚀"""
            context.bot.send_message(
                chat_id=listing_dict.get('customer_id'),
                text=seller_text,
                parse_mode='MARKDOWN'
            )
        except Exception as e:
            logger.error(f"Error notifying seller: {e}")
        
        query.edit_message_text(
            f"✅ Listing approved and published!\n• 🆔 ID: `{new_listing_id}`\n• Main Channel: ✅\n• In-Bot Browse: ✅",
            parse_mode='MARKDOWN'
        )
        
    except Exception as e:
        logger.error(f"Error approving listing: {e}", exc_info=True)
        query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    finally:
        conn.close()

def reject_customer_listing(update, context):
    """Reject a customer listing"""
    query = update.callback_query
    query.answer()
    
    listing_id = query.data.replace("reject_listing_", "")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE customer_listings SET status_flag = 'rejected' WHERE listing_id = ?", (listing_id,))
        conn.commit()
    finally:
        conn.close()
    
    query.edit_message_text(f"❌ Listing `{listing_id}` has been rejected.", parse_mode=ParseMode.MARKDOWN)

	
# ===== BACK BUTTON HANDLERS =====
def back_to_customer(update, context):
    return customer_start(update, context)

def back_to_escrow_info(update, context):
    return buyer_start(update, context)

def back_to_seller_info(update, context):
    return seller_start(update, context)

def back_to_seller_platform(update, context):
    return seller_list_account(update, context)

def back_to_payment_methods(update, context):
    """Go back to payment methods"""
    query = update.callback_query
    query.answer()
    
    if "buy_order" not in context.user_data:
        return buyer_enter_product_id(update, context)
    
    order = context.user_data["buy_order"]
    
    text = f"""✅ **Product Details:**

📋 **Account:**
• 🆔 **Product ID:** `{order['product_id']}`
• 📱 **Platform:** {order['platform']}
• 👤 **Type:** {order['account_type']}
• 👥 **Subscribers:** {order['subscribers']:,}
• 👀 **Views:** {order['views']:,}
• 🗃️ **Niche:** {order['niche']}

💰 **Pricing:**
• 💵 **Account Price:** ${order['price']:,.2f}
• 🛡️ **Escrow Fee (5%):** ${calculate_escrow_fee(order['price']):,.2f}

Choose your payment method:"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Coinbase", callback_data="pay_coinbase")],
        [InlineKeyboardButton("📊 Binance", callback_data="pay_binance")],
        [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data="pay_btc")],
        [InlineKeyboardButton("Ξ Ethereum (ETH)", callback_data="pay_eth")],
        [InlineKeyboardButton("💵 USDT", callback_data="pay_usdt")],
        [InlineKeyboardButton("💳 USDC", callback_data="pay_usdc")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_escrow_info")]
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    return BUYER_PAYMENT_METHODS

def admin_panel(update, context):
    return admin_start(update, context)

def admin_start(update, context):
    """REORGANIZED Admin Dashboard"""
    query = update.callback_query
    user = update.effective_user
    
    dashboard_text = (
        f"✅ <b>ADMIN DASHBOARD</b>\n\n"
        f"Welcome, {user.first_name}!"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ New Listing", callback_data="new_listing")],
        [InlineKeyboardButton("📦 Accounts Market", callback_data="view_listings")],
        [InlineKeyboardButton("📦 Orders", callback_data="admin_orders_panel")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
    ]
    
    if query:
        query.answer()
        query.edit_message_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    else:
        update.message.reply_text(
            dashboard_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    return MAIN_MENU

def admin_settings(update, context):
    """Admin Settings - PLACEHOLDER"""
    query = update.callback_query
    query.answer()
    
    text = (
        f"⚙️ <b>Admin Settings</b>\n\n"
        f"<b>1. Listing Bump Settings</b>\n"
        f"   • Global bump cooldown: 3 days\n"
        f"   • (To be configurable)\n\n"
        f"<b>2. User Profiles & Badges</b>\n"
        f"   • Manage user badges\n"
        f"   • Manage user status\n"
        f"   • (To be implemented)\n\n"
        f"<b>3. Reviews & Feedback Management</b>\n"
        f"   • View all reviews\n"
        f"   • Edit/remove reviews\n"
        f"   • (To be implemented)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔧 Bump Settings", callback_data="bump_settings")],
        [InlineKeyboardButton("👥 User Profiles", callback_data="user_profiles")],
        [InlineKeyboardButton("⭐ Reviews Management", callback_data="reviews_management")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")],
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU	
    
    
    
    
# ===== GLOBAL CALLBACK HANDLER =====

# CUSTOMER CALLBACK
def customer_callback(update, context):
    query = update.callback_query
    query.answer()
    data = query.data
    
    # 🚨 CRITICAL DEBUG: If clicking buttons does nothing, check your 'bot_debug.log'
    # or terminal. If you don't see this log, the callback isn't reaching the function.
    logger.info(f"Customer callback received: {data}")
    
    routes = {
        "start_customer_mode": customer_start,
        "customer_main": customer_start,
        "open_dashboard": customer_start, 
        "buyer_start": buyer_start,
        "enter_product_id": buyer_enter_product_id,
        "confirm_payment": confirm_payment,
        "seller_start": seller_start,
        "seller_list_account": seller_list_account,
        "customer_add_screenshots": customer_add_screenshots,
        "customer_skip_screenshots": customer_skip_screenshots,
        "customer_submit_listing": customer_submit_listing,
        "back_to_customer": back_to_customer,
        "back_to_escrow_info": back_to_escrow_info,
        "back_to_seller_info": back_to_seller_info,
        "back_to_seller_platform": back_to_seller_platform,
        "back_to_payment_methods": back_to_payment_methods,
        "admin_panel": admin_panel,
        "user_profile_feedback": user_profile_feedback,
        "transactions_log": transactions_log_view,
        "open_dashboard": customer_start,
		
        # --- DASHBOARD & MANAGEMENT ROUTES ---
        "view_my_listings": show_user_listings,
        "return_listings_view": show_user_listings,
        "back_to_customer_start": customer_start,
        "start_sell_flow": seller_start, 
        "customer_support": customer_support_callback,
        "customer_trigger_sold": customer_manage_item_callback,
        "customer_confirm_sold_execution": customer_confirm_sold_callback,

        # --- BROWSE & SEARCH ROUTES ---
        "browse_menu": browse_menu,
        "browse_filter_menu": browse_filter_menu,
        "browse_toggle_monetized": browse_toggle_monetized,
        "browse_clear_filters": browse_clear_filters,
        "browse_apply_filters": browse_apply_filters,
        "browse_set_price": browse_set_price_prompt,
        "browse_set_subs": browse_set_subs_prompt,
        "browse_set_keyword": browse_set_keyword_prompt,
    }
    
    # --- ROUTING ---
    if data in routes:
        return routes[data](update, context)
        
    # --- DYNAMIC HUB HANDLERS ---
    if data.startswith("manage_item_") or data.startswith("bump_item_"):
        return customer_manage_item_callback(update, context)
    elif data.startswith("pay_"):
        return handle_payment_method(update, context)
    elif data.startswith("customer_platform_"):
        return customer_platform_callback(update, context)
    elif data.startswith("customer_type_"):
        return customer_type_callback(update, context)
    elif data == "customer_edit_again":
        query.edit_message_text("✏️ Send corrected details in same format as before:")
        return SELLER_DETAILS
    elif data == "customer_cancel_listing":
        query.edit_message_text("❌ Listing cancelled.")
        return customer_start(update, context)
    elif data.startswith("browse_platform_"):
        return browse_platform_callback(update, context)
    elif data.startswith("browse_page_"):
        return browse_page_callback(update, context)
    elif data.startswith("browse_view_"):
        return browse_view_listing(update, context)
    elif data.startswith("buy_from_browse_"):
        return buy_from_browse_callback(update, context)
    elif data == "customer_my_orders":
        return customer_my_orders(update, context)
    elif data.startswith("customer_order_"):
        return customer_view_order_detail(update, context)
    elif data.startswith("confirm_pay_escrow_"):
        return confirm_pay_escrow(update, context)
    elif data.startswith("txlog_page_"):
        return transactions_log_view(update, context)
    
    # ⚠️ DEBUGGING CATCH-ALL
    logger.warning(f"❌ UNHANDLED CALLBACK DATA: {data}")
    query.message.reply_text(f"⚠️ Error: Button not configured for data '{data}'. Check your logs.")
    return CUSTOMER_MENU

def customer_support_callback(update, context):
    """Displays the Support & FAQ panel"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    query = update.callback_query
    query.answer()
    
    text = (
        "🎧 **SMyards Support & FAQ**\n\n"
        "🤝 **How does escrow work?**\n"
        "The buyer pays the secure escrow bot. Once the funds are confirmed, the seller safely hands over the channel assets. After verification, funds are released to the seller.\n\n"
        "📞 Need urgent admin help? Contact @smyards directly."
    )
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")]]
    query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    # Stays in the customer menu state
    return CUSTOMER_MENU

def verify_payment(update, context):
    """Admin verifies payment"""
    query = update.callback_query
    query.answer()
    order_number = query.data.replace("verify_payment_", "")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET payment_status = 'verified' WHERE order_number = ?", (order_number,))
        cursor.execute("SELECT customer_id FROM orders WHERE order_number = ?", (order_number,))
        result = cursor.fetchone()
        conn.commit()
    finally:
        conn.close()
    
    if result:
        try:
            context.bot.send_message(
                chat_id=result[0],
                text=f"✅ **Payment Verified!**\n\nYour payment for order `{order_number}` has been verified!\n\nOur agent will now contact the seller and create a secure group chat for the transaction.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error notifying customer: {e}")
            
    query.edit_message_text(f"✅ Payment for order `{order_number}` verified!\nCustomer has been notified.", parse_mode=ParseMode.MARKDOWN)





# ===== ORDER MANAGEMENT SYSTEM ===== #

def add_orders_table_columns():
    """Add missing columns to orders table for order management."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(orders)")
        existing_cols = {col[1] for col in cursor.fetchall()}
        
        # Add seller_id if missing
        if 'seller_id' not in existing_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN seller_id INTEGER")
            logger.info("Added seller_id column to orders table")
        
        # Add transaction_group_link if missing
        if 'transaction_group_link' not in existing_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN transaction_group_link TEXT")
            logger.info("Added transaction_group_link column to orders table")
        
        # Add payment_confirmed_at if missing
        if 'payment_confirmed_at' not in existing_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN payment_confirmed_at DATETIME")
            logger.info("Added payment_confirmed_at column to orders table")
        
        # Add completed_at if missing
        if 'completed_at' not in existing_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN completed_at DATETIME")
            logger.info("Added completed_at column to orders table")
        
        # Add order_status if missing (pending, group_link_set, completed)
        if 'order_status' not in existing_cols:
            cursor.execute("ALTER TABLE orders ADD COLUMN order_status TEXT DEFAULT 'pending'")
            logger.info("Added order_status column to orders table")
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding orders columns: {e}")


def admin_orders_panel(update, context):
    """Show admin the pending orders panel (only orders where payment is confirmed)."""
    query = update.callback_query
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, product_id, platform, total_price, escrow_fee, 
               customer_username, order_status, created_at
        FROM orders
        WHERE payment_status = 'confirmed' AND order_status IN ('pending', 'group_link_set')
        ORDER BY created_at DESC
        LIMIT 10
    """)
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        text = "📦 <b>PENDING ORDERS</b>\n\n✅ No pending orders right now!"
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")]]
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return MAIN_MENU

    text = "📦 <b>PENDING ORDERS</b>\n\n"
    keyboard = []

    for order in orders:
        order_id, order_num, product_id, platform, price, fee, buyer, status, created = order
        status_emoji = "⏳" if status == "pending" else "🔗"
        
        text += (
            f"{status_emoji} <b>{order_num}</b> | {platform}\n"
            f"💰 ${price:,.0f} (Fee: ${fee:.2f})\n"
            f"👤 {buyer}\n"
            f"📅 {created[:10]}\n\n"
        )
        
        keyboard.append([
            InlineKeyboardButton(f"View {order_num}", callback_data=f"admin_order_{order_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back_main")])
    
    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU


def admin_view_order_detail(update, context):
    """Show full order details for admin."""
    query = update.callback_query
    order_id = int(query.data.replace("admin_order_", ""))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM orders WHERE id = ?
    """, (order_id,))
    order = cursor.fetchone()
    
    if not order:
        query.answer("Order not found.", show_alert=True)
        return MAIN_MENU
    
    # Get column names
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    order_dict = dict(zip(columns, order))
    conn.close()

    # Get listing info for product details
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_type, niche FROM listings WHERE listing_id = ?", 
                   (order_dict['product_id'],))
    listing = cursor.fetchone()
    conn.close()

    account_type = listing[0] if listing else "N/A"
    niche = listing[1] if listing else "N/A"

    status_badge = {
        'pending': '⏳ Awaiting Payment',
        'group_link_set': '🔗 Group Link Set',
        'completed': '✅ Completed'
    }.get(order_dict['order_status'], order_dict['order_status'])

    text = (
        f"<b>📦 ORDER DETAILS</b>\n\n"
        f"<b>Order Number:</b> <code>{order_dict['order_number']}</code>\n"
        f"<b>Status:</b> {status_badge}\n\n"
        f"<b>📋 PRODUCT INFO</b>\n"
        f"• <b>Product ID:</b> <code>{order_dict['product_id']}</code>\n"
        f"• <b>Platform:</b> {order_dict['platform']}\n"
        f"• <b>Type:</b> {account_type}\n"
        f"• <b>Niche:</b> {niche}\n\n"
        f"<b>💳 PRICING</b>\n"
        f"• <b>Account Price:</b> ${order_dict['total_price']:,.2f}\n"
        f"• <b>Escrow Fee:</b> ${order_dict['escrow_fee']:.2f}\n\n"
        f"<b>👥 BUYER INFO</b>\n"
        f"• <b>Username:</b> @{order_dict['customer_username']}\n"
        f"• <b>ID:</b> <code>{order_dict['customer_id']}</code>\n\n"
        f"<b>📅 TIMELINE</b>\n"
        f"• <b>Order Created:</b> {order_dict['created_at']}\n"
        f"• <b>Payment Confirmed:</b> {order_dict['payment_confirmed_at'] or 'Pending'}\n\n"
        f"<b>🔗 GROUP LINK STATUS</b>\n"
    )
    
    if order_dict['transaction_group_link']:
        text += f"✅ Set: {order_dict['transaction_group_link']}\n"
    else:
        text += f"⏳ Not yet set\n"

    keyboard = []
    
    if not order_dict['transaction_group_link']:
        keyboard.append([InlineKeyboardButton("🔗 Add Group Link", callback_data=f"add_group_link_{order_id}")])
    
    if order_dict['transaction_group_link'] and order_dict['order_status'] != 'completed':
        keyboard.append([InlineKeyboardButton("✅ Mark as Completed", callback_data=f"mark_completed_{order_id}")])
    
    keyboard.append([InlineKeyboardButton("📦 Back to Orders", callback_data="admin_orders_panel")])
    
    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU


def customer_my_orders(update, context):
    """Show customer their orders."""
    query = update.callback_query if update.callback_query else None
    user_id = update.effective_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, product_id, platform, total_price, escrow_fee,
               order_status, created_at
        FROM orders
        WHERE customer_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        text = "🛒 <b>My Orders</b>\n\n📭 You haven't placed any orders yet.\n\nUse /dashboard to browse listings!"
        keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")]]
        
        if query:
            query.answer()
            query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return CUSTOMER_MENU

    text = "🛒 <b>My Orders</b>\n\n"
    keyboard = []

    for order in orders:
        order_id, order_num, product_id, platform, price, fee, status, created = order
        status_emoji = {"pending": "⏳", "group_link_set": "🔗", "completed": "✅"}.get(status, "❓")
        
        text += (
            f"{status_emoji} <b>{order_num}</b> | {platform} | ${price:,.0f}\n"
        )
        
        keyboard.append([InlineKeyboardButton(f"View {order_num}", callback_data=f"customer_order_{order_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back_to_customer_start")])
    
    if query:
        query.answer()
        query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    return CUSTOMER_MENU


def customer_view_order_detail(update, context):
    """Show customer their order details with COMPLETE info including group link."""
    query = update.callback_query
    order_id = int(query.data.replace("customer_order_", ""))
    user_id = update.effective_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Fetch complete order details
    cursor.execute("""
        SELECT id, order_number, product_id, platform, total_price, escrow_fee,
               order_status, payment_status, payment_confirmed_at, completed_at,
               seller_id, customer_username, created_at, transaction_group_link
        FROM orders 
        WHERE id = ? AND customer_id = ?
    """, (order_id, user_id))
    order = cursor.fetchone()
    
    if not order:
        query.answer("Order not found.", show_alert=True)
        return CUSTOMER_MENU
    
    (order_id, order_num, product_id, platform, total_price, escrow_fee,
     order_status, payment_status, payment_confirmed_at, completed_at,
     seller_id, buyer_username, created_at, group_link) = order
    
    # Fetch listing details
    cursor.execute("""
        SELECT account_type, subscribers, views, niche, monetization, seller_contact
        FROM listings
        WHERE listing_id = ?
    """, (product_id,))
    listing = cursor.fetchone()
    
    account_type = ""
    subscribers = "N/A"
    views = "N/A"
    niche = "N/A"
    monetization = "N/A"
    
    if listing:
        account_type, subs, views_num, niche, monetization, _ = listing
        subscribers = format_number(subs) if subs else "N/A"
        views = format_number(views_num) if views_num else "N/A"
    
    # Fetch seller info
    seller_username = "Unknown Seller"
    if seller_id:
        cursor.execute(
            "SELECT customer_username FROM customer_listings WHERE customer_id = ? ORDER BY created_at DESC LIMIT 1",
            (seller_id,)
        )
        seller_result = cursor.fetchone()
        if seller_result and seller_result[0]:
            seller_username = seller_result[0]
    
    conn.close()

    # Build status indicators
    status_emoji = {"pending": "⏳", "group_link_set": "🔗", "completed": "✅"}.get(order_status, "❓")
    payment_emoji = "✅" if payment_status == "confirmed" else "⏳"
    
    # Build comprehensive order details
    text = (
        f"{status_emoji} <b>ORDER {order_num}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        f"<b>📋 ACCOUNT DETAILS</b>\n"
        f"• 🆔 <b>Product ID:</b> <code>{product_id}</code>\n"
        f"• 📱 <b>Platform:</b> {platform}\n"
        f"• 👤 <b>Account Type:</b> {account_type}\n"
        f"• 🗃️ <b>Niche:</b> {niche}\n"
        f"• 👥 <b>Subscribers:</b> {subscribers}\n"
        f"• 👀 <b>Views:</b> {views}\n"
        f"• 💲 <b>Monetization:</b> {monetization}\n\n"
        
        f"<b>💰 PRICING & ESCROW</b>\n"
        f"• 💵 <b>Account Price:</b> ${total_price:,.2f}\n"
        f"• 🛡️ <b>Escrow Fee (5%):</b> ${escrow_fee:.2f}\n\n"
        
        f"<b>👥 PARTIES</b>\n"
        f"• 🛍️ <b>You (Buyer):</b> @{buyer_username}\n"
        f"• 🎯 <b>Seller:</b> @{seller_username}\n"
        f"• 👨‍⚖️ <b>Escrow Agent:</b> @smyards\n\n"
        
        f"<b>📊 ORDER STATUS</b>\n"
        f"• {payment_emoji} <b>Payment:</b> {'Confirmed ✅' if payment_status == 'confirmed' else 'Pending ⏳'}\n"
        f"• {status_emoji} <b>Order:</b> {order_status.replace('_', ' ').title()}\n\n"
        
        f"<b>📅 TIMELINE</b>\n"
        f"• 📝 <b>Created:</b> {created_at}\n"
    )
    
    if payment_confirmed_at:
        text += f"• ✅ <b>Payment Confirmed:</b> {payment_confirmed_at}\n"
    
    if completed_at:
        text += f"• 🎉 <b>Completed:</b> {completed_at}\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━"
    
    # Build keyboard
    keyboard = []
    
    # Add group link button if it exists
    if group_link and group_link.startswith('https://t.me/'):
        text += (
            f"\n\n🔗 <b>DEAL GROUP LINK</b>\n"
            f"Join the secure group where you, the seller, and escrow agent complete the transaction."
        )
        keyboard.append([
            InlineKeyboardButton("🔗 JOIN DEAL GROUP", url=group_link),
        ])
    elif order_status == "pending":
        text += f"\n\n⏳ <b>Waiting for admin to create the deal group...</b>"
    
    keyboard.append([InlineKeyboardButton("🔙 Back to My Orders", callback_data="customer_my_orders")])
    
    query.answer()
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return CUSTOMER_MENU

def user_profile_feedback(update, context):
    """User Profile & Feedback page - PLACEHOLDER"""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or str(user_id)
    
    # TODO: Fetch user stats from database
    text = (
        f"👤 <b>Your Profile</b>\n\n"
        f"👤 <b>Username:</b> @{username}\n"
        f"🌟 <b>Rating:</b> 4.8/5.0 (12 reviews)\n"
        f"🏆 <b>Badges:</b> Trusted Seller, Quick Responder\n"
        f"📊 <b>Transaction Count:</b> 24\n\n"
        f"<b>Reviews Left By Others:</b>\n"
        f"(To be implemented)\n\n"
        f"<b>Your Reviews:</b>\n"
        f"(To be implemented)"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="open_dashboard")]]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return CUSTOMER_MENU	

def notify_admin_on_order_created(order_number, product_id, price, escrow_fee, buyer_username, seller_username, order_id, context):
    """Notify admin when order created - NO GROUP LINK BUTTON YET (only after payment confirmed)."""
    try:
        # NO "Add Group Link" button here - only show when payment confirmed
        text = (
            f"🛍 <b>NEW ORDER CREATED!</b>\n\n"
            f"📦 <b>Product:</b> <code>{product_id}</code>\n"
            f"🆔 <b>Order:</b> <code>{order_number}</code>\n"
            f"💰 <b>Account Price:</b> ${price:,.2f}\n"
            f"🛡️ <b>Escrow Fee:</b> ${escrow_fee:.2f}\n"
            f"👤 <b>Buyer:</b> @{buyer_username}\n"
            f"👤 <b>Seller:</b> @{seller_username}\n\n"
            f"⏳ <b>Status:</b> Waiting for buyer to complete escrow fee payment...\n\n"
            f"The 'Add Group Link' button will appear once payment is confirmed."
        )
        
        keyboard = []  # EMPTY - no buttons until payment confirmed
        
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"✅ Admin notified of new order {order_number} (waiting for payment)")
    except Exception as e:
        logger.error(f"Error notifying admin of new order: {e}")


def notify_seller_on_payment(seller_id, order_number, product_id, price, escrow_fee, buyer_username, context):
    """Notify seller when buyer confirms escrow payment."""
    try:
        text = (
            f"🛍 <b>NEW ORDER ON YOUR LISTING!</b>\n\n"
            f"📦 <b>Product:</b> <code>{product_id}</code>\n"
            f"🆔 <b>Order:</b> <code>{order_number}</code>\n"
            f"💰 <b>Price:</b> ${price:,.2f}\n"
            f"🛡️ <b>Escrow Fee:</b> ${escrow_fee:.2f}\n"
            f"👤 <b>Buyer:</b> @{buyer_username}\n\n"
            f"⏳ <b>Status:</b> Waiting for admin to set up the deal group...\n\n"
            f"You'll receive the group link shortly!"
        )
        context.bot.send_message(
            chat_id=seller_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        logger.info(f"Seller {seller_id} notified for order {order_number}")
    except Exception as e:
        logger.error(f"Error notifying seller: {e}")
    
def admin_add_group_link(update, context):
    """Admin clicked 'Add Group Link' - prompt for the invite URL"""
    query = update.callback_query
    query.answer()
    
    order_id = int(query.data.replace("add_group_link_", ""))
    
    # Store with order_id AND query to get order_number for reference
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT order_number FROM orders WHERE id = ?", (order_id,))
    order_result = cursor.fetchone()
    conn.close()
    
    if not order_result:
        query.edit_message_text("❌ Order not found in database. This is unusual - please contact support.")
        return MAIN_MENU
    
    order_number = order_result[0]
    
    # Store BOTH for reference
    context.user_data['pending_group_link_order_id'] = order_id
    context.user_data['pending_group_link_order_number'] = order_number
    
    query.edit_message_text(
        "🔗 <b>Add Group Link</b>\n\n"
        f"<b>Order:</b> <code>{order_number}</code>\n\n"
        "Send the Telegram group invite link.\n\n"
        "Format: <code>https://t.me/+abcdef123xyz</code>\n\n"
        "Type 'cancel' to abort.",
        parse_mode=ParseMode.HTML
    )
    return ADMIN_ADD_GROUP_LINK

def admin_handle_group_link_input(update, context):
    """Handle the group link text input from admin"""
    group_link = update.message.text.strip()
    
    if group_link.lower() == 'cancel':
        update.message.reply_text("❌ Group link addition cancelled.")
        context.user_data.pop('pending_group_link_order_id', None)
        context.user_data.pop('pending_group_link_order_number', None)
        return MAIN_MENU
    
    if not group_link.startswith('https://t.me/'):
        update.message.reply_text(
            "❌ Invalid format. Please provide a valid Telegram invite link.\n\n"
            "Example: https://t.me/+abcdef123xyz\n\n"
            "Send again or type 'cancel':"
        )
        return ADMIN_ADD_GROUP_LINK
    
    order_id = context.user_data.get('pending_group_link_order_id')
    order_number = context.user_data.get('pending_group_link_order_number')
    
    if not order_id or not order_number:
        update.message.reply_text("❌ Order info expired. Please click 'Add Group Link' again.")
        return MAIN_MENU
    
    try:
        # Save group link to order
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET transaction_group_link = ?, order_status = 'group_link_set' WHERE id = ?",
            (group_link, order_id)
        )
        conn.commit()
        
        # Get order details to notify parties
        cursor.execute("""
            SELECT order_number, product_id, customer_id, customer_username, seller_id
            FROM orders WHERE id = ?
        """, (order_id,))
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            update.message.reply_text(f"❌ Order {order_number} not found after save. This is unusual.")
            return MAIN_MENU
        
        order_num, product_id, buyer_id, buyer_username, seller_id = order
        
        # Notify buyer
        buyer_text = (
            f"🎉 <b>Your Deal Group is Ready!</b>\n\n"
            f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
            f"📦 <b>Product:</b> <code>{product_id}</code>\n\n"
            f"Join the deal group:\n{group_link}\n\n"
            f"The seller and admin are waiting for you!"
        )
        try:
            context.bot.send_message(chat_id=buyer_id, text=buyer_text, parse_mode=ParseMode.HTML)
            logger.info(f"✅ Buyer {buyer_id} notified of group link for order {order_num}")
        except Exception as e:
            logger.error(f"❌ Error notifying buyer: {e}")
            update.message.reply_text(f"⚠️ Could not notify buyer {buyer_id}: {e}")
        
        # Notify seller
        if seller_id and seller_id != OWNER_ID:
            seller_text = (
                f"🛍 <b>Deal Group Ready!</b>\n\n"
                f"📦 <b>Product:</b> <code>{product_id}</code>\n"
                f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
                f"👤 <b>Buyer:</b> @{buyer_username}\n\n"
                f"Join the deal group here:\n{group_link}\n\n"
                f"Complete the transaction there!"
            )
            try:
                context.bot.send_message(chat_id=seller_id, text=seller_text, parse_mode=ParseMode.HTML)
                logger.info(f"✅ Seller {seller_id} notified of group link for order {order_num}")
            except Exception as e:
                logger.error(f"❌ Error notifying seller {seller_id}: {e}")
                update.message.reply_text(f"⚠️ Could not notify seller {seller_id}: {e}")
        else:
            logger.warning(f"No valid seller_id for order {order_num}: {seller_id}")
        
        # Confirm to admin
        update.message.reply_text(
            f"✅ <b>Group link saved!</b>\n\n"
            f"📦 <b>Order:</b> <code>{order_num}</code>\n"
            f"🔗 <b>Link:</b> {group_link}\n\n"
            f"Both parties have been notified.",
            parse_mode=ParseMode.HTML
        )
        
        # Clean up context
        context.user_data.pop('pending_group_link_order_id', None)
        context.user_data.pop('pending_group_link_order_number', None)
        
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Error saving group link: {e}", exc_info=True)
        update.message.reply_text(f"❌ Error saving group link: {str(e)[:100]}\n\nPlease try again.")
        return ADMIN_ADD_GROUP_LINK

def admin_handle_group_link_standalone(update, context):
    """Handle group link input from admin outside ConversationHandler."""
    if update.effective_user.id != OWNER_ID:
        return
    
    # Only handle if we're expecting a group link
    if 'pending_group_link_order_id' not in context.user_data:
        return
    
    group_link = update.message.text.strip()
    
    if group_link.lower() == 'cancel':
        context.user_data.pop('pending_group_link_order_id', None)
        update.message.reply_text("❌ Group link addition cancelled.")
        return
    
    if not group_link.startswith('https://t.me/'):
        update.message.reply_text(
            "❌ Invalid format. Please send a valid Telegram invite link.\n"
            "Example: https://t.me/+abcdef123xyz\n\n"
            "Type 'cancel' to abort."
        )
        return
    
    order_id = context.user_data.get('pending_group_link_order_id')
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET transaction_group_link = ?, order_status = 'group_link_set' WHERE id = ?",
            (group_link, order_id)
        )
        conn.commit()
        
        cursor.execute("""
            SELECT order_number, product_id, customer_id, customer_username, seller_id
            FROM orders WHERE id = ?
        """, (order_id,))
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            update.message.reply_text("❌ Order not found.")
            return
        
        order_num, product_id, buyer_id, buyer_username, seller_id = order
        
        # Notify buyer
        try:
            context.bot.send_message(
                chat_id=int(buyer_id),
                text=(
                    f"🎉 <b>Your Deal Group is Ready!</b>\n\n"
                    f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
                    f"📦 <b>Product:</b> <code>{product_id}</code>\n\n"
                    f"Join the deal group here:\n{group_link}\n\n"
                    f"The seller and admin are waiting for you!"
                ),
                parse_mode=ParseMode.HTML
            )
            update.message.reply_text("✅ Buyer notified.")
        except Exception as e:
            logger.error(f"Error notifying buyer: {e}")
            update.message.reply_text(f"⚠️ Could not notify buyer: {e}")
        
        # Notify seller
        if seller_id:
            try:
                context.bot.send_message(
                    chat_id=int(seller_id),
                    text=(
                        f"🛍 <b>Deal Group Ready!</b>\n\n"
                        f"📦 <b>Product:</b> <code>{product_id}</code>\n"
                        f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
                        f"👤 <b>Buyer:</b> @{buyer_username}\n\n"
                        f"Join the deal group here:\n{group_link}\n\n"
                        f"Complete the transaction there!"
                    ),
                    parse_mode=ParseMode.HTML
                )
                update.message.reply_text("✅ Seller notified.")
            except Exception as e:
                logger.error(f"Error notifying seller: {e}")
                update.message.reply_text(f"⚠️ Could not notify seller (seller_id: {seller_id}): {e}")
        else:
            update.message.reply_text(f"⚠️ No seller_id found for this order.")
        
        context.user_data.pop('pending_group_link_order_id', None)
        update.message.reply_text(
            f"✅ <b>Group link saved!</b>\n\n"
            f"Order: <code>{order_num}</code>\n"
            f"Link: {group_link}",
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Error saving group link: {e}", exc_info=True)
        update.message.reply_text(f"❌ Error saving group link: {e}")


def admin_add_group_link(update, context):
    """Admin clicked 'Add Group Link' button."""
    query = update.callback_query
    order_id = int(query.data.replace("add_group_link_", ""))
    context.user_data['pending_group_link_order_id'] = order_id
    
    query.answer()
    query.edit_message_text(
        "🔗 <b>Add Group Link</b>\n\n"
        "Create a Telegram group, add the bot as admin, then send the invite link here.\n\n"
        "Format: <code>https://t.me/+abcdef123xyz</code>\n\n"
        "Type 'cancel' to abort.",
        parse_mode=ParseMode.HTML
    )		
		
def admin_mark_order_completed(update, context):
    """Admin marked an order as completed"""
    query = update.callback_query
    order_id = int(query.data.replace("mark_completed_", ""))
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT order_number, customer_id, customer_username, seller_id, product_id, 
                   platform, total_price, escrow_fee
            FROM orders WHERE id = ?
        """, (order_id,))
        order = cursor.fetchone()
        
        if not order:
            query.answer("Order not found.", show_alert=True)
            return MAIN_MENU
        
        order_num, buyer_id, buyer_username, seller_id, product_id, platform, price, fee = order
        
        # Update order status
        cursor.execute("""
            UPDATE orders 
            SET order_status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order_id,))
        conn.commit()
        conn.close()
        
        # Notify buyer
        buyer_text = (
            f"🎉 <b>Deal Completed!</b>\n\n"
            f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
            f"✅ Your transaction has been successfully completed.\n\n"
            f"Please share your feedback:\n"
            f"[⭐ Review Seller] [⭐ Review SMYARDS]\n\n"
            f"<i>(Review buttons coming in Stage 3)</i>"
        )
        try:
            context.bot.send_message(chat_id=buyer_id, text=buyer_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error notifying buyer of completion: {e}")
        
        # Notify seller
        seller_text = (
            f"🎉 <b>Deal Completed!</b>\n\n"
            f"🆔 <b>Order:</b> <code>{order_num}</code>\n"
            f"✅ Your transaction has been successfully completed.\n\n"
            f"💰 <b>Amount Released:</b> ${price:,.2f}\n\n"
            f"Please share your feedback:\n"
            f"[⭐ Review Buyer] [⭐ Review SMYARDS]\n\n"
            f"<i>(Review buttons coming in Stage 3)</i>"
        )
        try:
            context.bot.send_message(chat_id=seller_id, text=seller_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error notifying seller of completion: {e}")
        
        query.answer("✅ Order marked as completed!", show_alert=True)
        return admin_view_order_detail(update, context)
        
    except Exception as e:
        logger.error(f"Error marking order completed: {e}", exc_info=True)
        query.answer("❌ Error marking order as completed", show_alert=True)
        return MAIN_MENU		





# ===== CORE BOT FUNCTIONS =====
def start(update, context):
    """Simplified /start - just show dashboard button"""
    context.user_data.clear()
    user_id = update.effective_user.id

    # If admin, tell them to use /admin
    if user_id == OWNER_ID or is_admin(user_id):
        update.message.reply_text(
            "👋 Welcome back, Admin!\n\n"
            "Use /admin to open your admin dashboard."
        )
        return ConversationHandler.END

    # Everyone else: just one button
    user_first = update.effective_user.first_name or "there"
    text = f"👋 Welcome, {user_first}!\n\nOpen your dashboard to get started."
    
    keyboard = [[InlineKeyboardButton("🏠 Open My Dashboard", callback_data="open_dashboard")]]
    
    update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END

def dashboard(update, context):
    """Customer dashboard entry point — /dashboard command"""
    return customer_start(update, context)


def handle_deep_link_buy(update, context, product_id):
    """Handles deep link buy — shows account details and escrow fee, waits for confirmation before generating invoice."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM listings WHERE listing_id = ? AND status_flag = 'published'", (product_id,))
        listing = cursor.fetchone()
        conn.close()

        if not listing:
            update.message.reply_text(
                f"❌ <b>Product Not Found</b>\n\n"
                f"Product <code>{product_id}</code> is not available or has already been sold.\n\n"
                f"Use /dashboard to browse other available listings.",
                parse_mode=ParseMode.HTML
            )
            return

        price = float(listing["price"])
        escrow_fee = calculate_escrow_fee(price)
        platform = listing["platform"]
        order_number = generate_order_number(platform)
        
        subs_fmt = format_number(listing['subscribers'])
        views_fmt = format_number(listing['views'])
        price_fmt = f"${price:,.0f}"
        fee_fmt = f"${escrow_fee:.2f}"

        # Store order info
        context.user_data['pending_order'] = {
            'listing_id': product_id,
            'platform': platform,
            'price': price,
            'escrow_fee': escrow_fee,
            'order_number': order_number
        }

        text = (
            f"🎯 <b>{listing['platform']} ACCOUNT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>📋 BASIC INFO</b>\n"
            f"• 🆔 <b>Product ID:</b> <code>{product_id}</code>\n"
            f"• 👤 <b>Type:</b> {listing['account_type']}\n"
            f"• 🌍 <b>Region:</b> {listing['region'] or 'N/A'}\n\n"
            f"<b>📊 STATISTICS</b>\n"
            f"• 👥 <b>Subscribers:</b> {subs_fmt}\n"
            f"• 👀 <b>Views:</b> {views_fmt}\n"
            f"• ✅ <b>Status:</b> {listing['status'] or 'N/A'}\n\n"
            f"<b>⚙️ FEATURES</b>\n"
            f"• 🗃️ <b>Niche:</b> {listing['niche'] or 'Mixed'}\n"
            f"• 🔧 <b>Features:</b> {listing['features'] or 'N/A'}\n"
            f"• 💲 <b>Monetization:</b> {listing['monetization'] or 'N/A'}\n\n"
            f"<b>💰 PRICING & ESCROW</b>\n"
            f"• 💵 <b>Account Price:</b> {price_fmt}\n"
            f"• 🔐 <b>Escrow Fee (5%, min $5):</b> <b>{fee_fmt} USDT</b>\n\n"
            f"<b>🛡️ How Escrow Works:</b>\n"
            f"1. You pay the escrow fee\n"
            f"2. Admin creates a private group with you, seller, and themselves\n"
            f"3. Seller transfers the account to you\n"
            f"4. You confirm receipt of the account\n"
            f"5. Admin releases funds to the seller\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        keyboard = [
            [InlineKeyboardButton(f"💳 Pay Escrow Fee ({fee_fmt})", callback_data=f"confirm_pay_escrow_{product_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_customer_start")]
        ]
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Error in handle_deep_link_buy: {e}", exc_info=True)
        update.message.reply_text("❌ An error occurred. Please contact @smyards for assistance.")
		

def handle_deep_link_sell(update, context):
    """Deep link sell — goes straight to the sell info screen, same as clicking Sell a Channel"""
    try:
        text = (
            "💰 <b>SELL YOUR ACCOUNT</b>\n\n"
            "✅ <b>Why Sell With SMYARDS:</b>\n"
            "• Reach thousands of serious buyers\n"
            "• Secure escrow protection\n"
            "• Get paid quickly &amp; safely\n"
            "• Professional listing presentation\n\n"
            "📋 <b>How It Works:</b>\n"
            "1. Submit your account details\n"
            "2. Our team reviews &amp; approves within 2-12 hours\n"
            "3. Your account gets listed on @smyard\n"
            "4. Buyers contact you via our system\n"
            "5. We handle secure payment via escrow\n"
            "6. You get paid after successful transfer\n\n"
            "⏰ <b>Approval Time:</b> 2-12 hours\n"
            "💰 <b>Commission:</b> 5% escrow fee (paid by buyer)\n"
            "🛡️ <b>Security:</b> 100% protected transactions\n\n"
            "Ready to list your account?"
        )
        keyboard = [
            [InlineKeyboardButton("📝 List Your Account Now", callback_data="seller_list_account")],
        ]
        update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        return SELLER_INFO
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in deep link sell: {str(e)}")
    
    
def handle_direct_message(update, context):
    """Handle direct text inputs outside of specific conversational states"""
    if update.effective_chat.type != "private" or not update.message or not update.message.text:
        return
        
    message_text = update.message.text.strip()
    
    if '-' in message_text and len(message_text) <= 10:
        product_id = message_text.upper()
        valid_prefixes = ('YT-', 'IG-', 'FB-', 'TT-')
        if product_id.startswith(valid_prefixes):
            update.message.reply_text(
                f"👋 I see you're interested in product <code>{product_id}</code>!\n\nUse /dashboard to open your dashboard and place an order.",
                parse_mode=ParseMode.HTML
            )
            return
            
    update.message.reply_text(
        "👋 <b>Welcome to SMYARDS Marketplace!</b>\n\n"
        "I can help you:\n"
        "🛍 <b>Buy accounts</b> safely with escrow protection\n"
        "💰 <b>Sell your accounts</b> to verified buyers\n\n"
        "<b>Commands:</b>\n"
        "• /start — Welcome &amp; platform intro\n"
        "• /dashboard — Open your dashboard\n\n"
        "📢 Visit our channel: @smyard\n"
        "📞 Support: @smyards",
        parse_mode=ParseMode.HTML
    )

def error_handler(update, context):
    """Log errors cleanly without redundant try/except blocks"""
    logger.error(f"Update {update} caused error:", exc_info=context.error)
    
    try:
        if update and update.effective_message and update.effective_chat.type == "private":
            update.effective_message.reply_text("❌ An unexpected error occurred.\nPlease try again or contact @smyards for support.")
    except Exception as e:
        logger.error(f"Error notifying user in error handler: {e}")

        

def admin_simulate_payment(update, context):
    """TESTING ONLY — manually mark an order as paid to test the post-payment flow."""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        update.message.reply_text(
            "Usage: /simulate_payment ORDER_NUMBER\n"
            "Example: /simulate_payment YT#0007"
        )
        return
    
    order_number = context.args[0]
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders 
        SET payment_status = 'confirmed', 
            payment_confirmed_at = CURRENT_TIMESTAMP
        WHERE order_number = ?
    """, (order_number,))
    conn.commit()
    
    cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
    order = cursor.fetchone()
    cursor.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    
    if not order:
        update.message.reply_text(f"❌ Order {order_number} not found.")
        return
    
    order_dict = dict(zip(columns, order))
    order_id = order_dict.get('id')
    seller_id = order_dict.get('seller_id')
    product_id = order_dict.get('product_id')
    buyer_username = order_dict.get('customer_username', 'N/A')
    price = order_dict.get('total_price', 0)
    escrow_fee = order_dict.get('escrow_fee', 0)

    # Send admin notification WITH the Add Group Link button
    keyboard = [[InlineKeyboardButton("🔗 Add Group Link", callback_data=f"add_group_link_{order_id}")]]
    
    update.message.reply_text(
        f"✅ <b>PAYMENT CONFIRMED (Simulated)</b>\n\n"
        f"🆔 Order: <code>{order_number}</code>\n"
        f"📦 Product: <code>{product_id}</code>\n"
        f"👤 Buyer: @{buyer_username}\n"
        f"💵 Escrow Fee: ${escrow_fee:.2f}\n\n"
        f"➡️ Click below to add the group link:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

    # Notify seller
    if seller_id:
        try:
            context.bot.send_message(
                chat_id=int(seller_id),
                text=(
                    f"🛍 <b>NEW ORDER ON YOUR LISTING!</b>\n\n"
                    f"📦 <b>Product:</b> <code>{product_id}</code>\n"
                    f"🆔 <b>Order:</b> <code>{order_number}</code>\n"
                    f"💰 <b>Price:</b> ${price:,.2f}\n"
                    f"🛡️ <b>Escrow Fee:</b> ${escrow_fee:.2f}\n"
                    f"👤 <b>Buyer:</b> @{buyer_username}\n\n"
                    f"⏳ Waiting for admin to set up the deal group...\n\n"
                    f"You'll receive the group link shortly!"
                ),
                parse_mode=ParseMode.HTML
            )
            update.message.reply_text("✅ Seller also notified.")
        except Exception as e:
            update.message.reply_text(
                f"⚠️ Could not notify seller.\n"
                f"seller_id in DB: {seller_id}\n"
                f"Error: {e}"
            )
    else:
        update.message.reply_text(
            f"⚠️ No seller_id found for this order.\n"
            f"This is likely an admin-created listing.\n"
            f"seller_id in DB: {seller_id}"
        )

def admin_manage_listing(update, context):
    """Admin manage single listing with bump/delete/mark sold options."""
    query = update.callback_query
    query.answer()
    
    listing_id = int(query.data.replace("admin_manage_listing_", ""))
    context.user_data['admin_managing_listing_id'] = listing_id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id, platform, price, status_flag FROM listings WHERE id = ?", (listing_id,))
    listing = cursor.fetchone()
    conn.close()
    
    if not listing:
        query.edit_message_text("❌ Listing not found.")
        return MAIN_MENU
    
    l_id, platform, price, status = listing
    
    text = (
        f"⚙️ <b>Manage Listing</b>\n"
        f"🆔 {l_id} | {platform} | ${price:,.0f}\n"
        f"Status: {status.upper()}\n\n"
        f"Choose action:"
    )
    
    keyboard = [
        [InlineKeyboardButton("⚡ Bump to Top", callback_data=f"admin_bump_listing_{listing_id}")],
        [InlineKeyboardButton("💰 Mark as Sold", callback_data=f"admin_mark_sold_listing_{listing_id}")],
        [InlineKeyboardButton("🗑️ Delete Listing", callback_data=f"admin_delete_listing_{listing_id}")],
        [InlineKeyboardButton("🔙 Back to Listings", callback_data="admin_view_listings_reset")],
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# admin_delete_listing - delete with confirmation
def admin_delete_listing(update, context):
    """Delete a listing after confirmation."""
    query = update.callback_query
    query.answer()
    
    listing_id = int(query.data.replace("admin_delete_listing_", ""))
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT listing_id FROM listings WHERE id = ?", (listing_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        query.edit_message_text("❌ Listing not found.")
        return MAIN_MENU
    
    l_id = result[0]
    context.user_data['listing_to_delete'] = listing_id
    
    text = f"⚠️ <b>CONFIRM DELETE</b>\n\nPermanently delete listing <code>{l_id}</code>?\n\nThis cannot be undone!"
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data="confirm_delete_listing")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_view_listings_reset")],
    ]
    
    query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return MAIN_MENU

# confirm_delete_listing - executes deletion
def confirm_delete_listing(update, context):
    """Execute listing deletion."""
    query = update.callback_query
    query.answer()
    
    listing_id = context.user_data.pop('listing_to_delete', None)
    
    if not listing_id:
        query.edit_message_text("❌ Error: Listing ID not found.")
        return MAIN_MENU
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT listing_id FROM listings WHERE id = ?", (listing_id,))
        result = cursor.fetchone()
        
        if result:
            l_id = result[0]
            cursor.execute("DELETE FROM listings WHERE id = ?", (listing_id,))
            conn.commit()
            query.edit_message_text(f"✅ Listing <code>{l_id}</code> deleted from database.", parse_mode=ParseMode.HTML)
        else:
            query.edit_message_text("❌ Listing not found.")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error deleting listing: {e}")
        query.edit_message_text(f"❌ Error: {str(e)[:100]}")
    
    return MAIN_MENU

# admin_view_listings_reset - reset filters
def admin_view_listings_reset(update, context):
    """Reset platform filter and go back to main admin listings view."""
    query = update.callback_query
    query.answer()
    
    context.user_data.pop('admin_platform_filter', None)
    context.user_data['listings_page'] = 0
    
    return admin_view_listings(update, context)

		


		
		
def debug_check_order(update, context):
    """Admin command to check order details - /check_order ORDER_NUMBER"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        update.message.reply_text(
            "Usage: /check_order ORDER_NUMBER\n"
            "Example: /check_order YT#0001\n"
            "This shows order details including seller_id"
        )
        return
    
    order_number = context.args[0]
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, order_number, product_id, customer_id, customer_username, 
               seller_id, payment_status, order_status, created_at, transaction_group_link
        FROM orders WHERE order_number = ?
    """, (order_number,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        update.message.reply_text(f"❌ Order {order_number} not found")
        return
    
    order_id, ord_num, product_id, customer_id, customer_username, seller_id, payment_status, order_status, created_at, group_link = order
    
    text = (
        f"🔍 <b>ORDER DEBUG INFO</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Order Details:</b>\n"
        f"• ID: <code>{order_id}</code>\n"
        f"• Order #: <code>{ord_num}</code>\n"
        f"• Product: <code>{product_id}</code>\n"
        f"• Payment: {payment_status}\n"
        f"• Status: {order_status}\n"
        f"• Created: {created_at}\n\n"
        f"<b>Buyer:</b>\n"
        f"• ID: <code>{customer_id}</code>\n"
        f"• Username: @{customer_username}\n\n"
        f"<b>SELLER (THIS IS KEY!):</b>\n"
        f"• seller_id: <code>{seller_id}</code> {'✅ VALID' if seller_id else '❌ NULL!'}\n"
        f"• Is Admin? {seller_id == OWNER_ID}\n\n"
        f"<b>Group Link:</b>\n"
        f"• Set: {'✅ Yes' if group_link else '❌ No'}\n"
        f"• Link: {group_link if group_link else 'None'}\n"
    )

	
    update.message.reply_text(text, parse_mode=ParseMode.HTML)

def admin_check_seller_id(update, context):
    """Admin command to diagnose seller notification issues"""
    if update.effective_user.id != OWNER_ID:
        return
    
    if not context.args:
        update.message.reply_text(
            "Usage: /check_seller ORDER_NUMBER\n"
            "Shows if seller_id is set and what it is\n\n"
            "Example: /check_seller YT#0001"
        )
        return
    
    order_number = context.args[0]
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check orders table
    cursor.execute("""
        SELECT id, product_id, seller_id, customer_id, payment_status
        FROM orders WHERE order_number = ?
    """, (order_number,))
    order = cursor.fetchone()
    
    if not order:
        update.message.reply_text(f"❌ Order {order_number} not found")
        conn.close()
        return
    
    order_id, product_id, seller_id, buyer_id, payment_status = order
    
    # Check listing
    cursor.execute("SELECT created_by FROM listings WHERE listing_id = ?", (product_id,))
    listing = cursor.fetchone()
    listing_created_by = listing[0] if listing else None
    
    conn.close()
    
    text = (
        f"🔍 <b>SELLER DIAGNOSTIC</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>Order:</b> {order_number}\n"
        f"<b>Product:</b> {product_id}\n"
        f"<b>Payment Status:</b> {payment_status}\n\n"
        f"<b>CRITICAL - Seller ID:</b>\n"
        f"• In orders table: <code>{seller_id}</code>\n"
        f"• In listings.created_by: <code>{listing_created_by}</code>\n"
        f"• Match? {'✅ YES' if seller_id == listing_created_by else '❌ NO'}\n"
        f"• Is NULL? {'❌ YES - PROBLEM!' if not seller_id else '✅ NO'}\n"
        f"• Is Admin (OWNER_ID={OWNER_ID})? {'⚠️ YES - Will skip' if seller_id == OWNER_ID else '✅ NO'}\n\n"
        f"<b>Buyer ID:</b> {buyer_id}\n\n"
    )
    
    if not seller_id:
        text += "❌ <b>PROBLEM FOUND:</b> seller_id is NULL!\n"
        text += "This is why seller is not notified.\n"
        text += "Check if listing {product_id} has created_by set."
    elif seller_id == OWNER_ID:
        text += "⚠️ <b>INFO:</b> This is admin-created listing.\n"
        text += "Seller notifications skipped for admin listings (expected)."
    else:
        text += f"✅ seller_id={seller_id} looks valid.\n"
        text += f"If seller still not notified, check:\n"
        text += f"1. Is Telegram ID {seller_id} correct?\n"
        text += f"2. Can bot message that Telegram ID?\n"
        text += f"3. Check bot logs for error messages."
    
    update.message.reply_text(text, parse_mode=ParseMode.HTML)

	
# ===== MAIN EXECUTION =====
def main():
    init_database()
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # 1. STANDALONE CALLBACKS
    dispatcher.add_handler(CallbackQueryHandler(approve_customer_listing, pattern='^approve_listing_'))
    dispatcher.add_handler(CallbackQueryHandler(reject_customer_listing, pattern='^reject_listing_'))
    dispatcher.add_handler(CallbackQueryHandler(verify_payment, pattern='^verify_payment_'))
    dispatcher.add_handler(CommandHandler('simulate_payment', admin_simulate_payment))
	# Standalone handler for group link button (works outside ConversationHandler)
    dispatcher.add_handler(CallbackQueryHandler(admin_add_group_link, pattern='^add_group_link_'))
	# Standalone handler for group link text input
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.user(OWNER_ID),
        admin_handle_group_link_standalone
    ))
    dispatcher.add_handler(CommandHandler('check_order', debug_check_order))
    dispatcher.add_handler(CommandHandler('check_seller', admin_check_seller_id))
	
    # 2. ADMIN CONVERSATION
    admin_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('admin', admin_start),
        ],
        states={
            MAIN_MENU: [CallbackQueryHandler(admin_button_callback)],
            CREATE_PLATFORM: [CallbackQueryHandler(admin_button_callback)],
            CREATE_TYPE: [CallbackQueryHandler(admin_button_callback)],
            CREATE_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            CREATE_PRICE: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            CREATE_SELLER_CONTACT: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            SCREENSHOT_ASK: [CallbackQueryHandler(admin_button_callback)],
            SCREENSHOT_UPLOAD: [
                MessageHandler(Filters.photo, admin_button_callback),
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            CREATE_CONFIRM: [CallbackQueryHandler(admin_button_callback)],
            MARK_SOLD: [CallbackQueryHandler(admin_button_callback)],
            ENTER_PRODUCT_ID: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            ENTER_TXID: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            ENTER_PAYMENT_METHOD: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            ENTER_ORDER_NUMBER: [
                MessageHandler(Filters.text & ~Filters.command, admin_button_callback),
                CallbackQueryHandler(admin_button_callback)
            ],
            ADMIN_RELIST_MENU: [CallbackQueryHandler(admin_button_callback)],
            ADMIN_ORDERS_PANEL: [CallbackQueryHandler(admin_button_callback)],
            ADMIN_ORDER_DETAIL: [CallbackQueryHandler(admin_button_callback)],
            ADMIN_ADD_GROUP_LINK: [
                MessageHandler(Filters.text & ~Filters.command, admin_handle_group_link_input),
                CallbackQueryHandler(admin_button_callback)
            ],
            ADMIN_MARK_SOLD: [
                MessageHandler(Filters.text & ~Filters.command, route_admin_mark_sold_flow),
                CallbackQueryHandler(admin_button_callback)
            ],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True,
        name="admin_conversation"
    )
    dispatcher.add_handler(admin_conv_handler)
    
    # 3. CUSTOMER CONVERSATION (Uses /start and /customer)
    customer_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('customer', customer_start),
            CommandHandler('dashboard', dashboard),
            CommandHandler('start', start),
            CallbackQueryHandler(customer_start, pattern='^open_dashboard$'),
            CallbackQueryHandler(browse_menu, pattern='^browse_menu$'),
        ],
        states={
            CUSTOMER_MENU: [CallbackQueryHandler(customer_callback)],
            BUYER_ESCROW_INFO: [CallbackQueryHandler(customer_callback)],
            BUYER_ENTER_PRODUCT_ID: [
                MessageHandler(Filters.text & ~Filters.command, handle_buyer_product_id),
                CallbackQueryHandler(customer_callback)
            ],
            BUYER_PAYMENT_METHODS: [CallbackQueryHandler(customer_callback)],
            BUYER_PAYMENT_INSTRUCTIONS: [CallbackQueryHandler(customer_callback)],
            BUYER_CONFIRM_PAYMENT: [CallbackQueryHandler(customer_callback)],
            SELLER_INFO: [CallbackQueryHandler(customer_callback)],
            SELLER_PLATFORM: [CallbackQueryHandler(customer_callback)],
            SELLER_TYPE: [CallbackQueryHandler(customer_callback)],
            SELLER_DETAILS: [
                MessageHandler(Filters.text & ~Filters.command, handle_customer_details),
                CallbackQueryHandler(customer_callback)
            ],
            SELLER_PRICE: [
                MessageHandler(Filters.text & ~Filters.command, handle_customer_price),
                CallbackQueryHandler(customer_callback)
            ],
            SELLER_CONTACT: [
                MessageHandler(Filters.text & ~Filters.command, handle_customer_contact),
                CallbackQueryHandler(customer_callback)
            ],
            SELLER_SCREENSHOTS: [
                MessageHandler(Filters.photo, handle_customer_screenshot_upload),
                MessageHandler(Filters.text & ~Filters.command, handle_customer_screenshot_upload),
                CallbackQueryHandler(customer_callback)
            ],
            SELLER_CONFIRM: [CallbackQueryHandler(customer_callback)],
            CUSTOMER_MANAGE_LISTINGS: [CallbackQueryHandler(customer_callback)],
            CUSTOMER_CONFIRM_SOLD: [CallbackQueryHandler(customer_callback)],
            BROWSE_MENU: [CallbackQueryHandler(customer_callback)],
            BROWSE_PLATFORM_LIST: [CallbackQueryHandler(customer_callback)],
            BROWSE_LISTING_DETAIL: [CallbackQueryHandler(customer_callback)],
            BROWSE_FILTER_MENU: [CallbackQueryHandler(customer_callback)],
            BROWSE_FILTER_PRICE: [
                MessageHandler(Filters.text & ~Filters.command, browse_handle_filter_input),
                CallbackQueryHandler(customer_callback)
            ],
            BROWSE_FILTER_SUBS: [
                MessageHandler(Filters.text & ~Filters.command, browse_handle_filter_input),
                CallbackQueryHandler(customer_callback)
            ],
            BROWSE_SEARCH_KEYWORD: [
                MessageHandler(Filters.text & ~Filters.command, browse_handle_filter_input),
                CallbackQueryHandler(customer_callback)
            ],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
        name="customer_conversation"
    )
    dispatcher.add_handler(customer_conv_handler)
    
    # Start Flask webhook server in background thread for Cryptomus callbacks
    global _bot_instance
    _bot_instance = updater.bot
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask webhook server started on port 8080")

    logger.info("✅ SMYARDS BOT STARTED")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()