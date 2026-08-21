# google_sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import CRED_FILE, SHEET_URL, logger
from datetime import datetime

# ============================================================
# ЛЕНИВАЯ ЗАГРУЗКА КРЕДОВ (при импорте не подключаемся)
# ============================================================
_client = None
_spreadsheet = None
_sheet = None

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def _get_client():
    global _client
    if _client is None:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, SCOPES)
        _client = gspread.authorize(creds)
    return _client

def _get_sheet():
    global _sheet, _spreadsheet
    if _sheet is None:
        _spreadsheet = _get_client().open_by_url(SHEET_URL)
        _sheet = _spreadsheet.sheet1
    return _sheet

def get_sheet():
    """Возвращает объект листа Google Sheets (с ленивой загрузкой)."""
    return _get_sheet()

# ============================================================
# КЭШ
# ============================================================
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
    
    if vk_str in _vk_cache:
        return _vk_cache[vk_str]
    if vk_dot in _vk_cache:
        return _vk_cache[vk_dot]
    
    try:
        sheet = _get_sheet()
        col_a = sheet.col_values(1)
        for i, val in enumerate(col_a, start=1):
            val_str = str(val).strip()
            if val_str == vk_str or val_str == vk_dot:
                _vk_cache[vk_str] = i
                return i
    except Exception as e:
        logger.error(f"Ошибка поиска строки для vk_id {vk_id}: {e}")
    return None

def invalidate_cache(vk_id=None):
    """Очищает кэш для конкретного гостя или полностью."""
    if vk_id:
        vk_str = _vk_to_str(vk_id)
        _vk_cache.pop(vk_str, None)
        _vk_cache.pop(_vk_with_dot(vk_id), None)
        logger.debug(f"🗑️ Кэш очищен для гостя {vk_id}")
    else:
        _vk_cache.clear()
        logger.debug("🗑️ Весь кэш очищен")

# ============================================================
# ДОБАВЛЕНИЕ ГОСТЯ
# ============================================================
def add_guest_to_sheet(vk_id, name):
    try:
        sheet = _get_sheet()
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        vk_str = _vk_to_str(vk_id)
        # 15 колонок: A-O
        row = [vk_str, name, '', '', now, 0, 1, 'active', now, 0, '', '', 0, 0, 0]
        sheet.append_row(row)
        _vk_cache[vk_str] = len(sheet.col_values(1))
        logger.info(f"✅ Добавлен гость {vk_id} в Google Sheets")
    except Exception as e:
        logger.error(f"Ошибка добавления гостя {vk_id} в Google Sheets: {e}")

# ============================================================
# ОБНОВЛЕНИЕ ГОСТЯ
# ============================================================
def update_guest_sheet(vk_id, **kwargs):
    try:
        sheet = _get_sheet()
        row_num = find_row_by_vk(vk_id)
        if row_num is None:
            logger.warning(f"⚠️ Строка для vk_id {vk_id} не найдена")
            return
        
        updates = []
        
        # Маппинг полей на колонки
        field_map = {
            'visits': 'F',
            'level': 'G',
            'status': 'H',
            'updated_at': 'I',
            'phone': 'C',
            'birth': 'D',
            'registration_step': 'J',
            'last_activity': 'K',
            'last_reminder': 'L',
            'visits_in_cycle': 'M',
            'free_visit_available': 'N',
            'agreement_given': 'O',
        }
        
        for field, col in field_map.items():
            if field in kwargs:
                updates.append({'range': f'{col}{row_num}', 'values': [[kwargs[field]]]})
        
        if updates:
            sheet.batch_update(updates)
            logger.info(f"✅ Обновлены данные для гостя {vk_id} (обновлено {len(updates)} полей)")
    except Exception as e:
        logger.error(f"Ошибка обновления Google Sheets: {e}")

# ============================================================
# ПОИСК МАСТЕРА
# ============================================================
def get_today_master():
    try:
        client = _get_client()
        spreadsheet = client.open_by_url(SHEET_URL)
        master_sheet = spreadsheet.worksheet("Мастера")
        records = master_sheet.get_all_records()
        today_day = datetime.now().day
        for row in records:
            try:
                if int(row.get('День', -1)) == today_day:
                    return row.get('Имя', 'Мастер'), row.get('Телефон', 'Не указан')
            except (TypeError, ValueError):
                continue
    except Exception as e:
        logger.error(f"Ошибка при получении мастера: {e}")
    return "Администратор", "+7-999-000-00-00"

