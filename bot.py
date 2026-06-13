from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

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
# BUTTON PHONE
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
        "💨 Приветсвую тебя в DIA.MIST!\n\n"
        "🎁 Участвуй в еженедельных розыгрышах\n"
        "⭐ Копи посещения\n"
        "🔥 Получай бонусы и подарки\n"
        "🎂 Получай подарок на день рождения\n\n"
        "Для участия напиши своё имя 👇"
    )

# ======================
# CONTACT
# ======================

@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    user_data[user_id]["phone"] = message.contact.phone_number

    await message.answer(
        "🎂 Когда у тебя день рождения?\n\n"
        "Например: 15.08",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================
# TEXT HANDLER
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    # Шаг 1 — имя

    if "name" not in data:

        data["name"] = message.text

        await message.answer(
            "📱 Нажми кнопку ниже и поделись номером телефона",
            reply_markup=phone_keyboard
        )
        return

    # Если номер ещё не получен — ждём контакт

    if "phone" not in data:
        return

    # Шаг 2 — день рождения

    if "birthday" not in data:

        data["birthday"] = message.text

        reg_date = datetime.now().strftime("%d.%m.%Y")

        sheet.append_row([
            data["telegram_id"],
            data["username"],
            data["name"],
            data["phone"],
            data["birthday"],
            0,  # visits
            0,  # free_hookah
            reg_date
        ])

        await message.answer(
            "🎉 Регистрация завершена!\n\n"
            "Добро пожаловать в DIA.MIST Club 💨\n\n"
            "⭐ Посещений: 0\n"
            "🎁 Бесплатных кальянов: 0\n\n"
            "Следи за акциями и розыгрышами в нашем канале 🔥",
            reply_markup=ReplyKeyboardRemove()
        )

        user_data.pop(user_id)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
