# handlers_modules/utils.py
"""
Утилиты для обновления статистики пользователей.
"""
import json
import database as db
from config import logger


def update_command_count(user_id, command_name):
    """
    Увеличивает счётчик использованных команд для пользователя.
    
    Args:
        user_id (int): ID пользователя
        command_name (str): Название команды
    """
    guest = db.get_guest(user_id)
    if guest and len(guest) > 16:
        try:
            command_counts = json.loads(guest[16] if guest[16] else '{}')
            command_counts[command_name] = command_counts.get(command_name, 0) + 1
            db.update_guest(user_id, command_counts=json.dumps(command_counts))
        except Exception as e:
            logger.error(f"Ошибка обновления счётчика команд для {user_id}: {e}")


def update_raffle_participation(user_id, guest):
    """
    Увеличивает счётчик участия в розыгрышах для пользователя.
    
    Args:
        user_id (int): ID пользователя
        guest (tuple): Данные гостя из БД
    """
    if guest and len(guest) > 17:
        try:
            participations = int(guest[17]) if guest[17] is not None else 0
            db.update_guest(user_id, raffle_participations=participations + 1)
        except Exception as e:
            logger.error(f"Ошибка обновления участия в розыгрыше для {user_id}: {e}")