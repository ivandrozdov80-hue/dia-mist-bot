# handlers.py (корневой файл)
import random
import re
from datetime import datetime
from config import logger, ADMIN_IDS, LEVELS, LEVEL_NAMES
import database as db
import google_sheets as gs
import keyboards as kb
import utils
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

from handlers_modules.profile import handle_profile
from handlers_modules.visits import (
    handle_visit_button,
    handle_visit_request,
    handle_visit_manual,
    handle_admin_confirm,
    handle_admin_reject
)
from handlers_modules.raffle import handle_raffle_info, handle_raffle_participate
from handlers_modules.admin import (
    handle_admin_newvisit,
    handle_admin_command,
    handle_admin_create_raffle,
    handle_admin_draw,
    handle_status,
    handle_stat,
    handle_delete_guest,
    delete_guest,
    list_guests,
    clear_cache,
    restore_guests
)
from handlers_modules.greetings import handle_greeting, handle_emoji_short, handle_random_joke, handle_sticker
from handlers_modules.promo import handle_promo
from handlers_modules.help import handle_help
from handlers_modules.utils import update_command_count, update_raffle_participation
from handlers_modules.reviews import handle_review_response


def send_message(vk, user_id, text, attachment=None, keyboard=None):
    try:
        vk.messages.send(
            user_id=user_id,
            message=text,
            random_id=random.randint(1, 2**31),
            attachment=attachment,
            keyboard=keyboard.get_keyboard() if keyboard else None
        )
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")


