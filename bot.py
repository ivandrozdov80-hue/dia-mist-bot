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
# PHONE BUTTON
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
# MAIN MENU
# ======================

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)

main_menu.row(
    "🎁 Акции",
    "🏆 Розыгрыш недели"
)

main_menu.row(
    "⭐ Мои посещения",
    "📍 Контакты"
)

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
        "💨 Приветствую тебя в DIA.MIST!\n\n"
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
# MENU BUTTONS
# ======================

@dp.message_handler(lambda message: message.text == "🎁 Акции")
async def promotions(message: types.Message):

    await message.answer(
        "🔥 АКЦИЯ НЕДЕЛИ\n\n"
        "Закажи 2 кальяна и получи чайник чая бесплатно ☕"
    )


@dp.message_handler(lambda message: message.text == "🏆 Розыгрыш недели")
async def giveaway(message: types.Message):

    await message.answer(
        "🏆 РОЗЫГРЫШ НЕДЕЛИ\n\n"
        "🎁 Приз: бесплатный кальян\n\n"
        "Победитель будет выбран случайным образом в воскресенье."
    )


@dp.message_handler(lambda message: message.text == "⭐ Мои посещения")
async def visits(message: types.Message):

    await message.answer(
        "⭐ Твои посещения\n\n"
        "Пока посещений: 0\n\n"
        "До бесплатного кальяна осталось 6 посещений 🔥"
    )


@dp.message_handler(lambda message: message.text == "📍 Контакты")
async def contacts(message: types.Message):

    await message.answer(
        "📍 DIA.MIST\n\n"
        "Укажи здесь свой адрес\n\n"
        "🕐 Режим работы:\n"
        "12:00 - 23:00\n\n"
        "📞 Телефон:\n"
        "+XXXXXXXXXXX"
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

    # Имя

    if "name" not in data:

        data["name"] = message.text

        await message.answer(
            "📱 Нажми кнопку ниже и поделись номером телефона",
            reply_markup=phone_keyboard
        )
        return

    # Ждем контакт

    if "phone" not in data:
        return

    # День рождения

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
            "🎉 Регистрация завершена!\n\n"
            "Добро пожаловать в DIA.MIST Club 💨\n\n"
            "Теперь тебе доступны все возможности клуба 👇",
            reply_markup=main_menu
        )

        user_data.pop(user_id)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
