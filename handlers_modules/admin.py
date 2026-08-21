# handlers_modules/admin.py
import database as db
import google_sheets as gs
from config import ADMIN_IDS, logger
from handlers_modules.utils import update_command_count
from admin_commands import handle_newvisit, handle_create_raffle, handle_draw
from datetime import datetime, timedelta


def handle_admin_newvisit(vk, user_id, message, send_func):
    update_command_count(user_id, 'newvisit')
    handle_newvisit(vk, user_id, message, send_func)


def handle_admin_create_raffle(vk, user_id, message, send_func):
    handle_create_raffle(vk, user_id, message, send_func)


def handle_admin_draw(vk, user_id, send_func):
    handle_draw(vk, user_id, send_func)


def handle_status(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return

    lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━", "🟢 СТАТУС БОТА", "━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]

    # VK API
    try:
        vk.users.get(user_ids=1)
        lines.append("✅ VK API: подключено")
    except Exception as e:
        lines.append(f"❌ VK API: ошибка ({str(e)[:50]})")

    # SQLite
    try:
        db.cursor.execute("SELECT 1")
        lines.append("✅ SQLite: работает")
    except Exception as e:
        lines.append(f"❌ SQLite: ошибка ({str(e)[:50]})")

    # Google Sheets
    try:
        gs.get_sheet().row_values(1)
        lines.append("✅ Google Sheets: доступно")
    except Exception as e:
        lines.append(f"❌ Google Sheets: ошибка ({str(e)[:50]})")

    # Активный розыгрыш
    raffle = db.get_active_raffle()
    if raffle:
        lines.append(f"🎰 Розыгрыш: активен (приз: {raffle[1]})")
    else:
        lines.append("🎰 Розыгрыш: не активен")

    # Количество гостей
    db.cursor.execute("SELECT COUNT(*) FROM guests")
    count = db.cursor.fetchone()[0]
    lines.append(f"👥 Гостей в базе: {count}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    send_func(user_id, "\n".join(lines), keyboard=None)


def handle_stat(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return

    lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━", "📊 СТАТИСТИКА", "━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]

    # Всего гостей
    db.cursor.execute("SELECT COUNT(*) FROM guests")
    total = db.cursor.fetchone()[0]
    lines.append(f"👥 Всего гостей: {total}")

    # Визиты за неделю
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    db.cursor.execute("SELECT COUNT(*) FROM guests WHERE updated_at > ?", (week_ago,))
    week_visits = db.cursor.fetchone()[0]
    lines.append(f"📅 Визитов за неделю: {week_visits}")

    # Активные гости (30 дней)
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    db.cursor.execute("SELECT COUNT(*) FROM guests WHERE last_activity > ?", (month_ago,))
    active = db.cursor.fetchone()[0]
    inactive = total - active
    lines.append(f"🟢 Активных (30 дней): {active}")
    lines.append(f"🔴 Неактивных: {inactive}")

    # Достижения (если таблица существует)
    try:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_achievements'")
        table_exists = db.cursor.fetchone()
        if table_exists:
            db.cursor.execute("SELECT COUNT(*) FROM user_achievements")
            ach_total = db.cursor.fetchone()[0]
            lines.append(f"🏆 Всего выдано достижений: {ach_total}")
        else:
            lines.append("🏆 Таблица достижений: не создана")
    except Exception as e:
        lines.append(f"🏆 Ошибка при проверке достижений: {str(e)[:30]}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    send_func(user_id, "\n".join(lines), keyboard=None)


def handle_delete_guest(vk, user_id, message, send_func):
    """
    Полное удаление гостя из базы данных и Google Sheets.
    Использование: /delete_guest [ID_гостя]
    Пример: /delete_guest 123456789
    """
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return

    parts = message.split()
    if len(parts) != 2:
        send_func(
            user_id,
            "❌ Используй: /delete_guest [ID_гостя]\n"
            "Например: /delete_guest 123456789"
        )
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        send_func(user_id, "❌ ID должен быть числом.")
        return

    # Проверяем, существует ли гость в БД
    guest = db.get_guest(target_id)
    if not guest:
        send_func(user_id, f"❌ Гость с ID {target_id} не найден.")
        return

    guest_name = guest[1] if guest[1] else "Без имени"
    delete_results = []

    # ============================================================
    # 1. УДАЛЯЕМ ИЗ SQLite
    # ============================================================
    try:
        db.cursor.execute("DELETE FROM guests WHERE vk_id = ?", (target_id,))
        db.conn.commit()
        delete_results.append("✅ База данных (SQLite)")
        logger.info(f"✅ Гость {target_id} ({guest_name}) удалён из SQLite")
    except Exception as e:
        logger.error(f"Ошибка удаления из SQLite: {e}")
        send_func(user_id, f"❌ Ошибка при удалении из базы: {e}")
        return

    # ============================================================
    # 2. УДАЛЯЕМ ИЗ Google Sheets
    # ============================================================
    try:
        row_num = gs.find_row_by_vk(target_id)
        if row_num:
            gs.sheet.delete_rows(row_num)
            gs.invalidate_cache(target_id)
            delete_results.append("✅ Google Таблица")
            logger.info(f"✅ Гость {target_id} удалён из Google Sheets (строка {row_num})")
        else:
            delete_results.append("⚠️ Не найден в Google Таблице")
            logger.warning(f"⚠️ Гость {target_id} не найден в Google Sheets")
    except Exception as e:
        logger.error(f"Ошибка удаления из Google Sheets: {e}")
        delete_results.append(f"❌ Ошибка: {str(e)[:30]}")

    # ============================================================
    # 3. VACUUM — сжатие БД (опционально, можно делать реже)
    # ============================================================
    try:
        db.cursor.execute("VACUUM")
        db.conn.commit()
        logger.info("✅ VACUUM выполнен")
    except Exception as e:
        logger.warning(f"⚠️ VACUUM не выполнен: {e}")

    send_func(
        user_id,
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗑️ ГОСТЬ УДАЛЁН\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ ID: {target_id}\n"
        f"👤 Имя: {guest_name}\n\n"
        f"📊 Результат удаления:\n"
        f"   {delete_results[0]}\n"
        f"   {delete_results[1] if len(delete_results) > 1 else ''}\n\n"
        f"⚠️ Если гость напишет боту снова,\n"
        f"   он будет зарегистрирован как НОВЫЙ.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )