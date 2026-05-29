import os
import threading
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from flask import Flask

# রেন্ডারের ফ্রি পোর্টের ট্রিক (ওয়েব সার্ভার)
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    # রেন্ডার ফ্রি টায়ারে এই পোর্টটি খোঁজে, না পেলে বন্ধ করে দেয়
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Credentials
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SESSION_STRING = "1BVtsOKwBu0_woOgzB1A9opoKGx_QhsHug1kc8mrtVgjoHS-yaKl_eTYiCNAonHtqO5NHwf6_TSAxT6hRd8IuCPNqP1PIxYSJ8JNk4jbH9zkxujqyMPnwY98SfiX_slhZSFX2J9XdJ4-b1-Y3fUgzxvQa5XH0l1xJFjBXwtNKJQNk-zXm3nS5JPQuhafuckdHhrlPoOddPVMEXAfizN86pggqrUHY8bMeTifWgHdmj8FqK2GrIc6HGzthiaQ5iIlF-WLXHWNDOdkne3iUFONowwW-q76ioUwG1wTAf_bcmkY-HDUUMLqzadj1YxU1zVr0WP5ncoPJvURL3eo9f-1Ds35Zo48u8Is="
SOURCE_CHANNEL = -1003280015883

bot = telebot.TeleBot(BOT_TOKEN)

# আপনার বটের কমান্ড (টেস্ট করার জন্য)
@bot.message_handler(commands=['start', 'hello'])
def send_welcome(message):
    bot.reply_to(message, "হ্যালো! বট এখন সচল আছে।")

def run_bot():
    print("Bot polling started...")
    bot.infinity_polling()

async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        print("New message from channel")
    
    print("Scraper started...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    # ১. প্রথমে ব্যাকগ্রাউন্ডে ওয়েব সার্ভার চালু হবে রেন্ডারকে ফাঁকি দেওয়ার জন্য
    threading.Thread(target=run_web_server, daemon=True).start()
    # ২. তারপর বট পোলিং চালু হবে
    threading.Thread(target=run_bot, daemon=True).start()
    # ৩. সবশেষে স্ক্র্যাপার চলবে
    asyncio.run(run_scraper())
    
