import telebot

TOKEN = '8839286449:AAGoUpkTpPXmxEuimqA4PadWJhgrsvjUd58'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "বট সফলভাবে চালু হয়েছে!")

bot.polling()
