import os
import telebot
from telebot import types

# এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন নিচ্ছে
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    # এখানে বাটন টেক্সট 'Cancel' করে দেওয়া হয়েছে
    markup.add(types.InlineKeyboardButton("✅ Buy Now", callback_data="buy"), 
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel"))
    bot.send_message(message.chat.id, "বট সচল হয়েছে!", reply_markup=markup)

print("বট রান হচ্ছে...")
bot.polling()
