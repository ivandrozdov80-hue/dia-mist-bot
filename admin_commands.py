# admin_commands.py
import re
import random
import database as db
import utils
from keyboards import get_main_keyboard, get_confirm_visit_keyboard
from config import logger

def handle_newvisit(vk, user_id, message, send_func):
    match = re.search(r'\[id(\d+)\|', message)
    if not match:
        parts = message.split()
        if len(parts) == 2 and parts[1].isdigit():
            target_id = int(parts[1])
        else:
            send_func(user_id, "Не могу найти гостя. Используй /newvisit [id123|Имя] или просто ID")
            return
    else:
        target_id = int(match.group(1))

    code = utils.generate_visit_code(target_id)
    qr_img = utils.create_qr_image(code)
    attachment = None
    try:
        from vk_api.upload import VkUpload
        upload = VkUpload(vk)
        photo = upload.photo_messages(qr_img)[0]
        attachment = f"photo{photo['owner_id']}_{photo['id']}"
    except Exception as e:
        logger.error(f"Не удалось загрузить QR-картинку: {e}")

    send_func(
        user_id,
        f"✅ QR-код для гостя ID {target_id}. Код: {code}\nДействителен 1 час.\nГостю отправлено приглашение с кнопкой подтверждения.",
        attachment=attachment,
        keyboard=get_main_keyboard()
    )

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
    from config import PRIZES
    parts = message.split(maxsplit=1)
    if len(parts) == 1:
        raffle_id = db.create_raffle()
        prize = db.get_active_raffle()[1]
        send_func(user_id, f"✅ Создан розыгрыш с призом:\n**{prize}**\n(выбран случайно)")
    else:
        prize = parts[1].strip()
        raffle_id = db.create_raffle(prize)
        send_func(user_id, f"✅ Создан розыгрыш с призом:\n**{prize}**")

def handle_draw(vk, user_id, send_func):
    from config import ADMIN_IDS
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
    send_func(winner, f"🎉 ПОЗДРАВЛЯЮ! Ты выиграл **{prize}**! Приходи в течение 7 дней!")
    send_func(user_id, f"✅ Победитель выбран! ID: {winner}\nПриз: {prize}")
    db.create_raffle()