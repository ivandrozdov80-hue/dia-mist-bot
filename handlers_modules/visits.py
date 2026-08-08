# handlers_modules/visits.py
import re
from datetime import datetime
import database as db
import google_sheets as gs
import keyboards as kb
import utils
from config import ADMIN_IDS, logger, VISIT_REQUEST_COOLDOWN
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from .utils import update_command_count
from .reviews import ask_review

def handle_visit_button(vk, user_id, guest, send_func):
    update_command_count(user_id, 'button_visit')
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📅 ПОДТВЕРЖДЕНИЕ ВИЗИТА\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Жди, когда администратор отправит тебе\n"
        "приглашение подтвердить визит.\n\n"
        "Я, Джинн, прослежу, чтобы это было быстро! 😉\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_func(user_id, text, keyboard=kb.get_main_keyboard())

def handle_visit_request(vk, user_id, guest, message, send_func):
    update_command_count(user_id, 'button_visit')
    now = datetime.now()
    if int(guest[9]) < 3:
        send_func(user_id, "Сначала зарегистрируйся! Напиши /help, чтобы начать.", keyboard=kb.get_main_keyboard())
        return True
    last_request = db.get_last_request_time(user_id)
    if last_request:
        try:
            last_time = datetime.fromisoformat(last_request)
            if (now - last_time).total_seconds() < VISIT_REQUEST_COOLDOWN:
                send_func(user_id, f"Ты уже отправлял заявку недавно. Подожди {VISIT_REQUEST_COOLDOWN//60} минут.", keyboard=kb.get_main_keyboard())
                return True
        except:
            pass
    db.update_last_request_time(user_id)
    for admin_id in ADMIN_IDS:
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button(f'✅ Подтвердить {user_id}', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button(f'❌ Отклонить {user_id}', color=VkKeyboardColor.SECONDARY)
        send_func(
            admin_id,
            f"🆕 Новая заявка на визит!\n"
            f"Гость: {guest[1]} (ID: {user_id})\n"
            f"Время: {now.strftime('%H:%M')}\n"
            f"Нажмите «Подтвердить», чтобы засчитать визит.",
            keyboard=keyboard
        )
    send_func(user_id, "✅ Заявка отправлена администратору. Ожидайте подтверждения.", keyboard=kb.get_main_keyboard())
    return True

def handle_visit_manual(vk, user_id, guest, message, send_func):
    update_command_count(user_id, 'visit_manual')
    parts = message.split()
    if len(parts) != 2:
        send_func(user_id, "❌ Напиши: /visit КОД", keyboard=kb.get_main_keyboard())
        return True
    code_str = parts[1]
    if not code_str.isdigit():
        send_func(user_id, "❌ Код – только цифры", keyboard=kb.get_main_keyboard())
        return True
    code = int(code_str)
    result = utils.apply_visit(user_id, code, send_func)
    if result:
        new_visits, new_level, level_name, ach_count, promo_line, reached_six, free_used = result
        if free_used:
            report = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎉 ЭТОТ ВИЗИТ – БЕСПЛАТНЫЙ!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Ты использовал свой бонус.\n"
                "Счётчик акции обнулён.\n\n"
                f"🌀 Всего визитов: {new_visits}\n"
                f"🏅 Уровень: {level_name}\n"
                "🔥 Следующий бесплатный кальян: 0/6 визитов\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
        else:
            report = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ ВИЗИТ ЗАСЧИТАН!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🌀 Всего визитов: {new_visits}\n"
                f"🏅 Уровень: {level_name}\n"
                f"{promo_line}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            if reached_six:
                report += (
                    "\n\n🎉 ПОЗДРАВЛЯЮ!\n"
                    "Ты накопил на бесплатный кальян!\n"
                    "Следующий визит за наш счёт!"
                )
        send_func(user_id, report, keyboard=kb.get_main_keyboard())
        # Предложить отзыв
        db.set_awaiting_review(user_id, True)
        ask_review(vk, user_id, send_func)
    else:
        send_func(user_id, "❌ Ошибка при засчитывании визита.", keyboard=kb.get_main_keyboard())
    return True

def handle_admin_confirm(vk, user_id, message, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return True
    match = re.search(r'\d+', message)
    if not match:
        send_func(user_id, "Ошибка: не могу определить гостя.")
        return True
    target_id = int(match.group())
    result = utils.apply_visit(target_id, send_message_func=send_func)
    if result:
        new_visits, new_level, level_name, ach_count, promo_line, reached_six, free_used = result
        if free_used:
            report = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎉 ЭТОТ ВИЗИТ – БЕСПЛАТНЫЙ!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Ты использовал свой бонус.\n"
                "Счётчик акции обнулён.\n\n"
                f"🌀 Всего визитов: {new_visits}\n"
                f"🏅 Уровень: {level_name}\n"
                "🔥 Следующий бесплатный кальян: 0/6 визитов\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            send_func(target_id, report, keyboard=kb.get_main_keyboard())
        else:
            report = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "✅ ВИЗИТ ЗАСЧИТАН!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🌀 Всего визитов: {new_visits}\n"
                f"🏅 Уровень: {level_name}\n"
                f"{promo_line}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            if reached_six:
                report += (
                    "\n\n🎉 ПОЗДРАВЛЯЮ!\n"
                    "Ты накопил на бесплатный кальян!\n"
                    "Следующий визит за наш счёт!"
                )
            send_func(target_id, report, keyboard=kb.get_main_keyboard())
        send_func(user_id, f"✅ Визит для гостя {target_id} подтверждён.", keyboard=kb.get_main_keyboard())
        # Предложить отзыв
        db.set_awaiting_review(target_id, True)
        ask_review(vk, target_id, send_func)
    else:
        send_func(user_id, "❌ Не удалось засчитать визит. Проверьте, что гость существует.", keyboard=kb.get_main_keyboard())
    return True

def handle_admin_reject(vk, user_id, message, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return True
    match = re.search(r'\d+', message)
    if not match:
        send_func(user_id, "Ошибка: не могу определить гостя.")
        return True
    target_id = int(match.group())
    send_func(target_id, "❌ Ваш визит не подтверждён. Если вы в заведении, обратитесь к администратору.", keyboard=kb.get_main_keyboard())
    send_func(user_id, f"❌ Заявка для гостя {target_id} отклонена.", keyboard=kb.get_main_keyboard())
    return True