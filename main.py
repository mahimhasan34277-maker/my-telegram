import os
import threading
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot

# Credentials
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SESSION_STRING = "1BVtsOKwBu0_woOgzB1A9opoKGx_QhsHug1kc8mrtVgjoHS-yaKl_eTYiCNAonHtqO5NHwf6_TSAxT6hRd8IuCPNqP1PIxYSJ8JNk4jbH9zkxujqyMPnwY98SfiX_slhZSFX2J9XdJ4-b1-Y3fUgzxvQa5XH0l1xJFjBXwtNKJQNk-zXm3nS5JPQuhafuckdHhrlPoOddPVMEXAfizN86pggqrUHY8bMeTifWgHdmj8FqK2GrIc6HGzthiaQ5iIlF-WLXHWNDOdkne3iUFONowwW-q76ioUwG1wTAf_bcmkY-HDUUMLqzadj1YxU1zVr0WP5ncoPJvURL3eo9f-1Ds35Zo48u8Is="
SOURCE_CHANNEL = -1003280015883

bot = telebot.TeleBot(BOT_TOKEN)

# বট পোলিং ফাংশন
def run_bot():
    print("Bot is polling...")
    bot.infinity_polling()

# স্ক্র্যাপার ফাংশন
async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        print("New message received")
    
    print("Scraper is running...")
    await client.run_until_disconnected()

# দুটি থ্রেড একসাথে চালানো
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    asyncio.run(run_scraper())
    
