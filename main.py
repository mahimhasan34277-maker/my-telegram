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
SESSION_STRING = "YOUR_SESSION_STRING_HERE" 
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665

# --- Global State ---
filter_active = True
stats = {"listings": 0}
history = []

logging.basicConfig(level=logging.INFO)
bot = AsyncTeleBot(BOT_TOKEN)

# --- Features & Commands ---
@bot.message_handler(commands=['start'])
async def cmd_start(message):
    await bot.reply_to(message, "✅ Bot is active!\nCommands: /stats, /filteron, /filteroff, /history")

@bot.message_handler(commands=['stats'])
async def cmd_stats(message):
    await bot.reply_to(message, f"📊 Total Listings Processed: {stats['listings']}")

@bot.message_handler(commands=['filteron', 'filteroff'])
async def cmd_filter(message):
    global filter_active
    filter_active = (message.text == "/filteron")
    await bot.reply_to(message, f"✅ Filter is now {'ON' if filter_active else 'OFF'}")

@bot.message_handler(commands=['history'])
async def cmd_history(message):
    if not history:
        await bot.reply_to(message, "📭 No history found.")
    else:
        await bot.reply_to(message, "📜 Last 5 Listings:\n" + "\n".join(history[-5:]))

# --- Scraper Logic ---
async def start_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        global filter_active
        txt = event.message.text
        if not txt: return
        
        # Parse data
        d = {"bin": "N/A", "bal": "0.00", "price": "0.00"}
        if "Card BIN:" in txt: d["bin"] = txt.split("Card BIN:")[1].split("\n")[0].strip()
        if "Balance:" in txt: d["bal"] = txt.split("Balance:")[1].split("\n")[0].strip()
        
        stats["listings"] += 1
        history.append(f"BIN: {d['bin']} | Bal: {d['bal']}")
        
        # Apply filter
        if filter_active:
            if "Used PayPal: Yes" in txt or "Used Google: Yes" in txt:
                return # Skip listings that don't match criteria
        
        # Send
        msg = f"🚨 *New Listing!*\n\nBIN: `{d['bin']}`\nBal: `{d['bal']}`"
        await bot.send_message(OWNER_ID, msg, parse_mode="Markdown")
            
    await client.run_until_disconnected()

# --- Main ---
async def main():
    await asyncio.gather(bot.polling(), start_scraper())

if __name__ == "__main__":
    asyncio.run(main())
    
