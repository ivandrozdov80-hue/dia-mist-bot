@dp.message_handler(lambda message: message.text and message.text.startswith("/visit"))
async def add_visit(message: types.Message):

    # ===== ADMIN CHECK (можешь потом ограничить) =====
    # пока без защиты

    target_username = None

    # 1. если ответ на сообщение
    if message.reply_to_message:
        target_username = message.reply_to_message.from_user.username

    # 2. если через @username
    else:
        parts = message.text.split()
        if len(parts) > 1:
            target_username = parts[1].replace("@", "")

    if not target_username:
        await message.answer("❌ Укажи пользователя (/visit @name или ответом)")
        return

    data = sheet.get_all_records()

    for i, row in enumerate(data, start=2):

        if str(row.get("username")) == str(target_username):

            visits = int(row.get("visits", 0)) + 1
            free = int(row.get("free_hookah", 0))

            sheet.update_cell(i, 6, visits)  # visits column
            sheet.update_cell(i, 7, free)

            msg = f"⭐ +1 визит\nВсего: {visits}"

            # каждые 6 визитов
            if visits % 6 == 0:
                free += 1
                sheet.update_cell(i, 7, free)

                msg += "\n\n🔥 БОНУС: бесплатный кальян!"

                await bot.send_message(
                    row.get("telegram_id"),
                    "🔥 Поздравляем! Ты получил бесплатный кальян 🎁"
                )

            await message.answer(msg)
            return

    await message.answer("❌ Пользователь не найден")
