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

    # Ждём контакт, текст игнорируем

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
            "⭐ Посещений: 0\n"
            "🎁 Бесплатных кальянов: 0\n\n"
            "Следи за акциями и розыгрышами в нашем канале 🔥",
            reply_markup=ReplyKeyboardRemove()
        )

        user_data.pop(user_id)
