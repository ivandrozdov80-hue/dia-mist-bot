# handlers_modules/profile.py
import database as db
import google_sheets as gs
import keyboards as kb
import utils
from config import LEVEL_NAMES, logger
from .utils import update_command_count

def handle_profile(vk, user_id, guest, send_func):
    update_command_count(user_id, 'profile')
    update_command_count(user_id, 'button_profile')
    visits = int(guest[5]) if guest[5] is not None else 0
    level = utils.get_level_by_visits(visits)
    level_name = LEVEL_NAMES.get(level, "Новичок")
    cycle_info = db.get_cycle_info(user_id)
    visits_in_cycle, free_available = cycle_info
    if free_available == 1:
        promo_text = "🎁 Ты накопил на бесплатный кальян!\n   Следующий визит – бесплатный!"
    else:
        remaining = 6 - visits_in_cycle
        promo_text = f"🔥 Бесплатный кальян: {visits_in_cycle}/6\n   Осталось {remaining} визитов"

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 ПРОФИЛЬ ГОСТЯ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🧑‍💼 Имя: {guest[1]}\n"
        f"📞 Телефон: {guest[2] or 'не указан'}\n"
        f"🎂 Дата рождения: {guest[3] or 'не указана'}\n\n"
        f"🌀 Всего визитов: {visits}\n"
        f"🏅 Уровень: {level_name}\n\n"
        f"{promo_text}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_func(user_id, text, keyboard=kb.get_main_keyboard())