# ============================================================
# ПРОВЕРКА / ВОССТАНОВЛЕНИЕ ГОСТЯ
# ============================================================
def ensure_guest_in_sheet(vk_id, guest_data):
    """
    Проверяет, что гость есть в таблице, и восстанавливает данные.
    Вызывается на каждое сообщение, поэтому использует кэш.
    """
    try:
        sheet = _get_sheet()
        row_num = find_row_by_vk(vk_id)
        
        if row_num is None:
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            vk_str = _vk_to_str(vk_id)
            # 15 колонок: A-O
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
                guest_data[13] if len(guest_data) > 13 else 0,
                guest_data[14] if len(guest_data) > 14 else 0
            ]
            sheet.append_row(row)
            _vk_cache[vk_str] = len(sheet.col_values(1))
            logger.info(f"✅ Добавлена новая строка для гостя {vk_id}")
        else:
            current_row = sheet.row_values(row_num)
            # Восстанавливаем телефон (колонка C, индекс 2)
            if len(current_row) < 3 or not current_row[2]:
                if guest_data[2]:
                    sheet.update_cell(row_num, 3, guest_data[2])
                    logger.info(f"🔄 Восстановлен телефон для гостя {vk_id}")
            # Восстанавливаем дату рождения (колонка D, индекс 3)
            if len(current_row) < 4 or not current_row[3]:
                if guest_data[3]:
                    sheet.update_cell(row_num, 4, guest_data[3])
                    logger.info(f"🔄 Восстановлена дата рождения для гостя {vk_id}")
            # Восстанавливаем согласие (колонка O, индекс 14)
            if len(current_row) < 15:
                if guest_data[14]:
                    sheet.update_cell(row_num, 15, guest_data[14])
                    logger.info(f"🔄 Восстановлено согласие для гостя {vk_id}")
    except Exception as e:
        logger.error(f"⚠️ Ошибка при проверке/восстановлении гостя: {e}")

# ============================================================
# УДАЛЕНИЕ ГОСТЯ (ДОБАВЛЕНО)
# ============================================================
def delete_guest_by_id(vk_id):
    """
    Удаляет гостя из Google Таблицы по ID.
    ID ищется в колонке A (первая колонка).
    """
    try:
        sheet = _get_sheet()
        row_num = find_row_by_vk(vk_id)
        
        if row_num is None:
            logger.info(f"Гость {vk_id} не найден в таблице — пропускаем")
            return True  # Если его нет, считаем успехом
        
        sheet.delete_rows(row_num)
        
        # Очищаем кэш для этого гостя
        invalidate_cache(vk_id)
        
        logger.info(f"🗑️ Гость {vk_id} удалён из Google Sheets (строка {row_num})")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления из Google Sheets: {e}")
        return False

# ============================================================
# ОЧИСТКА КЭША (ДОБАВЛЕНО)
# ============================================================
def clear_system_cache():
    """
    Сбрасывает кэш Google Sheets, создавая новое подключение.
    Используй, если данные в таблице изменились вручную, но бот их не видит.
    """
    try:
        global _client, _spreadsheet, _sheet, _vk_cache
        
        # 1. Сбрасываем все глобальные переменные (принудительно переподключаемся)
        _client = None
        _spreadsheet = None
        _sheet = None
        
        # 2. Очищаем кэш поиска строк
        _vk_cache.clear()
        
        # 3. Принудительно перечитываем все данные (создаем новое подключение)
        sheet = _get_sheet()
        sheet.get_all_values()
        
        logger.info("✅ Кэш Google Sheets успешно очищен")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка очистки кэша: {e}")
        return False

# ============================================================
# ВОССТАНОВЛЕНИЕ ГОСТЕЙ ИЗ БД (ДОБАВЛЕНО)
# ============================================================
def restore_all_guests_from_db():
    """
    Восстанавливает всех гостей из SQLite в Google Таблицу.
    Проходит по БД и добавляет отсутствующих в таблице.
    """
    try:
        import database as db
        
        guests = db.get_all_guests()
        restored_count = 0
        
        for g in guests:
            # g - кортеж (vk_id, name, phone, birth, created_at, visits, level, status, updated_at, reg_step, last_activity, last_reminder, visits_in_cycle, free_visit_available, agreement_given)
            vk_id = g[0]
            name = g[1]
            
            # Проверяем, есть ли уже гость в таблице (через кэш или поиск)
            row_num = find_row_by_vk(vk_id)
            
            if row_num is None:
                # Если нет — добавляем
                add_guest_to_sheet(vk_id, name)
                restored_count += 1
        
        logger.info(f"✅ Восстановлено гостей: {restored_count}")
        return restored_count
    except Exception as e:
        logger.error(f"❌ Ошибка восстановления: {e}")
        return 0