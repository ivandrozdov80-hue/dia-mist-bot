import os
import json
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================
# LOGGING
# ======================

logging.basicConfig(level=logging.INFO)

# ======================
# ENV
# ======================

TOKEN = os.environ["TOKEN"]

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "").strip()
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")

if not WEBHOOK_HOST.startswith("https://"):
    raise ValueError("WEBHOOK_HOST must start with https://")

WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# ======================
# BOT
# ======================

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ======================
# SHEETS
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
# KEYBOARDS
# ======================

phone_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_kb.add(KeyboardButton("📱 Отправить номер", request_contact=True))

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.row("🎁 Акции", "⭐ Мои кальяны")

# ======================
# FSM
# ======================

class Form(StatesGroup):
    name = State()
    phone = State()
    birthday = State()

# ======================
# START
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await Form.name.set()
    await message.answer(
        "💨 DIA.MIST\n\nНапиши своё имя 👇",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================
# NAME
# ======================

@dp.message_handler(state=Form.name)
async def name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Form.phone.set()

    await message.answer("📱 Отправь номер", reply_markup=phone_kb)

# ======================
# PHONE
# ======================

@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=Form.phone)
async def phone(message: types.Message, state: FSMContext):

    if not message.contact:
        await message.answer("Нажми кнопку 📱")
        return

    await state.update_data(phone=message.contact.phone_number)
    await Form.birthday.set()

    await message.answer("🎂 Дата рождения (ДД.ММ.ГГГГ)", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=Form.phone)
async def phone_fallback(message: types.Message):
    await message.answer("Используй кнопку 📱")

# ======================
# BIRTHDAY + SAVE
# ======================

@dp.message_handler(state=Form.birthday)
async def birthday(message: types.Message, state: FSMContext):

    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Формат: ДД.ММ.ГГГГ")
        return

    data = await state.get_data()

    try:
        sheet.append_row([
            message.from_user.id,
            message.from_user.username or "",
            data["name"],
            data["phone"],
            message.text,
            1,   # hookah_count
            0,   # bonus_used
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ])
    except Exception as e:
        logging.error(e)
        await message.answer("❌ Ошибка базы данных")
        await state.finish()
        return

    await state.finish()
    await message.answer("🎉 Готово! Добро пожаловать", reply_markup=main_kb)

# ======================
# 🔥 АКЦИИ
# ======================

@dp.message_handler(lambda m: m.text == "🎁 Акции", state="*")
async def promo(message: types.Message):
    await message.answer(
        "🔥 АКЦИЯ КАЛЬЯННОЙ\n\n"
        "7-й кальян — БЕСПЛАТНО 🎁"
    )

# ======================
# ⭐ КАЛЬЯНЫ
# ======================

@dp.message_handler(lambda m: m.text == "⭐ Мои кальяны", state="*")
async def my_hookahs(message: types.Message):

    records = sheet.get_all_records()

    for r in records:
        if str(r["telegram_id"]) == str(message.from_user.id):

            count = int(r.get("hookah_count", 0))
            remaining = 7 - (count % 7)

            await message.answer(
                f"⭐ Кальяны: {count}\n"
                f"🎯 До бонуса: {remaining}"
            )
            return

    await message.answer("У тебя пока нет посещений")

# ======================
# ➕ АДМИН
# ======================

@dp.message_handler(commands=["addhookah"])
async def add_hookah(message: types.Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        _, user_id = message.text.split()
    except:
        await message.answer("Формат: /addhookah ID")
        return

    records = sheet.get_all_records()

    for i, r in enumerate(records, start=2):

        if str(r["telegram_id"]) == str(user_id):

            count = int(r.get("hookah_count", 0)) + 1
            sheet.update_cell(i, 6, count)

            await message.answer("✔ Добавлено")

            if count % 7 == 0:
                await bot.send_message(user_id, "🎉 БЕСПЛАТНЫЙ КАЛЬЯН!")

            return

    await message.answer("Не найден")

# ======================
# WEBHOOK
# ======================

async def on_startup(dp):
    logging.info(f"Webhook: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

# ======================
# RUN
# ======================

if __name__ == "__main__":
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
