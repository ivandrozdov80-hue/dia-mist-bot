# google_sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ =====
CRED_FILE = 'credentials.json'
SHEET_ID = '1BS-h_Oq70P2G9cTR5K7yUS8KadkUpcH9ymrMKx-NYIo'
SHEET_NAME = 'Лист1'  # Если название листа другое — замени

# ===== ПОДКЛЮЧЕНИЕ =====
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# ===== ДОБАВЛЕНИЕ ГОСТЯ =====
def add_guest_to_sheet(guest_id, name):
    """
    Добавляет гостя в таблицу.
    Столбцы:
    M - визиты, N - бесплатный доступ, O - согласие,
    S - ID, T - имя, U - дата/время
    """
    try:
        sheet = get_sheet()
        row = [
            "", "", "", "", "", "", "", "", "", "", "", "",  # A-L (пустые)
            "0",                            # M  - Визиты
            "0",                            # N  - Бесплатный доступ
            "0",                            # O  - Согласие
            "", "", "", "",                 # P-R (пустые)
            str(guest_id),                  # S  - ID
            str(name),                      # T  - Имя
            datetime.now().strftime("%d.%m.%Y %H:%M:%S")  # U - Дата/время
        ]
        sheet.append_row(row, table_range="A:U")
        logger.info(f"✅ Гость {guest_id} добавлен в Google Sheets")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка добавления в Google Sheets: {e}")
        return False

# ===== ОБНОВЛЕНИЕ ГОСТЯ =====
def update_guest_sheet(guest_id, **kwargs):
    """
    Обновляет данные гостя.
    Доступные ключи: visits, free_visits, agreement_given, birth, last_activity
    """
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        
        # Ищем строку по ID в столбце S (индекс 18)
        row_num = None
        for i, row in enumerate(all_rows):
            if len(row) > 18 and str(row[18]) == str(guest_id):
                row_num = i + 1
                break
        
        if not row_num:
            # Если гостя нет в таблице — добавляем
            add_guest_to_sheet(guest_id, guest_id)
            return update_guest_sheet(guest_id, **kwargs)
        
        # Соответствие ключей столбцам
        col_map = {
            "visits": "M",
            "free_visits": "N",
            "agreement_given": "O",
            "birth": "D",
            "last_activity": "U"
        }
        
        for key, value in kwargs.items():
            if key in col_map:
                sheet.update(f"{col_map[key]}{row_num}", str(value))
        
        logger.info(f"✅ Гость {guest_id} обновлён в Google Sheets")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления в Google Sheets: {e}")
        return False

# ===== УДАЛЕНИЕ ГОСТЯ =====
def delete_guest_by_id(guest_id):
    """
    Удаляет гостя из Google Таблицы по ID.
    ID ищется в столбце S (индекс 18).
    """
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        
        for i, row in enumerate(all_rows):
            if len(row) > 18 and str(row[18]) == str(guest_id):
                row_num = i + 1
                sheet.delete_rows(row_num)
                logger.info(f"🗑️ Гость {guest_id} удалён из Google Sheets (строка {row_num})")
                return True
        
        # Если не нашли — считаем успехом
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления из Google Sheets: {e}")
        return False

# ===== ПРОВЕРКА НАЛИЧИЯ ГОСТЯ =====
def ensure_guest_in_sheet(guest_id, guest_data):
    """Проверяет, есть ли гость в таблице, если нет — добавляет"""
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        
        for row in all_rows:
            if len(row) > 18 and str(row[18]) == str(guest_id):
                return True
        
        # Если нет — добавляем
        add_guest_to_sheet(guest_id, guest_data[1] if len(guest_data) > 1 else guest_id)
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки гостя: {e}")
        return False

# ================== ОЧИСТКА КЭША ==================
def clear_system_cache():
    """
    Сбрасывает кэш Google Sheets, создавая новое подключение.
    """
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CRED_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        
        # Принудительно читаем все данные, чтобы обновить кэш
        sheet.get_all_values()
        print("✅ Кэш Google Sheets успешно очищен")
        return True
    except Exception as e:
        print(f"❌ Ошибка очистки кэша: {e}")
        return False

# ================== ВОССТАНОВЛЕНИЕ ГОСТЕЙ ==================
def restore_all_guests_from_db():
    """
    Восстанавливает всех гостей из SQLite в Google Таблицу.
    """
    try:
        import database as db
        
        guests = db.get_all_guests()
        restored_count = 0
        
        for g in guests:
            guest_id = g[0]
            name = g[1]
            
            # Проверяем, есть ли уже гость в таблице
            sheet = get_sheet()
            all_rows = sheet.get_all_values()
            exists = False
            
            for row in all_rows:
                if len(row) > 18 and str(row[18]) == str(guest_id):
                    exists = True
                    break
            
            if not exists:
                add_guest_to_sheet(guest_id, name)
                restored_count += 1
        
        print(f"✅ Восстановлено гостей: {restored_count}")
        return restored_count
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")
        return 0