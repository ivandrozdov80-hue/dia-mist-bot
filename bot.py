import os
import json
from datetime import datetime
from flask import Flask, request

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils.executor import start_webhook

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# CONFIG
# ======================

TOKEN = os.environ["TOKEN"]
WEBHOOK_HOST = os.environ["WEBHOOK_HOST"]  # например https://xxx.onrender.com
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

app = Flask(__name__)

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
# HANDLERS
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id

    user_data[user_id] = {
        "telegram_id": user_id,
        "username": message.from_user.username
    }

    await message.answer(
        "💨 DIA.MIST\n\n"
        "Напиши своё имя 👇"
    )


@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def text(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if "name" not in data:
        data["name"] = message.text
        await message.answer("📱 Отправь телефон")
        return

    if "phone" not in data:
        data["phone"] = message.text
        await message.answer("🎂 Дата рождения?")
        return

    if "birthday" not in data:
        data["birthday"] = message.text

        reg = datetime.now().strftime("%d.%m.%Y")

        sheet.append_row([
            data["telegram_id"],
            data["username"],
            data["name"],
            data["phone"],
            data["birthday"],
            0,
            0,
            reg
        ])

        await message.answer("🔥 Готово! Ты в клубе DIA.MIST")
        user_data.pop(user_id)


# ======================
# WEBHOOK ROUTE
# ======================

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = types.Update(**request.json)
    await dp.process_update(update)
    return "ok"


# ======================
# STARTUP / SHUTDOWN
# ======================

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()


# ======================
# RUN (IMPORTANT FOR RENDER)
# ======================

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
