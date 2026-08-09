# google_sheets.py
import os
import re
import json
import threading
import gspread
from google.oauth2.service_account import Credentials
from config import CRED_FILE, SHEET_URL, logger
from datetime import datetime

# gspread 6.x работает только с google-auth; oauth2client он не поддерживает.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_spreadsheet = None
_sheet = None
_init_lock = threading.RLock()

# Поле гостя -> колонка листа. Порядок колонок задан в database.py: init_db()
GUEST_COLUMNS = {
    'phone': 'C',
    'birth': 'D',
    'visits': 'F',
    'level': 'G',
    'status': 'H',
    'updated_at': 'I',
    'registration_step': 'J',
    'last_activity': 'K',
    'last_reminder': 'L',
    'visits_in_cycle': 'M',
    'free_visit_available': 'N',
}

DEFAULT_MASTER = ("Администратор", "+7-999-000-00-00")


def _load_credentials():
    """Креды сервисного аккаунта.

    GOOGLE_CREDS_JSON – либо JSON-строка целиком, либо путь к файлу.
    Если переменная не задана – берём CRED_FILE из корня проекта.
    """
    raw = os.getenv("GOOGLE_CREDS_JSON", "").strip()
    if raw.startswith("{"):
        return Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    if raw:
        return Credentials.from_service_account_file(raw, scopes=SCOPES)
    if os.path.isfile(CRED_FILE):
        return Credentials.from_service_account_file(CRED_FILE, scopes=SCOPES)
    raise RuntimeError(
        "Не найдены креды Google: задай GOOGLE_CREDS_JSON (путь к файлу "
        f"или JSON-строку) либо положи {CRED_FILE} в корень проекта"
    )


def get_client():
    global _client
    with _init_lock:
        if _client is None:
            _client = gspread.authorize(_load_credentials())
        return _client


def get_spreadsheet():
    global _spreadsheet
    with _init_lock:
        if _spreadsheet is None:
            _spreadsheet = get_client().open_by_url(SHEET_URL)
        return _spreadsheet


def get_sheet():
    """Основной лист гостей.

    Подключение создаётся при первом обращении, а не при импорте: сетевой сбой
    Google или отсутствие кредов не должны мешать боту стартовать.
    """
    global _sheet
    with _init_lock:
        if _sheet is None:
            _sheet = get_spreadsheet().sheet1
        return _sheet


# Простой кэш для vk_id -> row_number (чтобы не искать каждый раз)
_vk_cache = {}
# Гости, чью строку уже сверяли в этом процессе (см. ensure_guest_in_sheet)
_verified_guests = set()

def _vk_to_str(vk_id):
    try:
        return str(int(float(vk_id)))
    except (TypeError, ValueError):
        return str(vk_id)

def _vk_with_dot(vk_id):
    vk_str = _vk_to_str(vk_id)
    try:
        return str(float(vk_str))
    except (TypeError, ValueError):
        return vk_str

def invalidate_cache(vk_id=None):
    """Сбросить кэш строк. Нужен, если строки в таблице правили руками:
    номера сдвигаются, и бот начнёт писать данные одного гостя в строку другого."""
    if vk_id is None:
        _vk_cache.clear()
        _verified_guests.clear()
    else:
        _vk_cache.pop(_vk_to_str(vk_id), None)
        _verified_guests.discard(_vk_to_str(vk_id))


def _row_from_append_response(response):
    """Номер добавленной строки из ответа append_row ("'Гости'!A5:N5" -> 5).

    Считать его как len(col_values(1)) нельзя: это лишний запрос к API и
    неверный результат, если в колонке A есть пропуски.
    """
    try:
        updated_range = response['updates']['updatedRange']
    except (KeyError, TypeError):
        return None
    match = re.search(r'![A-Z]+(\d+)', updated_range)
    return int(match.group(1)) if match else None


