# handlers_modules/admin.py
import logging
import database as db
import google_sheets as gs
import utils
from config import ADMIN_IDS, PRIZES
from datetime import datetime
import re
import random

logger = logging.getLogger(__name__)

# ============================================================
# ОБЩАЯ ПРОВЕРКА ПРАВ
# ============================================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================================
# РЕАГИРОВАНИЕ НА НОВЫЙ ВИЗИТ (вызывается из main.py)
# ============================================================
def handle_admin_newvisit(vk, user_id, guest, send_func):
    """
    Функция, которая ожидается в __init__.py.
    Вызывается при новом визите гостя (админ-уведомление).
    """
    if not is_admin(user_id):
        return
    
    guest_name = guest[1] if guest else "Неизвестный"
    guest_phone = guest[2] if guest and len(guest) > 2 else "Не указан"
    visits = guest[5] if guest and len(guest) > 5 else 0
    
    admin_text = (
        f"🔔 НОВЫЙ ВИЗИТ!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Гость: {guest_name}\n"
        f"🆔 ID: {user_id}\n"
        f"📞 Телефон: {guest_phone}\n"
        f"📊 Визитов: {visits}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    for admin_id in ADMIN_IDS:
        try:
            vk.messages.send(
                user_id=admin_id,
                message=admin_text,
                random_id=0
            )
        except:
            pass

# ============================================================
# ОБРАБОТКА КОМАНДЫ /admin
# ============================================================
def handle_admin_command(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    text = (
        "🛠️ АДМИН-КОМАНДЫ:\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "/delete_guest <ID> — удалить гостя\n"
        "/list_guests — список гостей\n"
        "/clear_cache — очистить кэш Google Sheets\n"
        "/restore_guests — восстановить гостей из БД\n"
        "/admin — эта справка"
    )
    send_func(user_id, text)

# ============================================================
# УДАЛЕНИЕ ГОСТЯ
# ============================================================
def delete_guest(vk, user_id, guest_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    guest = db.get_guest(guest_id)
    
    result_text = f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n🗑️ ГОСТЬ УДАЛЁН\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result_text += f"✅ ID: {guest_id}\n"
    
    if guest:
        result_text += f"👤 Имя: {guest[1]}\n"
    else:
        result_text += f"👤 Имя: Не найден\n"
    
    result_text += f"\n📊 Результат удаления:\n"
    
    db_result = db.delete_guest(guest_id)
    result_text += f"   {'✅' if db_result else '❌'} База данных (SQLite)\n"
    
    try:
        sheets_result = gs.delete_guest_by_id(guest_id)
        result_text += f"   {'✅' if sheets_result else '❌'} Google Sheets\n"
    except Exception as e:
        result_text += f"   ❌ Google Sheets: {e}\n"
    
    send_func(user_id, result_text)

# ============================================================
# СПИСОК ГОСТЕЙ
# ============================================================
def list_guests(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    guests = db.get_all_guests()
    if not guests:
        send_func(user_id, "📭 База пуста")
        return
    
    text = "📋 СПИСОК ГОСТЕЙ:\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for g in guests:
        text += f"🆔 {g[0]} | {g[1]} | 📞 {g[2] or 'нет'} | Визиты: {g[5] if len(g) > 5 else 0}\n"
    
    send_func(user_id, text[:4000])

# ============================================================
# ОЧИСТКА КЭША
# ============================================================
def clear_cache(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    send_func(user_id, "⏳ Очищаю кэш...")
    result = gs.clear_system_cache()
    if result:
        send_func(user_id, "✅ Кэш Google Sheets очищен!")
    else:
        send_func(user_id, "❌ Ошибка очистки кэша")

# ============================================================
# ВОССТАНОВЛЕНИЕ ГОСТЕЙ
# ============================================================
def restore_guests(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    send_func(user_id, "⏳ Восстанавливаю гостей из базы данных...")
    count = gs.restore_all_guests_from_db()
    send_func(user_id, f"✅ Готово! Восстановлено гостей: {count}")

# ============================================================
# СОЗДАНИЕ ВИЗИТА (для /newvisit)
# ============================================================
def handle_admin_create_raffle(vk, user_id, message, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    parts = message.split(maxsplit=1)
    
    if len(parts) == 1:
        prize = random.choice(PRIZES)
        db.create_raffle(prize)
        send_func(
            user_id,
            f"✅ Создан розыгрыш с призом:\n**{prize}**\n(выбран случайно)"
        )
    else:
        prize = parts[1].strip()
        db.create_raffle(prize)
        send_func(
            user_id,
            f"✅ Создан розыгрыш с призом:\n**{prize}**"
        )

# ============================================================
# ПРОВЕДЕНИЕ РОЗЫГРЫША (для /draw)
# ============================================================
def handle_admin_draw(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
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
    
    new_prize = random.choice(PRIZES)
    db.create_raffle(new_prize)
    logger.info(f"✅ Создан новый розыгрыш с призом: {new_prize}")

# ============================================================
# СТАТУС (для /status)
# ============================================================
def handle_status(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    total_guests = len(db.get_all_guests())
    active_raffle = db.get_active_raffle()
    raffle_prize = active_raffle[1] if active_raffle else "Нет активного"
    
    text = (
        "🔍 **СТАТУС БОТА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего гостей: {total_guests}\n"
        f"🎁 Активный розыгрыш: {raffle_prize}\n"
        f"⏰ Планировщик: работает\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_func(user_id, text, keyboard=None)

# ============================================================
# СТАТИСТИКА (для /stat)
# ============================================================
def handle_stat(vk, user_id, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    guests = db.get_all_guests()
    total_visits = sum(g[5] for g in guests if len(g) > 5 and g[5])
    
    text = (
        "📊 **СТАТИСТИКА**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Всего гостей: {len(guests)}\n"
        f"🌀 Всего визитов: {total_visits}\n"
        f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_func(user_id, text, keyboard=None)

# ============================================================
# УДАЛЕНИЕ ГОСТЯ (для /delete_guest)
# ============================================================
def handle_delete_guest(vk, user_id, message, send_func):
    if not is_admin(user_id):
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    match = re.search(r'\d+', message)
    if not match:
        send_func(user_id, "❌ Укажи ID. Пример: /delete_guest 123456789")
        return
    
    guest_id = int(match.group())
    delete_guest(vk, user_id, guest_id, send_func)