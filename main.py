import telebot
from telebot import types

TOKEN = '8839286449:AAGoUpkTpPXmxEuimqA4PadWJhgrsvjUd58'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    # বাটন তৈরি
    markup = types.InlineKeyboardMarkup()
    # এখানে 'Cancel' বাটন যোগ করা হয়েছে
    markup.add(types.InlineKeyboardButton("✅ Buy Now", callback_data="buy"), 
               types.InlineKeyboardButton("❌ Cancel", callback_data="cancel"))
    
    bot.send_message(message.chat.id, "বট সচল হয়েছে! নিচে আপনার অপশন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "buy":
        bot.answer_callback_query(call.id, "কেনার প্রক্রিয়া শুরু হচ্ছে...")
        bot.send_message(call.message.chat.id, "আপনি 'Buy Now' সিলেক্ট করেছেন।")
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "অপারেশন বাতিল করা হয়েছে।")
        bot.send_message(call.message.chat.id, "ক্যানসেল করা হয়েছে।")

bot.polling()