def find_row_by_vk(vk_id):
    vk_str = _vk_to_str(vk_id)
    vk_dot = _vk_with_dot(vk_id)

    # Проверяем кэш
    if vk_str in _vk_cache:
        return _vk_cache[vk_str]

    try:
        col_a = get_sheet().col_values(1)
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
        response = get_sheet().append_row(row)
        # Обновляем кэш
        row_num = _row_from_append_response(response)
        if row_num is not None:
            _vk_cache[vk_str] = row_num
        logger.info(f"✅ Добавлен гость {vk_id} в Google Sheets")
    except Exception as e:
        logger.error(f"Ошибка добавления гостя {vk_id} в Google Sheets: {e}")

def update_guest_sheet(vk_id, **kwargs):
    try:
        row_num = find_row_by_vk(vk_id)
        if row_num is None:
            logger.warning(f"⚠️ Строка для vk_id {vk_id} не найдена. Попробуйте вызвать ensure_guest_in_sheet")
            return

        unknown = set(kwargs) - set(GUEST_COLUMNS)
        if unknown:
            logger.warning(f"⚠️ Нет колонки в таблице для полей: {', '.join(sorted(unknown))}")

        updates = [
            {'range': f'{GUEST_COLUMNS[field]}{row_num}', 'values': [[value]]}
            for field, value in kwargs.items()
            if field in GUEST_COLUMNS
        ]
        if not updates:
            return
        get_sheet().batch_update(updates)
        logger.info(f"✅ Обновлены данные для гостя {vk_id} в строке {row_num}")
    except Exception as e:
        logger.error(f"Ошибка обновления Google Sheets: {e}")

def get_today_master():
    try:
        records = get_spreadsheet().worksheet("Мастера").get_all_records()
    except Exception as e:
        logger.error(f"Ошибка при получении мастера: {e}")
        return DEFAULT_MASTER

    today_day = datetime.now().day
    for row in records:
        try:
            day = int(row.get('День', -1))
        except (TypeError, ValueError):
            # Одна строка с нечисловым «Днём» не должна отменять весь перебор
            continue
        if day == today_day:
            return row.get('Имя', 'Мастер'), row.get('Телефон', 'Не указан')

    logger.warning(f"⚠️ В листе «Мастера» нет строки на {today_day} число")
    return DEFAULT_MASTER

def _read_guest_row(sheet, row_num):
    """Первые четыре колонки строки, дополненные до полной длины:
    row_values обрезает пустые ячейки справа."""
    current_row = sheet.row_values(row_num)
    current_row += [''] * (4 - len(current_row))
    return current_row


def ensure_guest_in_sheet(vk_id, guest_data):
    """Проверяет, что гость есть в таблице, и восстанавливает потерянные телефон
    и дату рождения.

    Вызывается на каждое входящее сообщение, поэтому результат запоминается:
    иначе каждое сообщение стоило бы отдельного запроса к API, а квота Sheets –
    60 запросов в минуту на пользователя.
    """
    vk_str = _vk_to_str(vk_id)
    if vk_str in _verified_guests:
        return
    try:
        sheet = get_sheet()
        row_num = find_row_by_vk(vk_id)
        current_row = None

        if row_num is not None:
            current_row = _read_guest_row(sheet, row_num)
            if _vk_to_str(current_row[0]) != vk_str:
                # Строки в таблице переставили или удалили – кэш указывает не туда
                logger.warning(f"⚠️ Кэш строки для гостя {vk_id} протух, ищу заново")
                invalidate_cache(vk_id)
                row_num = find_row_by_vk(vk_id)
                current_row = _read_guest_row(sheet, row_num) if row_num else None

        if row_num is None:
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
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
            response = sheet.append_row(row)
            new_row_num = _row_from_append_response(response)
            if new_row_num is not None:
                _vk_cache[vk_str] = new_row_num
            logger.info(f"✅ Добавлена новая строка для гостя {vk_id} в Google Sheets")
        else:
            if not current_row[2] and guest_data[2]:
                sheet.update_cell(row_num, 3, guest_data[2])
                logger.info(f"🔄 Восстановлен телефон для гостя {vk_id}")
            if not current_row[3] and guest_data[3]:
                sheet.update_cell(row_num, 4, guest_data[3])
                logger.info(f"🔄 Восстановлена дата рождения для гостя {vk_id}")
        _verified_guests.add(vk_str)
    except Exception as e:
        logger.error(f"⚠️ Ошибка при проверке/восстановлении гостя в Google Sheets: {e}")
