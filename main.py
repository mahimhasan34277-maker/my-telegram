import os
import uuid
import asyncio
import threading
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot import types

# Credentials
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SESSION_STRING = "1BVtsOKwBu0_woOgzB1A9opoKGx_QhsHug1kc8mrtVgjoHS-yaKl_eTYiCNAonHtqO5NHwf6_TSAxT6hRd8IuCPNqP1PIxYSJ8JNk4jbH9zkxujqyMPnwY98SfiX_slhZSFX2J9XdJ4-b1-Y3fUgzxvQa5XH0l1xJFjBXwtNKJQNk-zXm3nS5JPQuhafuckdHhrlPoOddPVMEXAfizN86pggqrUHY8bMeTifWgHdmj8FqK2GrIc6HGzthiaQ5iIlF-WLXHWNDOdkne3iUFONowwW-q76ioUwG1wTAf_bcmkY-HDUUMLqzadj1YxU1zVr0WP5ncoPJvURL3eo9f-1Ds35Zo48u8Is="
OWNER_ID = 7034610665
SOURCE_CHANNEL = -1003280015883

bot = telebot.TeleBot(BOT_TOKEN)
pending_purchases = {}
USER_DB = "users.json"

# ইউজার ডেটাবেজ ম্যানেজমেন্ট
def load_users():
    if not os.path.exists(USER_DB): return {}
    try:
        with open(USER_DB, "r") as f: return json.load(f)
    except: return {}

def save_users(users):
    with open(USER_DB, "w") as f: json.dump(users, f)

# বাটন হ্যান্ডলার
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    token = call.data.split("_")[1]
    if call.data.startswith("cancel_"):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ অপারেশনটি বাতিল করা হয়েছে।")
        if token in pending_purchases: del pending_purchases[token]
    elif call.data.startswith("confirm_"):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ কেনা সম্পন্ন হয়েছে!")

# এপ্রুভাল কমান্ড
@bot.message_handler(commands=["approve"])
def approve_user(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: return bot.reply_to(message, "ব্যবহার: /approve [USER_ID]")
    users = load_users()
    users[args[1]] = {"status": "approved"}
    save_users(users)
    bot.reply_to(message, f"ইউজার {args[1]} এখন অনুমোদিত!")

# পোলিং
def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()

# স্ক্র্যাপার
async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        listing = {"balance": 10.0, "listing_id": "TEST123"}
        # এখানে এপ্রুভড ইউজারদের লজিক যোগ করা যাবে
        print("নতুন লিস্টিং পাওয়া গেছে") 
    await client.run_until_disconnected()

asyncio.run(run_scraper())
