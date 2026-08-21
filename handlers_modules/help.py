# handlers_modules/help.py
"""
Модуль для отображения справки по командам бота.
"""
import keyboards as kb
from .utils import update_command_count


def handle_help(user_id, send_func):
    """
    Показывает список доступных команд и их описание.
    
    Args:
        user_id (int): ID пользователя
        send_func (callable): Функция отправки сообщения
    """
    update_command_count(user_id, 'help')
    
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
    
    send_func(user_id, text, keyboard=kb.get_main_keyboard())