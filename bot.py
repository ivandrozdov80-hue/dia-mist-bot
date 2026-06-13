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
        "⭐ Копи посещения (6 = бесплатный кальян)\n"
        "🔥 Получай бонусы и подарки\n"
        "🎂 Подарок на день рождения\n\n"
        "Напиши своё имя 👇"
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
        "Закажи 2 кальяна и получи чай бесплатно ☕"
    )


@dp.message_handler(lambda message: message.text == "🏆 Розыгрыш недели")
async def giveaway(message: types.Message):

    await message.answer(
        "🏆 РОЗЫГРЫШ НЕДЕЛИ\n\n"
        "🎁 Бесплатный кальян каждую неделю\n"
        "Участвуют все зарегистрированные гости 🔥"
    )


@dp.message_handler(lambda message: message.text == "⭐ Мои посещения")
async def visits(message: types.Message):

    user_id = message.from_user.id

    data = sheet.get_all_records()

    for row in data:
        if str(row["telegram_id"]) == str(user_id):

            v = row["visits"]

            await message.answer(
                f"⭐ Твои посещения: {v}/6\n\n"
                f"До бесплатного кальяна осталось: {6 - int(v)} 🔥"
            )
            return

    await message.answer("Ты ещё не зарегистрирован.")

@dp.message_handler(lambda message: message.text == "📍 Контакты")
async def contacts(message: types.Message):

    await message.answer(
        "📍 DIA.MIST\n\n"
        "🕐 12:00 - 23:00\n\n"
        "📞 +XXXXXXXXXXX"
    )

# ======================
# REGISTRATION
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    # имя
    if "name" not in data:

        data["name"] = message.text

        await message.answer(
            "📱 Поделись номером телефона",
            reply_markup=phone_keyboard
        )
        return

    if "phone" not in data:
        return

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
            "Теперь копи посещения и получай бесплатный кальян 🔥",
            reply_markup=main_menu
        )

        user_data.pop(user_id)

# ======================
# ADD VISIT (ADMIN)
# ======================

@dp.message_handler(lambda message: message.text and message.text.startswith("/addvisit"))
async def add_visit(message: types.Message):

    try:
        parts = message.text.split()
        user_id = parts[1]

        data = sheet.get_all_records()

        for i, row in enumerate(data, start=2):

            if str(row["telegram_id"]) == str(user_id):

                visits = int(row["visits"]) + 1
                sheet.update_cell(i, 6, visits)

                await message.answer(f"⭐ Визит добавлен: {visits}/6")

                if visits >= 6:

                    sheet.update_cell(i, 7, int(row["free_hookah"]) + 1)

                    await bot.send_message(
                        int(user_id),
                        "🔥 Поздравляем!\n\n"
                        "Ты получил бесплатный кальян 🎁"
                    )

                return

        await message.answer("❌ Пользователь не найден")

    except Exception as e:
        await message.answer("❌ Ошибка команды")
        print(e)

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
