# admin_commands.py
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
import database as db
import google_sheets as gs

logger = logging.getLogger(__name__)

# ===== УДАЛЕНИЕ ГОСТЯ =====
async def delete_guest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /delete_guest <ID>"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Только для администратора!")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("📝 Укажи ID. Пример: /delete_guest 123456789")
        return
    
    try:
        guest_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом!")
        return
    
    # Получаем гостя из БД (у тебя в БД гости хранятся как кортежи)
    guest = db.get_guest(guest_id)
    
    result_text = f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n🗑️ ГОСТЬ УДАЛЁН\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    result_text += f"✅ ID: {guest_id}\n"
    
    if guest:
        result_text += f"👤 Имя: {guest[1]}\n"
    else:
        result_text += f"👤 Имя: Не найден\n"
    
    result_text += f"\n📊 Результат удаления:\n"
    
    # 1. Удаляем из SQLite
    db_result = db.delete_guest(guest_id)
    result_text += f"   {'✅' if db_result else '❌'} База данных (SQLite)\n"
    
    # 2. Удаляем из Google Sheets
    try:
        sheets_result = gs.delete_guest_by_id(guest_id)
        result_text += f"   {'✅' if sheets_result else '❌'} Google Sheets\n"
    except Exception as e:
        result_text += f"   ❌ Google Sheets: {e}\n"
    
    await update.message.reply_text(result_text)

# ===== СПИСОК ГОСТЕЙ =====
async def list_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /list_guests"""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Только для администратора!")
        return
    
    guests = db.get_all_guests()
    if not guests:
        await update.message.reply_text("📭 База пуста")
        return
    
    text = "📋 СПИСОК ГОСТЕЙ:\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for g in guests:
        # g - кортеж: (id, name, phone, birth, ..., visits, ...)
        text += f"🆔 {g[0]} | {g[1]} | 📞 {g[2] or 'нет'} | Визиты: {g[5] if len(g) > 5 else 0}\n"
    
    await update.message.reply_text(text[:4000])