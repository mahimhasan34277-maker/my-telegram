import os, re, asyncio, logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot import types

# --- Configuration ---
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = "8839286449:AAEBGJHmPDY4_FAddCA9uVgtz5fXOqBoLXg"
SESSION_STRING = "YOUR_SESSION_STRING_HERE" # আপনার সেশন স্ট্রিং দিন
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665
APPROVED_FILE = "approved_users.txt"

# Logger
logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(BOT_TOKEN)

# --- Admin Tools ---
def get_approved():
    if not os.path.exists(APPROVED_FILE): return []
    with open(APPROVED_FILE, "r") as f: return [line.strip() for line in f]

# --- Parser & Logic ---
def parse_listing(text):
    data = {"bin": "N/A", "bal": "0.00", "price": "0.00", "pp": "No", "goog": "No", "reg": "False"}
    try:
        if "Card BIN:" in text: data["bin"] = text.split("Card BIN:")[1].split("\n")[0].strip()
        if "Balance:" in text: data["bal"] = text.split("Balance:")[1].split("\n")[0].strip().replace("$", "").replace("USD", "")
        if "Price:" in text: data["price"] = text.split("Price:")[1].split("\n")[0].strip()
        if "Used PayPal: Yes" in text: data["pp"] = "Yes"
        if "Used Google: Yes" in text: data["goog"] = "Yes"
        if "Registered: True" in text: data["reg"] = "True"
    except: pass
    return data

# --- Bot Commands ---
@bot.message_handler(commands=['approve'])
async def cmd_approve(message):
    if message.from_user.id != OWNER_ID: return
    try:
        uid = message.text.split()[1]
        with open(APPROVED_FILE, "a") as f: f.write(f"{uid}\n")
        await bot.reply_to(message, f"✅ User {uid} approved.")
    except: await bot.reply_to(message, "Usage: /approve <id>")

@bot.message_handler(commands=['broadcast'])
async def cmd_broadcast(message):
    if message.from_user.id != OWNER_ID: return
    text = message.text.replace("/broadcast ", "")
    for uid in get_approved():
        try: await bot.send_message(uid, text)
        except: pass
    await bot.reply_to(message, "✅ Broadcast sent.")

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data == "buy":
        await bot.answer_callback_query(call.id, "Buying process initiated...")
        await bot.send_message(OWNER_ID, f"🛒 User clicked Buy Now on listing.")
    elif call.data == "skip":
        await bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        await bot.answer_callback_query(call.id, "Listing skipped.")

# --- Scraper ---
async def start_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        txt = event.message.text
        d = parse_listing(txt)
        
        # Filter Logic: Only send if criteria match
        if d["pp"] == "No" and d["goog"] == "No" and d["reg"] == "False":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Buy Now", callback_data="buy"),
                       types.InlineKeyboardButton("❌ Skip", callback_data="skip"))
            
            msg = f"🚨 *New Listing!*\n\nBIN: `{d['bin']}`\nBal: `${d['bal']}`\nPrice: `{d['price']}`"
            await bot.send_message(OWNER_ID, msg, parse_mode="Markdown", reply_markup=markup)
            
    await client.run_until_disconnected()

# --- Main Entry ---
async def main():
    await asyncio.gather(bot.polling(), start_scraper())

if __name__ == "__main__":
    asyncio.run(main())
 