def handle_main_menu(vk, user_id, guest, message, send_func):
    low_msg = message.lower()

    logger.info(f"🔍 handle_main_menu: user={user_id}, message='{message}'")

    # ===== ПРИВЕТСТВИЯ =====
    if handle_greeting(user_id, message, send_func):
        return True

    # ===== СМАЙЛИКИ =====
    if handle_emoji_short(user_id, message, send_func):
        return True

    # ===== ОТЗЫВЫ =====
    if handle_review_response(vk, user_id, guest, message, send_func):
        return True

    # ============================================================
    # АДМИН-МЕНЮ (кнопка)
    # ============================================================
    if message == '📊 Админ-меню' and user_id in ADMIN_IDS:
        send_func(
            user_id,
            "👑 **АДМИН-МЕНЮ**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "📨 Рассылка – отправить сообщение всем гостям\n"
            "📊 Статистика – бизнес-показатели\n"
            "🔍 Статус – состояние бота\n"
            "👥 Все гости – список ID гостей\n\n"
            "Выбери действие:",
            keyboard=kb.get_admin_menu_keyboard()
        )
        return True

    # ===== КНОПКА "НАЗАД" (из админ-меню) =====
    if message == '🔙 Назад' and user_id in ADMIN_IDS:
        send_func(
            user_id,
            "Главное меню:",
            keyboard=kb.get_main_keyboard(user_id)
        )
        return True

    # ===== РАССЫЛКА (кнопка) =====
    if message == '📨 Рассылка' and user_id in ADMIN_IDS:
        send_func(
            user_id,
            "✍️ Напиши текст для рассылки:\n"
            "/notify Текст сообщения\n\n"
            "Например:\n"
            "/notify У нас поступление новых табаков!"
        )
        return True

    # ===== СТАТИСТИКА (кнопка) =====
    if message == '📊 Статистика' and user_id in ADMIN_IDS:
        handle_stat(vk, user_id, send_func)
        return True

    # ===== СТАТУС (кнопка) =====
    if message == '🔍 Статус' and user_id in ADMIN_IDS:
        handle_status(vk, user_id, send_func)
        return True

    # ===== ВСЕ ГОСТИ (кнопка) =====
    if message == '👥 Все гости' and user_id in ADMIN_IDS:
        db.cursor.execute("SELECT vk_id, name, phone FROM guests ORDER BY vk_id DESC LIMIT 50")
        rows = db.cursor.fetchall()
        if rows:
            text = "👥 **ПОСЛЕДНИЕ ГОСТИ (50):**\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            for row in rows:
                text += f"ID: {row[0]} | {row[1]} | {row[2] or 'нет телефона'}\n"
            send_func(user_id, text, keyboard=kb.get_admin_menu_keyboard())
        else:
            send_func(user_id, "Нет гостей.", keyboard=kb.get_admin_menu_keyboard())
        return True

    # ============================================================
    # АДМИН-КОМАНДЫ (через текст)
    # ============================================================
    if user_id in ADMIN_IDS:
        if low_msg == '/status':
            handle_status(vk, user_id, send_func)
            return True
        if low_msg == '/stat':
            handle_stat(vk, user_id, send_func)
            return True

    # ============================================================
    # КОМАНДА /visit (ручной ввод кода)
    # ============================================================
    if low_msg.startswith('/visit'):
        return handle_visit_manual(vk, user_id, guest, message, send_func)

    # ============================================================
    # ЗАЯВКА НА ВИЗИТ (текст)
    # ============================================================
    if 'визит' in low_msg or 'заявка' in low_msg:
        logger.info(f"✅ Заявка на визит от {user_id}, текст: '{message}'")
        return handle_visit_request(vk, user_id, guest, message, send_func)

    # ============================================================
    # КНОПКИ АДМИНИСТРАТОРА (подтверждение/отклонение визита)
    # ============================================================
    if message.startswith('✅ Подтвердить ') or message.startswith('✅ подтвердить '):
        return handle_admin_confirm(vk, user_id, message, send_func)

    if message.startswith('❌ Отклонить ') or message.startswith('❌ отклонить '):
        return handle_admin_reject(vk, user_id, message, send_func)

    # ============================================================
    # КНОПКА "НАЗАД" (для всех)
    # ============================================================
    if message == '🔙 Назад':
        send_func(user_id, "Главное меню:", keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # УЧАСТИЕ В РОЗЫГРЫШЕ
    # ============================================================
    if message == '✅ Участвую':
        return handle_raffle_participate(user_id, send_func)

    if message == '✅ Вы уже участвуете':
        send_func(user_id, "Ты уже в списке участников! Жди розыгрыша в воскресенье.", keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # АКЦИИ
    # ============================================================
    if message == '🔥 Акции' or low_msg == '/promo':
        handle_promo(user_id, send_func)
        return True

    # ============================================================
    # КОМАНДА /birth
    # ============================================================
    if low_msg.startswith('/birth '):
        birth = message[7:].strip()
        if re.match(r'^\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})$', birth):
            db.cursor.execute(
                "UPDATE guests SET birth=?, registration_step=3 WHERE vk_id=?",
                (birth, user_id)
            )
            db.conn.commit()
            gs.update_guest_sheet(user_id, birth=birth, registration_step=3)
            send_func(
                user_id,
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎂 ДЕНЬ РОЖДЕНИЯ СОХРАНЁН!\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Отлично! Записал: {birth}\n"
                f"Теперь подарок точно найдёт своего хозяина! 😎\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
                keyboard=kb.get_main_keyboard(user_id)
            )
        else:
            send_func(
                user_id,
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "❌ НЕВЕРНЫЙ ФОРМАТ\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Формат даты: ДД.ММ.ГГГГ\n"
                "Например: /birth 15.05.1999\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                keyboard=kb.get_main_keyboard(user_id)
            )
        return True

    # ============================================================
    # ПРОФИЛЬ
    # ============================================================
    if message == '👤 Профиль' or low_msg == '/profile':
        handle_profile(vk, user_id, guest, send_func)
        return True

    # ============================================================
    # РОЗЫГРЫШ
    # ============================================================
    if message == '🎁 Розыгрыш' or low_msg == '/raffle':
        handle_raffle_info(user_id, guest, send_func)
        return True

    # ============================================================
    # УРОВНИ (команда /levelinfo)
    # ============================================================
    if low_msg == '/levelinfo':
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🏅 ТАБЛИЦА УРОВНЕЙ",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        for lvl, need in sorted(LEVELS.items(), key=lambda x: x[1]):
            lines.append(f"   {LEVEL_NAMES[lvl]} – {need} визитов")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        send_func(user_id, "\n".join(lines), keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # АДМИН-КОМАНДЫ (через /)
    # ============================================================
    if low_msg.startswith('/newvisit') and user_id in ADMIN_IDS:
        handle_admin_newvisit(vk, user_id, message, send_func)
        return True

    if low_msg.startswith('/create_raffle') and user_id in ADMIN_IDS:
        handle_admin_create_raffle(vk, user_id, message, send_func)
        return True

    if low_msg == '/draw' and user_id in ADMIN_IDS:
        handle_admin_draw(vk, user_id, send_func)
        return True

    if low_msg.startswith('/delete_guest') and user_id in ADMIN_IDS:
        handle_delete_guest(vk, user_id, message, send_func)
        return True

    # ============================================================
    # МАССОВАЯ РАССЫЛКА (/notify)
    # ============================================================
    if low_msg.startswith('/notify') and user_id in ADMIN_IDS:
        parts = message.split(maxsplit=1)
        if len(parts) < 2:
            send_func(
                user_id,
                "❌ Напиши текст для рассылки:\n"
                "/notify Текст сообщения"
            )
            return True
        
        text = parts[1].strip()
        if len(text) < 5:
            send_func(user_id, "❌ Текст слишком короткий (минимум 5 символов).")
            return True

        signature = (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📨 Это сообщение от Джинна Dia Mist\n"
            "📞 По всем вопросам звоните: +7 909 727 68 37\n"
            "✍️ Или напишите создателю: https://vk.com/im?sel=57703251"
        )

        db.cursor.execute("SELECT vk_id FROM guests")
        rows = db.cursor.fetchall()
        total = len(rows)

        if total == 0:
            send_func(user_id, "❌ Нет зарегистрированных гостей.")
            return True

        send_func(
            user_id,
            f"🔄 Начинаю рассылку для {total} гостей...\n"
            f"Текст: {text[:50]}..."
        )

        import time
        success = 0
        failed = 0

        for vk_id, in rows:
            try:
                send_func(vk_id, text + signature)
                success += 1
                time.sleep(0.3)
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка отправки гостю {vk_id}: {e}")

        send_func(
            user_id,
            f"✅ Рассылка завершена!\n"
            f"✅ Успешно: {success}\n"
            f"❌ Ошибок: {failed}\n"
            f"👥 Всего гостей: {total}"
        )
        return True

    # ============================================================
    # КНОПКА "ТВОЙ МАСТЕР"
    # ============================================================
    if message == '🤵 Твой Мастер' or low_msg == '/book':
        name, phone = gs.get_today_master()
        responses = [
            "Сегодня разжигает угли так, что даже ад позавидует. 😈\nТяга будет мощнее, чем твоё желание уйти домой.\nНо лучше позвони, чтобы он не разжёг всё без тебя. 🔥",
            "Знает о вкусах больше, чем ты о своих бывших. 😏\nОн смешает тебе такой дым, что ты забудешь, как выглядит свежий воздух.\nПозвони, пока он не смешал себя с другим гостем. 💨",
            "Умеет делать кальян так, что ты почувствуешь себя героем фильма. 🎬\nНу, или хотя бы злодеем, который знает, чего хочет.\nЗвони, пока он не начал настраивать кальян для кого-то другого. 😎",
            "Сегодня выдаёт такие секреты дыма, что даже облака завидуют. ☁️\nТы выйдешь отсюда с чувством, что побывал в другой атмосфере.\nНо сначала позвони – ему нужно подготовиться к твоему величию. ⚡",
            "Подходит к каждому гостью как к уникальному эксперименту. 🧪\nОн сделает так, что ты вернёшься ещё, даже если не хочешь признаваться.\nПозвони, пока он не начал экспериментировать без тебя. 🔥"
        ]
        chosen_text = random.choice(responses)
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🤵 ТВОЙ МАСТЕР\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🧑‍💼 {name}\n\n"
            f"{chosen_text}\n\n"
            f"📱 Номер для брони:\n   {phone}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_func(user_id, text, keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # КНОПКА "СОЗДАТЕЛЬ"
    # ============================================================
    if message == '✍️ Создатель':
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✍️ СВЯЗЬ С СОЗДАТЕЛЕМ\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🧞 Хочешь задать вопрос лично?\n"
            "Это отличная идея! 😊\n\n"
            "👉 Напиши мне напрямую в личные сообщения:\n"
            "https://vk.com/im?sel=57703251\n\n"
            "Или звони по телефону:\n"
            "+7 909 727 68 37\n\n"
            "Я всегда на связи! 📱\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_func(user_id, text, keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # ПОМОЩЬ
    # ============================================================
    if message == '❓ Помощь' or low_msg == '/help':
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🧞 ДЖИНН ПОМОЩНИК\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Привет, мой друг! 👋\n"
            "Я – Джинн Dia Mist, твой проводник в мире дыма\n"
            "и хорошего настроения.\n\n"
            "🔹 Главное меню – это кнопки внизу экрана.\n"
            "   Нажимай на них, чтобы управлять ботом.\n\n"
            "🔹 Продвинутые команды:\n"
            "   /profile – посмотреть свой профиль\n"
            "   /visit КОД – подтвердить визит\n"
            "   /book – узнать мастера\n"
            "   /levelinfo – таблица уровней\n"
            "   /raffle – розыгрыш\n"
            "   /promo – акции\n"
            "   /birth ДД.ММ.ГГГГ – указать дату рождения\n\n"
            "👑 Администратору:\n"
            "   /newvisit [id], /create_raffle, /draw\n"
            "   /status, /stat, /notify, /delete_guest [id]\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Теперь ты знаешь всё! Жми на кнопки\n"
            "и наслаждайся! 🧞💨\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_func(user_id, text, keyboard=kb.get_main_keyboard(user_id))
        return True

    # ============================================================
    # СЛУЧАЙНАЯ ШУТКА
    # ============================================================
    if handle_random_joke(user_id, send_func):
        return True

    return False


__all__ = [
    'send_message',
    'handle_main_menu',
    'handle_sticker',
    'update_command_count',
    'update_raffle_participation'
]