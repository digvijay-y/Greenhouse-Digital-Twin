import random
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

TOKEN = '6914100769:AAEZzLUaOy5mGPb69XFjpKAglvv1gZmTE2A'
chat_id = None

# Assuming tele_fetch is a dictionary containing moisture values
tele_fetch = {
    "sensor1": 153,
    "sensor2": 153,
    "sensor3": 153,
    "sensor4": 153,
    "sensor5": 153,
    "sensor6": 153
}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! This is your Smart Irrigation System.')
    global chat_id
    chat_id = update.message.chat_id
    send_sensor_data()

def send_sensor_data():
    if chat_id is not None:
        # Fetch moisture values directly from the tele_fetch dictionary
        moisture_values = [tele_fetch.get(f"sensor{i}", 0) for i in range(1, 5)]

        # Create the message
        message = (
            f"sensor1: Moisture_value {moisture_values[0]}\n"
            f"sensor2: Moisture_value {moisture_values[1]}\n"
            f"sensor3: Moisture_value {moisture_values[2]}\n"
            f"sensor4: Moisture_value {moisture_values[3]}\n"
        )

        # Send the message to the Telegram bot
        bot = Bot(token=TOKEN)
        bot.send_message(chat_id=chat_id, text=message)

def main():
    updater = Updater(token=TOKEN, use_context=True)

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
     

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
