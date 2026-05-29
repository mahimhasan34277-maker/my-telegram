import os
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telebot.async_telebot import AsyncTeleBot

# Config - নতুন টোকেন বসানো হয়েছে
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = "8839286449:AAEl-g-3B9SQ2Vo_FD1EEGw1XwSzXdB2Rms" 
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665

# সেশন স্ট্রিং এনভায়রনমেন্ট থেকে নিবে
SESSION_STRING = os.environ.get("SESSION_STRING", "")

bot = AsyncTeleBot(BOT_TOKEN)

async def start_scraper():
    if not SESSION_STRING:
        print("SESSION_STRING খালি!")
        return
    
    # নতুন সেশন স্ট্রিং জেনারেট করে এখানে সেট করতে ভুলবেন না
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        txt = event.message.text
        if "Used PayPal: No" in txt and "Used Google: No" in txt and "Registered: False" in txt:
            await bot.send_message(OWNER_ID, f"✅ Match Found:\n{txt}")

    await client.run_until_disconnected()

async def main():
    await asyncio.gather(bot.polling(), start_scraper())

if __name__ == "__main__":
    asyncio.run(main())
    
