# admin_commands.py
import logging
import database as db
import google_sheets as gs
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# ===== УДАЛЕНИЕ ГОСТЯ =====
def delete_guest(vk, user_id, guest_id, send_func):
    """Вызывается из main.py при команде /delete_guest <ID>"""
    if user_id not in ADMIN_IDS:
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

# ===== СПИСОК ГОСТЕЙ =====
def list_guests(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
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

# ===== ОЧИСТКА КЭША =====
def clear_cache(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    send_func(user_id, "⏳ Очищаю кэш...")
    result = gs.clear_system_cache()
    if result:
        send_func(user_id, "✅ Кэш Google Sheets очищен!")
    else:
        send_func(user_id, "❌ Ошибка очистки кэша")

# ===== ВОССТАНОВЛЕНИЕ ГОСТЕЙ =====
def restore_guests(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администратора!")
        return
    
    send_func(user_id, "⏳ Восстанавливаю гостей из базы данных...")
    count = gs.restore_all_guests_from_db()
    send_func(user_id, f"✅ Готово! Восстановлено гостей: {count}")