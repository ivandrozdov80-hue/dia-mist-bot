# google_sheets.py
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import CRED_FILE, SHEET_URL, logger
from datetime import datetime

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Создание кредов с scopes
creds = None
if os.getenv("GOOGLE_CREDS_JSON"):
    # Из файла сервисного аккаунта
    creds = ServiceAccountCredentials.from_service_account_file(
        os.getenv("GOOGLE_CREDS_JSON"),
        scopes=scope
    )
elif os.getenv(CRED_FILE):
    # Из переменной окружения (JSON строка)
    creds_info = json.loads(os.getenv(CRED_FILE))
    creds = ServiceAccountCredentials.from_service_account_info(
        creds_info,
        scopes=scope
    )


gc = gspread.authorize(creds)
sheet = gc.open_by_url(SHEET_URL).sheet1

# Простой кэш для vk_id -> row_number (чтобы не искать каждый раз)
_vk_cache = {}

def _vk_to_str(vk_id):
    try:
        return str(int(float(vk_id)))
    except:
        return str(vk_id)

def _vk_with_dot(vk_id):
    vk_str = _vk_to_str(vk_id)
    try:
        return str(float(vk_str))
    except:
        return vk_str

def find_row_by_vk(vk_id):
    vk_str = _vk_to_str(vk_id)
    vk_dot = _vk_with_dot(vk_id)
    
    # Проверяем кэш
    if vk_str in _vk_cache:
        return _vk_cache[vk_str]
    if vk_dot in _vk_cache:
        return _vk_cache[vk_dot]
    
    try:
        col_a = sheet.col_values(1)
        for i, val in enumerate(col_a, start=1):
            val_str = str(val).strip()
            if val_str == vk_str or val_str == vk_dot:
                _vk_cache[vk_str] = i
                return i
    except Exception as e:
        logger.error(f"Ошибка поиска строки для vk_id {vk_id}: {e}")
    return None

def add_guest_to_sheet(vk_id, name):
    try:
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        vk_str = _vk_to_str(vk_id)
        row = [vk_str, name, '', '', now, 0, 1, 'active', now, 0, '', '', 0, 0]
        sheet.append_row(row)
        # Обновляем кэш
        _vk_cache[vk_str] = len(sheet.col_values(1))
        logger.info(f"✅ Добавлен гость {vk_id} в Google Sheets")
    except Exception as e:
        logger.error(f"Ошибка добавления гостя {vk_id} в Google Sheets: {e}")

def update_guest_sheet(vk_id, **kwargs):
    try:
        row_num = find_row_by_vk(vk_id)
        if row_num is None:
            logger.warning(f"⚠️ Строка для vk_id {vk_id} не найдена. Попробуйте вызвать ensure_guest_in_sheet")
            return
        # Собираем обновления в список (batch_update)
        updates = []
        if 'visits' in kwargs:
            updates.append({'range': f'F{row_num}', 'values': [[kwargs['visits']]]})
            logger.debug(f"   Обновлены визиты: {kwargs['visits']}")
        if 'level' in kwargs:
            updates.append({'range': f'G{row_num}', 'values': [[kwargs['level']]]})
        if 'status' in kwargs:
            updates.append({'range': f'H{row_num}', 'values': [[kwargs['status']]]})
        if 'updated_at' in kwargs:
            updates.append({'range': f'I{row_num}', 'values': [[kwargs['updated_at']]]})
        if 'phone' in kwargs:
            updates.append({'range': f'C{row_num}', 'values': [[kwargs['phone']]]})
        if 'birth' in kwargs:
            updates.append({'range': f'D{row_num}', 'values': [[kwargs['birth']]]})
        if 'registration_step' in kwargs:
            updates.append({'range': f'J{row_num}', 'values': [[kwargs['registration_step']]]})
        if 'last_activity' in kwargs:
            updates.append({'range': f'K{row_num}', 'values': [[kwargs['last_activity']]]})
        if 'last_reminder' in kwargs:
            updates.append({'range': f'L{row_num}', 'values': [[kwargs['last_reminder']]]})
        if 'visits_in_cycle' in kwargs:
            updates.append({'range': f'M{row_num}', 'values': [[kwargs['visits_in_cycle']]]})
        if 'free_visit_available' in kwargs:
            updates.append({'range': f'N{row_num}', 'values': [[kwargs['free_visit_available']]]})
        if updates:
            sheet.batch_update(updates)
        logger.info(f"✅ Обновлены данные для гостя {vk_id} в строке {row_num}")
    except Exception as e:
        logger.error(f"Ошибка обновления Google Sheets: {e}")

def get_today_master():
    try:
        local_creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
        local_gc = gspread.authorize(local_creds)
        master_sheet = local_gc.open_by_url(SHEET_URL).worksheet("Мастера")
        records = master_sheet.get_all_records()
        today_day = datetime.now().day
        for row in records:
            if int(row.get('День', -1)) == today_day:
                return row.get('Имя', 'Мастер'), row.get('Телефон', 'Не указан')
    except Exception as e:
        logger.error(f"Ошибка при получении мастера: {e}")
    return "Администратор", "+7-999-000-00-00"

def ensure_guest_in_sheet(vk_id, guest_data):
    try:
        row_num = find_row_by_vk(vk_id)
        if row_num is None:
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            vk_str = _vk_to_str(vk_id)
            row = [
                vk_str,
                guest_data[1] or '',
                guest_data[2] or '',
                guest_data[3] or '',
                guest_data[4] or now,
                guest_data[5] or 0,
                guest_data[6] or 1,
                guest_data[7] or 'active',
                guest_data[8] or now,
                guest_data[9] if len(guest_data) > 9 else 0,
                guest_data[10] if len(guest_data) > 10 else '',
                guest_data[11] if len(guest_data) > 11 else '',
                guest_data[12] if len(guest_data) > 12 else 0,
                guest_data[13] if len(guest_data) > 13 else 0
            ]
            sheet.append_row(row)
            _vk_cache[vk_str] = len(sheet.col_values(1))
            logger.info(f"✅ Добавлена новая строка для гостя {vk_id} в Google Sheets")
        else:
            current_row = sheet.row_values(row_num)
            if not current_row[2] and guest_data[2]:
                sheet.update_cell(row_num, 3, guest_data[2])
                logger.info(f"🔄 Восстановлен телефон для гостя {vk_id}")
            if not current_row[3] and guest_data[3]:
                sheet.update_cell(row_num, 4, guest_data[3])
                logger.info(f"🔄 Восстановлена дата рождения для гостя {vk_id}")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при проверке/восстановлении гостя в Google Sheets: {e}")