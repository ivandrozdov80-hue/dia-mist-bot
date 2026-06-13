from aiogram import Bot, Dispatcher, types, executor
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# Telegram Bot
TOKEN = os.environ["TOKEN"]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Google Sheets
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

# Temporary user storage
user_data = {}


@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    user_id = message.from_user.id

    user_data[user_id] = {
        "telegram_id": user_id,
        "username": message.from_user.username
    }

    await message.answer(
        "💨 Добро пожаловать в DIA.MIST Club!\n\n"
        "🎁 Участвуй в розыгрышах\n"
        "⭐ Копи посещения\n"
        "🔥 Получай бонусы и подарки\n"
        "🎂 Получай подарок на день рождения\n\n"
        "Для участия напиши своё имя 👇"
    )


@dp.message_handler()
async def handler(message: types.Message):

    user_id = message.from_user.id

    if user_id not in user_data:
        user_data[user_id] = {
            "telegram_id": user_id,
            "username": message.from_user.username
        }

    data = user_data[user_id]

    # Имя
    if "name" not in data:
        data["name"] = message.text
        await message.answer(
            "📱 Отправь номер телефона"
        )

    # Телефон
    elif "phone" not in data:
        data["phone"] = message.text
        await message.answer(
            "🎂 Когда у тебя день рождения?\n\n"
            "Например: 15.08"
        )

    # День рождения
    elif "birthday" not in data:

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
            "⭐ Посещений: 0\n"
            "🎁 Бесплатных кальянов: 0\n\n"
            "Следи за акциями и розыгрышами в нашем канале 🔥"
        )

        user_data.pop(user_id)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
