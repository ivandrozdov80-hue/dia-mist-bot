# handlers_modules/admin.py
import database as db
import google_sheets as gs
from config import ADMIN_IDS, logger
from .utils import update_command_count
from admin_commands import handle_newvisit, handle_create_raffle, handle_draw
from datetime import datetime, timedelta


def handle_admin_newvisit(vk, user_id, message, send_func):
    update_command_count(user_id, 'newvisit')
    handle_newvisit(vk, user_id, message, send_func)


def handle_admin_create_raffle(vk, user_id, message, send_func):
    handle_create_raffle(vk, user_id, message, send_func)


def handle_admin_draw(vk, user_id, send_func):
    handle_draw(vk, user_id, send_func)


# ===== НОВОЕ: /status (health-check) =====
def handle_status(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return

    lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━", "🟢 СТАТУС БОТА", "━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]

    # 1. VK
    try:
        vk.users.get(user_ids=1)
        lines.append("✅ VK API: подключено")
    except Exception as e:
        lines.append(f"❌ VK API: ошибка ({str(e)[:50]})")

    # 2. SQLite
    try:
        db.cursor.execute("SELECT 1")
        lines.append("✅ SQLite: работает")
    except Exception as e:
        lines.append(f"❌ SQLite: ошибка ({str(e)[:50]})")

    # 3. Google Sheets
    try:
        gs.get_sheet().row_values(1)
        lines.append("✅ Google Sheets: доступно")
    except Exception as e:
        lines.append(f"❌ Google Sheets: ошибка ({str(e)[:50]})")

    # 4. Активный розыгрыш
    raffle = db.get_active_raffle()
    if raffle:
        lines.append(f"🎰 Розыгрыш: активен (приз: {raffle[1]})")
    else:
        lines.append("🎰 Розыгрыш: не активен")

    # 5. Количество гостей
    db.cursor.execute("SELECT COUNT(*) FROM guests")
    count = db.cursor.fetchone()[0]
    lines.append(f"👥 Гостей в базе: {count}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    send_func(user_id, "\n".join(lines), keyboard=None)


# ===== НОВОЕ: /stat (статистика) =====
def handle_stat(vk, user_id, send_func):
    if user_id not in ADMIN_IDS:
        send_func(user_id, "⛔ Только для администраторов.")
        return

    lines = ["━━━━━━━━━━━━━━━━━━━━━━━━━━", "📊 СТАТИСТИКА", "━━━━━━━━━━━━━━━━━━━━━━━━━━", ""]

    # Всего гостей
    db.cursor.execute("SELECT COUNT(*) FROM guests")
    total = db.cursor.fetchone()[0]
    lines.append(f"👥 Всего гостей: {total}")

    # Визиты за неделю (updated_at за последние 7 дней)
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    db.cursor.execute("SELECT COUNT(*) FROM guests WHERE updated_at > ?", (week_ago,))
    week_visits = db.cursor.fetchone()[0]
    lines.append(f"📅 Визитов за неделю: {week_visits}")

    # Активные гости (last_activity за последние 30 дней)
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    db.cursor.execute("SELECT COUNT(*) FROM guests WHERE last_activity > ?", (month_ago,))
    active = db.cursor.fetchone()[0]
    inactive = total - active
    lines.append(f"🟢 Активных (30 дней): {active}")
    lines.append(f"🔴 Неактивных: {inactive}")

    # Всего достижений у всех гостей
    db.cursor.execute("SELECT COUNT(*) FROM user_achievements")
    ach_total = db.cursor.fetchone()[0]
    lines.append(f"🏆 Всего выдано достижений: {ach_total}")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    send_func(user_id, "\n".join(lines), keyboard=None)