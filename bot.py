from aiogram import Bot, Dispatcher, types, executor
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import os
from aiogram import Bot

import os

TOKEN = os.environ["TOKEN"]

bot = Bot(token=TOKEN)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

import os
import json
from oauth2client.service_account import ServiceAccountCredentials

creds_dict = json.loads(os.environ["GOOGLE_CREDS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open("DIA.MIST CRM").sheet1

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

user_data = {}

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Как тебя зовут?")
    user_data[message.from_user.id] = {}

@dp.message_handler()
async def handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {}

    data = user_data[user_id]

    if "name" not in data:
        data["name"] = message.text
        await message.answer("Отправь номер телефона")
    
    elif "phone" not in data:
        data["phone"] = message.text
        await message.answer("Когда у тебя день рождения? (дд.мм)")

    elif "birthday" not in data:
        data["birthday"] = message.text

        # Save to Google Sheets
        sheet.append_row([
            data["name"],
            data["phone"],
            data["birthday"]
        ])

        await message.answer("Готово! Ты добавлен в DIA.MIST Club 🔥")

        user_data.pop(user_id)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
