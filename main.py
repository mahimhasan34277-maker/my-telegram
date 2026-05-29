import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot.async_telebot import AsyncTeleBot

# Config
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = "8839286449:AAEBGJHmPDY4_FAddCA9uVgtz5fXOqBoLXg"
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665

# Render এর Environment Variable থেকে সেশন স্ট্রিং নিবে
SESSION_STRING = os.environ.get("SESSION_STRING", "")

bot = AsyncTeleBot(BOT_TOKEN)

async def start_bot():
    if not SESSION_STRING:
        print("ERROR: SESSION_STRING পাওয়া যায়নি!")
        return
        
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        txt = event.message.text
        # আপনার ফিল্টার
        if "Used PayPal: No" in txt and "Used Google: No" in txt and "Registered: False" in txt:
            await bot.send_message(OWNER_ID, f"🚨 Match Found:\n{txt}")

    await client.run_until_disconnected()

async def main():
    await asyncio.gather(bot.polling(), start_bot())

if __name__ == "__main__":
    asyncio.run(main())
    
