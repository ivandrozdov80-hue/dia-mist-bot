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
# FLASK (FIX FOR RENDER)
# ======================
from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "DIA.MIST bot is running"

def run_web():
    app.run(host="0.0.0.0", port=10000)

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

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

phone_button = KeyboardButton(
    text="📱 Поделиться номером",
    request_contact=True
)

phone_keyboard.add(phone_button)

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)

main_menu.row("🎁 Акции", "🏆 Розыгрыш недели")
main_menu.row("⭐ Мои посещения", "📍 Контакты")

# ======================
# START (QR + REGISTRATION)
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id
    args = message.get_args()

    # если человек уже есть в памяти
    user_data.setdefault(user_id, {
        "telegram_id": user_id,
        "username": message.from_user.username
    })

    # ======================
    # QR VISIT MODE
    # ======================
    if args and args.startswith("visit_"):

        target_id = args.replace("visit_", "")

        data = sheet.get_all_records()

        for i, row in enumerate(data, start=2):

            if str(row.get("telegram_id")) == str(target_id):

                visits = int(row.get("visits", 0)) + 1

                sheet.update_cell(i, 6, visits)

                # бонус
                if visits >= 6:

                    sheet.update_cell(i, 7, int(row.get("free_hookah", 0)) + 1)

                    await bot.send_message(
                        target_id,
                        "🔥 Поздравляем!\n\n"
                        "Ты получил бесплатный кальян 🎁"
                    )

                await message.answer(
                    f"⭐ Визит засчитан!\n"
                    f"Всего: {visits}/6"
                )

                return

        await message.answer("❌ Пользователь не найден")
        return

    # ======================
    # NORMAL START
    # ======================
    await message.answer(
        "💨 Приветствую тебя в DIA.MIST!\n\n"
        "🎁 Участвуй в розыгрышах\n"
        "⭐ Копи посещения (6 = бесплатный кальян)\n"
        "🔥 Бонусы и подарки\n\n"
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
# REGISTRATION FLOW
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    # name
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
            0,
            0,
            reg_date
        ])

        await message.answer(
            "🎉 Регистрация завершена!\n\n"
            "Теперь копи посещения и получай бонусы 🔥",
            reply_markup=main_menu
        )

        user_data.pop(user_id)

# ======================
# MENU
# ======================

@dp.message_handler(lambda message: message.text == "🎁 Акции")
async def promotions(message: types.Message):
    await message.answer("🔥 АКЦИЯ НЕДЕЛИ\n\n2 кальяна = чай бесплатно ☕")

@dp.message_handler(lambda message: message.text == "🏆 Розыгрыш недели")
async def giveaway(message: types.Message):
    await message.answer("🏆 РОЗЫГРЫШ НЕДЕЛИ\n\nБесплатный кальян каждую неделю 🔥")

@dp.message_handler(lambda message: message.text == "⭐ Мои посещения")
async def visits(message: types.Message):

    user_id = message.from_user.id

    data = sheet.get_all_records()

    for row in data:
        if str(row["telegram_id"]) == str(user_id):

            v = int(row["visits"])

            await message.answer(
                f"⭐ Твои посещения: {v}/6\n"
                f"До бесплатного кальяна: {6 - v}"
            )
            return

    await message.answer("Ты ещё не зарегистрирован.")

@dp.message_handler(lambda message: message.text == "📍 Контакты")
async def contacts(message: types.Message):
    await message.answer("📍 DIA.MIST\n\n🕐 12:00–23:00")

# ======================
# RUN
# ======================

if __name__ == "__main__":

    threading.Thread(target=run_web).start()
    executor.start_polling(dp, skip_updates=True)
