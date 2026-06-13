from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

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
# KEYBOARD
# ======================

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(KeyboardButton("📱 Поделиться номером", request_contact=True))

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("🎁 Акции", "🏆 Розыгрыш")
main_menu.row("⭐ Мои посещения", "📍 Контакты")

# ======================
# START (QR + REGISTRATION)
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id
    args = message.get_args()

    user_data.setdefault(user_id, {
        "telegram_id": user_id,
        "username": message.from_user.username
    })

    # ================= QR VISIT =================
    if args and args.startswith("visit_"):

        target_id = args.replace("visit_", "")

        data = sheet.get_all_records()

        for i, row in enumerate(data, start=2):

            if str(row.get("telegram_id")) == str(target_id):

                visits = int(row.get("visits", 0)) + 1
                sheet.update_cell(i, 6, visits)

                if visits >= 6:
                    sheet.update_cell(i, 7, int(row.get("free_hookah", 0)) + 1)

                    await bot.send_message(
                        target_id,
                        "🔥 Поздравляем!\n\nТы получил бесплатный кальян 🎁"
                    )

                await message.answer(f"⭐ Визит засчитан: {visits}/6")
                return

        await message.answer("❌ Пользователь не найден")
        return

    # ================= NORMAL START =================
    await message.answer(
        "💨 Добро пожаловать в DIA.MIST!\n\n"
        "🎁 Розыгрыши и бонусы\n"
        "⭐ Копи посещения (6 = кальян)\n\n"
        "Напиши своё имя 👇"
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
        "🎂 Когда день рождения?\n\nНапример: 15.08",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================
# REGISTRATION
# ======================

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def text_handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        return

    data = user_data[user_id]

    if "name" not in data:
        data["name"] = message.text

        await message.answer(
            "📱 Отправь номер телефона",
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
            "🎉 Готово!\n\nТы в системе DIA.MIST 🔥",
            reply_markup=main_menu
        )

        user_data.pop(user_id)

# ======================
# MENU
# ======================

@dp.message_handler(lambda m: m.text == "🎁 Акции")
async def promo(m):
    await m.answer("🔥 Акция недели...")

@dp.message_handler(lambda m: m.text == "🏆 Розыгрыш")
async def give(m):
    await m.answer("🏆 Розыгрыш каждую неделю")

@dp.message_handler(lambda m: m.text == "⭐ Мои посещения")
async def visits(m):

    user_id = m.from_user.id

    data = sheet.get_all_records()

    for row in data:
        if str(row["telegram_id"]) == str(user_id):

            v = int(row["visits"])
            await m.answer(f"⭐ {v}/6")
            return

    await m.answer("Нет данных")

@dp.message_handler(lambda m: m.text == "📍 Контакты")
async def contacts(m):
    await m.answer("📍 DIA.MIST")

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
