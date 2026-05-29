import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot

API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = "8839286449:AAEBGJHmPDY4_FAddCA9uVgtz5fXOqBoLXg"
SOURCE_CHANNEL = -1003280015883
OWNER_ID = 7034610665

# সেশন স্ট্রিং অবশ্যই Render-এর Environment Variable-এ দিবেন
SESSION_STRING = os.environ.get("SESSION_STRING", "")

bot = telebot.TeleBot(BOT_TOKEN)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    txt = event.message.text
    # ফিল্টার লজিক
    if "Used PayPal: No" in txt and "Used Google: No" in txt and "Registered: False" in txt:
        bot.send_message(OWNER_ID, f"✅ Match Found:\n{txt}")

print("Bot is starting...")
client.start()
client.run_until_disconnected()
