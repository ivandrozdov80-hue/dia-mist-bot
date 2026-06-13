import os
import json
from flask import Flask, request

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.webhook import get_new_configured_app
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ======================
# CONFIG
# ======================

TOKEN = os.environ["TOKEN"]

WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # Render URL

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ======================
# GOOGLE SHEETS
# ======================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open("DIA.MIST CRM").sheet1

# ======================
# MEMORY
# ======================

user_data = {}

# ======================
# KEYBOARD
# ======================

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(KeyboardButton("📱 Поделиться номером", request_contact=True))

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("🎁 Акции", "⭐ Мои посещения")

# ======================
# START
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id

    user_data[user_id] = {
        "telegram_id": user_id,
        "username": message.from_user.username
    }

    await message.answer(
        "💨 DIA.MIST\n\nНапиши имя 👇"
    )

# ======================
# CONTACT
# ======================

@dp.message_handler(content_types=["contact"])
async def contact(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    user_data[user_id]["phone"] = message.contact.phone_number

    await message.answer(
        "🎂 Дата рождения?",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================
# TEXT FLOW
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def text(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if "name" not in data:
        data["name"] = message.text

        await message.answer(
            "📱 Отправь номер",
            reply_markup=phone_keyboard
        )
        return

    if "phone" not in data:
        return

    if "birthday" not in data:

        data["birthday"] = message.text

        sheet.append_row([
            data["telegram_id"],
            data["username"],
            data["name"],
            data["phone"],
            data["birthday"],
            0,
            0,
            datetime.now().strftime("%d.%m.%Y")
        ])

        await message.answer(
            "🎉 Готово!",
            reply_markup=main_menu
        )

        user_data.pop(user_id)

# ======================
# FLASK WEB SERVER
# ======================

app = Flask(__name__)

@app.route("/")
def home():
    return "DIA.MIST bot is running"

# ======================
# WEBHOOK SETUP
# ======================

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = types.Update(**request.json)
    await dp.process_update(update)
    return "ok"

@app.before_first_request
async def on_start():
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
