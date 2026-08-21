# handlers_modules/admin.py
import logging
import database as db
import google_sheets as gs
from config import ADMIN_IDS
from datetime import datetime

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