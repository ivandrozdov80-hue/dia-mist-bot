from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# ======================
# BOT
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
phone_keyboard.add(KeyboardButton("📱 Поделиться номером", request_contact=True))

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("🎁 Акции", "🏆 Розыгрыш")
main_menu.row("⭐ Мои посещения", "📍 Контакты")

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
        "💨 DIA.MIST\n\n"
        "Напиши своё имя 👇"
    )

# ======================
# CONTACT
# ======================

@dp.message_handler(content_types=['contact'])
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
# REGISTRATION
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def register(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if "name" not in data:
        data["name"] = message.text
        await message.answer("📱 Отправь номер телефона", reply_markup=phone_keyboard)
        return

    if "phone" not in data:
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
            0,   # visits
            0,   # free_hookah
            reg
        ])

        await message.answer("🔥 Ты зарегистрирован!", reply_markup=main_menu)
        user_data.pop(user_id)

# ======================
# VISIT SYSTEM (FIXED)
# ======================

@dp.message_handler(lambda message: message.text and message.text.startswith("/visit"))
async def visit(message: types.Message):

    target_id = None

    # reply
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id

    # /visit 123
    else:
        parts = message.text.split()
        if len(parts) > 1:
            target_id = parts[1]

    if not target_id:
        await message.answer("❌ Нет пользователя")
        return

    data = sheet.get_all_records()

    for i, row in enumerate(data, start=2):

        if str(row.get("telegram_id")) == str(target_id):

            visits = int(row.get("visits", 0)) + 1
            free = int(row.get("free_hookah", 0))

            sheet.update_cell(i, 6, visits)
            sheet.update_cell(i, 7, free)

            msg = f"⭐ +1 визит → {visits}/6"

            if visits % 6 == 0:
                free += 1
                sheet.update_cell(i, 7, free)

                msg += "\n\n🔥 БОНУС: бесплатный кальян!"

                await bot.send_message(
                    target_id,
                    "🔥 Ты получил бесплатный кальян 🎁"
                )

            await message.answer(msg)
            return

    await message.answer("❌ Пользователь не найден")

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
