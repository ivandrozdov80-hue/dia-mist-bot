# utils.py
import json
import database as db
from config import logger

def update_command_count(user_id, command_name):
    guest = db.get_guest(user_id)
    if guest and len(guest) > 16:
        try:
            command_counts = json.loads(guest[16] if guest[16] else '{}')
            command_counts[command_name] = command_counts.get(command_name, 0) + 1
            db.update_guest(user_id, command_counts=json.dumps(command_counts))
        except Exception as e:
            logger.error(f"Ошибка обновления счётчика команд для {user_id}: {e}")

def update_message_count(user_id, guest):
    if guest and len(guest) > 14:
        try:
            total_messages = int(guest[14]) if guest[14] is not None else 0
            db.update_guest(user_id, total_messages=total_messages + 1)
        except Exception as e:
            logger.error(f"Ошибка обновления счётчика сообщений для {user_id}: {e}")

def update_raffle_participation(user_id, guest):
    if guest and len(guest) > 17:
        try:
            participations = int(guest[17]) if guest[17] is not None else 0
            db.update_guest(user_id, raffle_participations=participations + 1)
        except Exception as e:
            logger.error(f"Ошибка обновления участия в розыгрыше для {user_id}: {e}")