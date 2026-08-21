# handlers_modules/raffle.py
"""
Модуль для работы с розыгрышами.
Показывает информацию о текущем розыгрыше и позволяет участвовать.
"""
import database as db
import keyboards as kb
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from .utils import update_command_count, update_raffle_participation


def handle_raffle_info(user_id, guest, send_func):
    """
    Показывает информацию о текущем розыгрыше.
    
    Args:
        user_id (int): ID пользователя
        guest (tuple): Данные гостя из БД
        send_func (callable): Функция отправки сообщения
    """
    update_command_count(user_id, 'raffle')
    update_command_count(user_id, 'button_raffle')
    update_raffle_participation(user_id, guest)

    # Проверяем, есть ли активный розыгрыш
    active_raffle = db.get_active_raffle()
    if not active_raffle:
        db.create_raffle()
        active_raffle = db.get_active_raffle()

    raffle_id = active_raffle[0]
    prize = active_raffle[1]
    is_participant = db.is_raffle_participant(raffle_id, user_id)

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎰 РОЗЫГРЫШ НЕДЕЛИ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 Приз: {prize}\n"
        "📅 Розыгрыш состоится в воскресенье в 20:00\n\n"
        "👥 Чтобы участвовать, нажми кнопку ниже!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = VkKeyboard(one_time=False)
    if is_participant:
        keyboard.add_button('✅ Вы уже участвуете', color=VkKeyboardColor.SECONDARY)
    else:
        keyboard.add_button('✅ Участвую', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)

    send_func(user_id, text, keyboard=keyboard)


def handle_raffle_participate(user_id, send_func):
    """
    Обрабатывает участие пользователя в розыгрыше.
    
    Args:
        user_id (int): ID пользователя
        send_func (callable): Функция отправки сообщения
    """
    active_raffle = db.get_active_raffle()
    
    if active_raffle:
        raffle_id = active_raffle[0]
        success = db.add_raffle_participant(raffle_id, user_id)
        
        if success:
            send_func(
                user_id,
                "✅ Ты успешно участвуешь в розыгрыше! Удачи! 🍀",
                keyboard=kb.get_main_keyboard()
            )
        else:
            send_func(
                user_id,
                "❌ Ты уже участвуешь!",
                keyboard=kb.get_main_keyboard()
            )
    else:
        send_func(
            user_id,
            "❌ Нет активного розыгрыша. Попробуй позже.",
            keyboard=kb.get_main_keyboard()
        )