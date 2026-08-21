# handlers_modules/promo.py
"""
Модуль для отображения акций и специальных предложений.
"""
import keyboards as kb
from .utils import update_command_count


def handle_promo(user_id, send_func):
    """
    Показывает текущие акции и специальные предложения.
    
    Args:
        user_id (int): ID пользователя
        send_func (callable): Функция отправки сообщения
    """
    update_command_count(user_id, 'promo')
    update_command_count(user_id, 'button_promo')
    
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🕒 DaytimeHookah\n"
        "📅 Вс / Чт с 14:00 до 17:00\n\n"
        "💨 Кальян + ☕️ чай/кофе/лимонад\n"
        "💵 Всего за 900 ₽!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ Не упусти возможность отдохнуть с выгодой!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    send_func(user_id, text, keyboard=kb.get_main_keyboard())