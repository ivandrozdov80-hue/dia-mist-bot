# admin_commands.py
"""
Команды для администраторов бота.
Включает создание визитов, розыгрышей и проведение розыгрышей.
"""
import re
import random
import database as db
import utils
from keyboards import get_main_keyboard, get_confirm_visit_keyboard
from config import logger, ADMIN_IDS, PRIZES


def handle_newvisit(vk, user_id, message, send_func):
    """
    Создаёт новый визит для гостя.
    Генерирует QR-код и отправляет гостю приглашение с кнопкой подтверждения.
    
    Args:
        vk: Объект VK API
        user_id (int): ID администратора
        message (str): Текст команды (/newvisit [id])
        send_func (callable): Функция отправки сообщения
    """
    # Парсим ID гостя из сообщения
    match = re.search(r'\[id(\d+)\|', message)
    if not match:
        parts = message.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_id = int(parts[1])
        else:
            send_func(
                user_id,
                "Не могу найти гостя. Используй /newvisit [id123|Имя] или просто ID"
            )
            return
    else:
        target_id = int(match.group(1))

    # Генерируем код и QR-код
    code = utils.generate_visit_code(target_id)
    qr_img = utils.create_qr_image(code)
    
    # Загружаем QR-код в VK
    attachment = None
    try:
        from vk_api.upload import VkUpload
        upload = VkUpload(vk)
        photo = upload.photo_messages(qr_img)[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
    except Exception as e:
        logger.error(f"Не удалось загрузить QR-картинку: {e}")

    # Отправляем QR-код администратору
    send_func(
        user_id,
        f"✅ QR-код для гостя ID {target_id}. Код: {code}\n"
        f"Действителен 1 час.\n"
        f"Гостю отправлено приглашение с кнопкой подтверждения.",
        attachment=attachment,
        keyboard=get_main_keyboard()
    )

    # Отправляем приглашение гостю
    guest_message = (
        f"🧞 Привет! Администратор зарегистрировал твой визит.\n"
        f"Просто нажми кнопку ниже, чтобы подтвердить его.\n"
        f"Код действителен 1 час."
    )
    send_func(
        target_id,
        guest_message,
        keyboard=get_confirm_visit_keyboard(code)
    )


def handle_create_raffle(vk, user_id, message, send_func):
    """
    Создаёт новый розыгрыш.
    Если приз не указан, выбирается случайный из списка PRIZES.
    
    Args:
        vk: Объект VK API
        user_id (int): ID администратора
        message (str): Текст команды (/create_raffle [приз])
        send_func (callable): Функция отправки сообщения
    """
    parts = message.split(maxsplit=1)
    
    if len(parts) == 1:
        # Случайный приз
        prize = random.choice(PRIZES)
        db.create_raffle(prize)
        send_func(
            user_id,
            f"✅ Создан розыгрыш с призом:\n**{prize}**\n(выбран случайно)"
        )
    else:
        # Указанный приз
        prize = parts[1].strip()
        db.create_raffle(prize)
        send_func(
            user_id,
            f"✅ Создан розыгрыш с призом:\n**{prize}**"
        )


def handle_draw(vk, user_id, send_func):
    """
    Проводит розыгрыш: выбирает победителя из участников.
    
    Args:
        vk: Объект VK API
        user_id (int): ID администратора
        send_func (callable): Функция отправки сообщения
    """
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ У тебя нет прав для этой команды.")
        return
    
    active_raffle = db.get_active_raffle()
    if not active_raffle:
        send_func(user_id, "❌ Нет активного розыгрыша.")
        return
    
    raffle_id = active_raffle[0]
    prize = active_raffle[1]
    participants = db.get_raffle_participants(raffle_id)
    
    if not participants:
        send_func(user_id, "❌ Нет участников. Розыгрыш отменён.")
        return
    
    winner = random.choice(participants)
    db.finish_raffle(raffle_id, winner)
    
    # Уведомляем победителя
    send_func(
        winner,
        f"🎉 ПОЗДРАВЛЯЮ! Ты выиграл **{prize}**! Приходи в течение 7 дней!"
    )
    
    # Уведомляем администратора
    send_func(
        user_id,
        f"✅ Победитель выбран! ID: {winner}\nПриз: {prize}"
    )
    
    # Создаём новый розыгрыш автоматически
    new_prize = random.choice(PRIZES)
    db.create_raffle(new_prize)
    logger.info(f"✅ Создан новый розыгрыш с призом: {new_prize}")