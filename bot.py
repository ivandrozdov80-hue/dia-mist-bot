import os
import json
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

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

WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST")  # https://your-domain.com
WEBHOOK_PATH = os.environ.get("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", 8000))

# ======================
# BOT INIT
# ======================

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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
# KEYBOARDS
# ======================

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(KeyboardButton("📱 Отправить номер", request_contact=True))

main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.row("🎁 Акции", "⭐ Мои посещения")

# ======================
# FSM STATES
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
    await message.answer("💨 DIA.MIST\n\nНапиши своё имя 👇", reply_markup=ReplyKeyboardRemove())

# ======================
# NAME
# ======================

@dp.message_handler(state=Form.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    await Form.phone.set()
    await message.answer(
        "📱 Отправь номер телефона",
        reply_markup=phone_keyboard
    )

# ======================
# PHONE (contact)
# ======================

@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=Form.phone)
async def get_contact(message: types.Message, state: FSMContext):

    if not message.contact:
        await message.answer("Нажми кнопку, чтобы отправить номер")
        return

    await state.update_data(phone=message.contact.phone_number)

    await Form.birthday.set()
    await message.answer(
        "🎂 Введи дату рождения (ДД.ММ.ГГГГ)",
        reply_markup=ReplyKeyboardRemove()
    )

# ======================
# PHONE fallback text
# ======================

@dp.message_handler(state=Form.phone)
async def phone_fallback(message: types.Message):
    await message.answer("Нажми кнопку 📱 'Отправить номер'")

# ======================
# BIRTHDAY
# ======================

@dp.message_handler(state=Form.birthday)
async def get_birthday(message: types.Message, state: FSMContext):

    # validate date
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
    except ValueError:
        await message.answer("❌ Формат: ДД.ММ.ГГГГ (например 25.12.2000)")
        return

    data = await state.get_data()

    try:
        sheet.append_row([
            message.from_user.id,
            message.from_user.username or "",
            data["name"],
            data["phone"],
            message.text,
            0,
            0,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ])
    except Exception as e:
        logging.error(f"Sheets error: {e}")
        await message.answer("❌ Ошибка сохранения. Попробуй позже")
        await state.finish()
        return

    await message.answer(
        "🎉 Готово! Ты зарегистрирован",
        reply_markup=main_menu
    )

    await state.finish()

# ======================
# WEBHOOK STARTUP
# ======================

async def on_startup(dp):
    logging.info("Setting webhook...")
    await bot.set_webhook(WEBHOOK_URL)

# ======================
# SHUTDOWN
# ======================

async def on_shutdown(dp):
    logging.info("Deleting webhook...")
    await bot.delete_webhook()

# ======================
# RUN WEBHOOK SERVER
# ======================

if __name__ == "__main__":
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
