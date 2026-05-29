import os
import re
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot.async_telebot import AsyncTeleBot
from telebot import types

# --- Configuration ---
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = "8839286449:AAEBGJHmPDY4_FAddCA9uVgtz5fXOqBoLXg"
SESSION_STRING = "YOUR_SESSION_STRING_HERE" 
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665
APPROVED_FILE = "approved_users.txt"

logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(BOT_TOKEN)

# --- Parser ---
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

# --- Bot Features ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    await bot.reply_to(message, "✅ StockZone Bot is Active!")

@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data == "buy":
        await bot.answer_callback_query(call.id, "Buying process initiated...")
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
        if not txt: return
        d = parse_listing(txt)
        
        # Filter Logic
        if d["pp"] == "No" and d["goog"] == "No" and d["reg"] == "False":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Buy Now", callback_data="buy"),
                       types.InlineKeyboardButton("❌ Skip", callback_data="skip"))
            
            msg = f"🚨 *New Listing!*\n\nBIN: `{d['bin']}`\nBal: `${d['bal']}`\nPrice: `{d['price']}`"
            await bot.send_message(OWNER_ID, msg, parse_mode="Markdown", reply_markup=markup)
            
    await client.run_until_disconnected()

# --- Main ---
async def main():
    await asyncio.gather(bot.polling(), start_scraper())

if __name__ == "__main__":
    asyncio.run(main())
            
