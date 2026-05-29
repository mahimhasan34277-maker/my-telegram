import os
import re
import uuid
import asyncio
import threading
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot import types

# 1. Credentials
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# মনে রাখবেন আপনার SESSION_STRING টি এখানে সঠিক থাকতে হবে
SESSION_STRING = "1BVtsOKwBu0_woOgzB1A9opoKGx_QhsHug1kc8mrtVgjoHS-yaKl_eTYiCNAonHtqO5NHwf6_TSAxT6hRd8IuCPNqP1PIxYSJ8JNk4jbH9zkxujqyMPnwY98SfiX_slhZSFX2J9XdJ4-b1-Y3fUgzxvQa5XH0l1xJFjBXwtNKJQNk-zXm3nS5JPQuhafuckdHhrlPoOddPVMEXAfizN86pggqrUHY8bMeTifWgHdmj8FqK2GrIc6HGzthiaQ5iIlF-WLXHWNDOdkne3iUFONowwW-q76ioUwG1wTAf_bcmkY-HDUUMLqzadj1YxU1zVr0WP5ncoPJvURL3eo9f-1Ds35Zo48u8Is="

# 2. Source channel and owner
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665

# 3. Live filter settings
FILTER = {
    "enabled": True,
    "min_balance": 1.00,
    "max_balance": 20.00,
    "require_paypal_no": True,
    "require_google_no": True,
    "require_registered_no": True,
}

bot = telebot.TeleBot(BOT_TOKEN)
pending_purchases = {}

STATE = {"paused": False}

def parse_listing(text: str) -> dict:
    result = {"raw": text}
    m = re.search(r"[Bb]alance[:\s]+\$?([\d,]+\.?\d*)\s*(?:USD)?", text)
    if m: result["balance"] = float(m.group(1).replace(",", ""))
    m = re.search(r"[Uu]sed\s*[Pp]ay[Pp]al[:\s]+(Yes|No)", text)
    if m: result["used_paypal"] = m.group(1).strip()
    m = re.search(r"[Uu]sed\s*[Gg]oogle[:\s]+(Yes|No)", text)
    if m: result["used_google"] = m.group(1).strip()
    m = re.search(r"[Rr]egistered[:\s]+(Yes|No|True|False)", text, re.I)
    if m:
        val = m.group(1).strip()
        result["registered"] = "No" if val.lower() in ("no", "false") else "Yes"
    m = re.search(r"[Ll]isting\s*[Ii][Dd]?[:\s#]+(\w+)", text)
    if m: result["listing_id"] = m.group(1)
    return result

def parse_set_filter_args(args: str) -> tuple[dict, list[str]]:
    updates = {}
    errors = []
    for token in args.strip().split():
        if ":" not in token:
            errors.append(f"Unrecognised token `{token}`")
            continue
        key, _, value = token.partition(":")
        key, value = key.lower().strip(), value.strip()
        if key == "balance":
            if "-" in value:
                parts = value.split("-", 1)
                try:
                    updates["min_balance"], updates["max_balance"] = float(parts[0]), float(parts[1])
                except ValueError: errors.append(f"Invalid balance `{value}`")
        elif key in ("paypal", "used_paypal"):
            updates["require_paypal_no"] = (value.lower() in ("no", "false"))
        elif key in ("google", "used_google"):
            updates["require_google_no"] = (value.lower() in ("no", "false"))
        elif key == "registered":
            updates["require_registered_no"] = (value.lower() in ("no", "false"))
    return updates, errors

def filter_summary() -> str:
    f = FILTER
    state = "🟢 *Active*" if f["enabled"] else "🔴 *Disabled*"
    return (f"⚙️ *Filter Status:* {state}\n• Balance: `${f['min_balance']:.2f} – ${f['max_balance']:.2f}`\n"
            f"• Used PayPal/Google/Reg: Must be No ✅")

def trigger_auto_buy(listing: dict):
    print(f"[AUTO-BUY] Listing ID: {listing.get('listing_id')}")
    return True

def send_confirmation_prompt(listing: dict):
    token = str(uuid.uuid4())[:8]
    pending_purchases[token] = listing
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Buy Now", callback_data=f"confirm_{token}"),
        types.InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{token}"), 
    )
    msg = (f"🚨 *Listing Matches Your Criteria!*\n\n💰 Balance: `${listing.get('balance', 0):.2f}`\n"
           f"🆔 Listing ID: `{listing.get('listing_id', 'N/A')}`\n\n⏳ Auto-skipped in 60s.")
    sent = bot.send_message(OWNER_ID, msg, parse_mode="Markdown", reply_markup=markup)
    
    def auto_expire():
        if token in pending_purchases:
            pending_purchases.pop(token, None)
            try: bot.edit_message_text(chat_id=OWNER_ID, message_id=sent.message_id, text=msg + "\n\n⌛ *Expired.*", parse_mode="Markdown")
            except: pass
    threading.Timer(60, auto_expire).start()

@bot.callback_query_handler(func=lambda c: c.from_user.id == OWNER_ID)
def handle_callback(call):
    if call.data.startswith("confirm_"):
        token = call.data.split("_")[1]
        listing = pending_purchases.pop(token, None)
        if listing:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
            trigger_auto_buy(listing)
            bot.answer_callback_query(call.id, "✅ Buying!")
    elif call.data.startswith("cancel_"):
        token = call.data.split("_")[1]
        pending_purchases.pop(token, None)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.answer_callback_query(call.id, "❌ Cancelled.")

@bot.message_handler(commands=["start"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_start(message):
    bot.reply_to(message, "✅ Bot is active!")

def start_bot_polling():
    bot.infinity_polling()

threading.Thread(target=start_bot_polling, daemon=True).start()

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        if STATE["paused"]: return
        listing = parse_listing(event.message.text or "")
        send_confirmation_prompt(listing)
    await client.run_until_disconnected()

asyncio.run(run_scraper())
