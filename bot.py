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

from aiohttp import web

# ======================
# LOGGING
# ======================

logging.basicConfig(level=logging.INFO)

# ======================
# ENV
# ======================

TOKEN = os.environ["TOKEN"]
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

PORT = int(os.environ.get("PORT", 10000))

# ======================
# BOT
# ======================

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

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
# HANDLERS
# ======================

@dp.message_handler(commands=["start"])
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await Form.name.set()
    await message.answer("💨 DIA.MIST\n\nНапиши своё имя 👇", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=Form.name)
async def name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await Form.phone.set()
    await message.answer("📱 Отправь номер", reply_markup=phone_kb)

@dp.message_handler(content_types=types.ContentTypes.CONTACT, state=Form.phone)
async def phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await Form.birthday.set()
    await message.answer("🎂 Дата рождения (ДД.ММ.ГГГГ)", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=Form.birthday)
async def birthday(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")

        data = await state.get_data()

        sheet.append_row([
            message.from_user.id,
            message.from_user.username or "",
            data["name"],
            data["phone"],
            message.text,
            1,
            0,
            datetime.now().strftime("%d.%m.%Y %H:%M")
        ])

        await state.finish()
        await message.answer("🎉 Готово!", reply_markup=main_kb)

    except:
        await message.answer("❌ Формат: ДД.ММ.ГГГГ")

@dp.message_handler(lambda m: m.text == "🎁 Акции")
async def promo(message: types.Message):
    await message.answer("🔥 7-й кальян бесплатно 🎁")

@dp.message_handler(lambda m: m.text == "⭐ Мои кальяны")
async def stats(message: types.Message):
    records = sheet.get_all_records()

    for r in records:
        if str(r["telegram_id"]) == str(message.from_user.id):
            count = int(r.get("hookah_count", 0))
            await message.answer(f"⭐ Кальяны: {count}")
            return

    await message.answer("Нет данных")

# ======================
# WEB SERVER (ВАЖНО ДЛЯ RENDER)
# ======================

async def health(request):
    return web.Response(text="OK")

app = web.Application()
app.router.add_get("/", health)

def run_web():
    web.run_app(app, host="0.0.0.0", port=PORT)

# ======================
# RUN BOTH (WEB + BOT)
# ======================

if __name__ == "__main__":
    import threading

    threading.Thread(target=run_web).start()

    executor.start_polling(dp, skip_updates=True)
