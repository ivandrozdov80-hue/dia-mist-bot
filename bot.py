from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

from aiohttp import web
import threading

# ======================
# TELEGRAM
# ======================

TOKEN = os.environ["TOKEN"]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ======================
# GOOGLE SHEETS
# ======================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    scope
)

client = gspread.authorize(creds)
sheet = client.open("DIA.MIST CRM").sheet1

# ======================
# MEMORY
# ======================

user_data = {}

# ======================
# KEYBOARD
# ======================

phone_keyboard = ReplyKeyboardMarkup(
    resize_keyboard=True,
    one_time_keyboard=True
)

phone_button = KeyboardButton(
    text="📱 Поделиться номером",
    request_contact=True
)

phone_keyboard.add(phone_button)

# ======================
# BOT HANDLERS
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id

    user_data[user_id] = {
        "telegram_id": user_id,
        "username": message.from_user.username
    }

    await message.answer(
        "💨 Приветсвую тебя в DIA.MIST!\n\n"
        "🎁 Участвуй в еженедельных розыгрышах\n"
        "⭐ Копи посещения\n"
        "🔥 Получай бонусы и подарки\n\n"
        "Напиши своё имя 👇"
    )

@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    user_data[user_id]["phone"] = message.contact.phone_number

    await message.answer(
        "🎂 Когда у тебя день рождения? (пример: 15.08)",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    # NAME
    if "name" not in data:
        data["name"] = message.text

        await message.answer(
            "📱 Отправь номер телефона кнопкой ниже",
            reply_markup=phone_keyboard
        )
        return

    if "phone" not in data:
        return

    # BIRTHDAY
    if "birthday" not in data:

        data["birthday"] = message.text

        reg_date = datetime.now().strftime("%d.%m.%Y")

        sheet.append_row([
            data["telegram_id"],
            data["username"],
            data["name"],
            data["phone"],
            data["birthday"],
            0,
            0,
            reg_date
        ])

        await message.answer(
            "🎉 Регистрация завершена!",
            reply_markup=ReplyKeyboardRemove()
        )

        user_data.pop(user_id)

# ======================
# WEB SERVER (ВАЖНО ДЛЯ RENDER)
# ======================

async def handle(request):
    return web.Response(text="Bot is running ✅")

def run_web():
    app = web.Application()
    app.router.add_get("/", handle)
    return app

def start_web():
    port = int(os.environ.get("PORT", 10000))
    web.run_app(run_web(), host="0.0.0.0", port=port)

# ======================
# START BOTH (BOT + WEB)
# ======================

if __name__ == "__main__":

    # запускаем web сервер в отдельном потоке
    threading.Thread(target=start_web, daemon=True).start()

    # запускаем бот
    executor.start_polling(dp, skip_updates=True)
