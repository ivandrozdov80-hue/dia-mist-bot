# database.py
import sqlite3
from datetime import datetime
import logging
from config import FREE_HOOKAH_VISITS, PRIZES  # добавлен импорт PRIZES
import random  # добавлен импорт random

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="bot_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS guests (
                    vk_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    birth TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    visits INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    updated_at TEXT,
                    registration_step INTEGER DEFAULT 0,
                    last_activity TEXT,
                    last_reminder TEXT,
                    visits_in_cycle INTEGER DEFAULT 0,
                    free_visit_available INTEGER DEFAULT 0,
                    agreement_given INTEGER DEFAULT 0,
                    command_counts TEXT DEFAULT '{}',
                    raffle_participations INTEGER DEFAULT 0,
                    free_visits_used INTEGER DEFAULT 0,
                    cycles_completed INTEGER DEFAULT 0,
                    awaiting_review INTEGER DEFAULT 0,
                    last_request_time TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS visit_codes (
                    code INTEGER PRIMARY KEY,
                    vk_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    used INTEGER DEFAULT 0
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS raffles (
                    raffle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prize TEXT,
                    status TEXT DEFAULT 'active',
                    winner_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS raffle_participants (
                    raffle_id INTEGER,
                    vk_id INTEGER,
                    PRIMARY KEY (raffle_id, vk_id)
                )
            """)
        self._migrate()

    def _migrate(self):
        """Автоматически добавляет недостающие колонки в существующую таблицу."""
        try:
            columns = [row[1] for row in self.cursor.execute("PRAGMA table_info(guests)").fetchall()]
            if 'agreement_given' not in columns:
                self.cursor.execute("ALTER TABLE guests ADD COLUMN agreement_given INTEGER DEFAULT 0")
                logger.info("✅ Добавлена колонка agreement_given")
            if 'awaiting_review' not in columns:
                self.cursor.execute("ALTER TABLE guests ADD COLUMN awaiting_review INTEGER DEFAULT 0")
                logger.info("✅ Добавлена колонка awaiting_review")
            if 'last_request_time' not in columns:
                self.cursor.execute("ALTER TABLE guests ADD COLUMN last_request_time TEXT")
                logger.info("✅ Добавлена колонка last_request_time")
            
            # ИСПРАВЛЕНИЕ: Миграция для таблицы розыгрышей
            try:
                raffle_columns = [row[1] for row in self.cursor.execute("PRAGMA table_info(raffles)").fetchall()]
                if 'raffle_id' not in raffle_columns:
                    logger.info("🔄 Обнаружена старая таблица raffles. Полностью пересоздаю...")
                    self.cursor.execute("DROP TABLE IF EXISTS raffles")
                    self.cursor.execute("""
                        CREATE TABLE raffles (
                            raffle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            prize TEXT,
                            status TEXT DEFAULT 'active',
                            winner_id INTEGER,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    self.cursor.execute("DROP TABLE IF EXISTS raffle_participants")  # пересоздаём и связанную таблицу
                    self.cursor.execute("""
                        CREATE TABLE raffle_participants (
                            raffle_id INTEGER,
                            vk_id INTEGER,
                            PRIMARY KEY (raffle_id, vk_id)
                        )
                    """)
                    self.conn.commit()
                    logger.info("✅ Таблица raffles успешно пересоздана!")
            except Exception as e:
                logger.error(f"Ошибка миграции raffles: {e}")
                
            self.conn.commit()
        except Exception as e:
            logger.error(f"Ошибка миграции: {e}")

    # ==================== ГОСТИ ====================
    def add_guest(self, vk_id, name):
        try:
            with self.conn:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO guests (vk_id, name, created_at, updated_at, registration_step)
                    VALUES (?, ?, ?, ?, 0)
                """, (vk_id, name, datetime.now().isoformat(), datetime.now().isoformat()))
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления гостя: {e}")
            return False

    def get_guest(self, vk_id):
        self.cursor.execute("SELECT * FROM guests WHERE vk_id = ?", (vk_id,))
        row = self.cursor.fetchone()
        if row:
            return tuple(row)
        return None

    def update_guest(self, vk_id, **kwargs):
        if not kwargs:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [vk_id]
        with self.conn:
            self.cursor.execute(f"UPDATE guests SET {set_clause} WHERE vk_id = ?", values)
        return True

    def delete_guest(self, vk_id):
        with self.conn:
            self.cursor.execute("DELETE FROM guests WHERE vk_id = ?", (vk_id,))
        return self.cursor.rowcount > 0

    def get_all_guests(self):
        self.cursor.execute("SELECT * FROM guests")
        rows = self.cursor.fetchall()
        return [tuple(r) for r in rows]

    def update_activity(self, vk_id):
        now = datetime.now().isoformat()
        self.update_guest(vk_id, last_activity=now, updated_at=now)

    # ==================== ВИЗИТЫ ====================
    def get_last_request_time(self, vk_id):
        self.cursor.execute("SELECT last_request_time FROM guests WHERE vk_id = ?", (vk_id,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def update_last_request_time(self, vk_id):
        self.update_guest(vk_id, last_request_time=datetime.now().isoformat())

    def use_free_visit(self, vk_id):
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        free_available = self.get_guest_column_value(guest, 'free_visit_available')
        if free_available == 1:
            self.update_guest(vk_id, free_visit_available=0, visits_in_cycle=0)
            return True
        return False

    def increment_cycle(self, vk_id):
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        visits_in_cycle = self.get_guest_column_value(guest, 'visits_in_cycle')
        new_visits_in_cycle = visits_in_cycle + 1
        if new_visits_in_cycle >= FREE_HOOKAH_VISITS:
            self.update_guest(vk_id, visits_in_cycle=0, free_visit_available=1)
            return True
        else:
            self.update_guest(vk_id, visits_in_cycle=new_visits_in_cycle)
            return False

    def get_cycle_info(self, vk_id):
        guest = self.get_guest(vk_id)
        if not guest:
            return (0, 0)
        return (self.get_guest_column_value(guest, 'visits_in_cycle'), self.get_guest_column_value(guest, 'free_visit_available'))

    def get_guest_column_value(self, guest, column_name):
        """Возвращает значение колонки по имени, ища его в кортеже гостя."""
        try:
            # Получаем список колонок из таблицы
            cols = [row[1] for row in self.cursor.execute("PRAGMA table_info(guests)").fetchall()]
            if column_name in cols:
                idx = cols.index(column_name)
                return guest[idx] if idx < len(guest) else 0
        except Exception as e:
            logger.error(f"Ошибка получения колонки {column_name}: {e}")
        return 0

    # ==================== КОДЫ ВИЗИТОВ ====================
    def add_code(self, code, vk_id):
        with self.conn:
            self.cursor.execute("""
                INSERT INTO visit_codes (code, vk_id, created_at, used)
                VALUES (?, ?, ?, 0)
            """, (code, vk_id, datetime.now().isoformat()))

    def get_valid_code(self, code):
        self.cursor.execute("SELECT code, vk_id FROM visit_codes WHERE code = ? AND used = 0", (code,))
        row = self.cursor.fetchone()
        if row:
            return (row[0], row[1])
        return None

    def mark_code_used(self, code):
        with self.conn:
            self.cursor.execute("UPDATE visit_codes SET used = 1 WHERE code = ?", (code,))

    # ==================== ОТЗЫВЫ ====================
    def set_awaiting_review(self, vk_id, awaiting):
        self.update_guest(vk_id, awaiting_review=1 if awaiting else 0)

    def get_awaiting_review(self, vk_id):
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        return self.get_guest_column_value(guest, 'awaiting_review') == 1

    # ==================== РОЗЫГРЫШИ ====================
    def create_raffle(self, prize=None):
        if not prize:
            prize = random.choice(PRIZES)  # выбираем случайный из списка
        with self.conn:
            self.cursor.execute("""
                INSERT INTO raffles (prize, status, created_at)
                VALUES (?, 'active', ?)
            """, (prize, datetime.now().isoformat()))
        return self.cursor.lastrowid

    def get_active_raffle(self):
        self.cursor.execute("SELECT raffle_id, prize FROM raffles WHERE status = 'active' LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return (row[0], row[1])
        return None

    def get_raffle_participants(self, raffle_id):
        self.cursor.execute("SELECT vk_id FROM raffle_participants WHERE raffle_id = ?", (raffle_id,))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows]

    def add_raffle_participant(self, raffle_id, vk_id):
        with self.conn:
            self.cursor.execute("""
                INSERT OR IGNORE INTO raffle_participants (raffle_id, vk_id)
                VALUES (?, ?)
            """, (raffle_id, vk_id))
        return self.cursor.rowcount > 0

    def is_raffle_participant(self, raffle_id, vk_id):
        self.cursor.execute("SELECT 1 FROM raffle_participants WHERE raffle_id = ? AND vk_id = ?", (raffle_id, vk_id))
        return self.cursor.fetchone() is not None

    def finish_raffle(self, raffle_id, winner_id):
        with self.conn:
            self.cursor.execute("""
                UPDATE raffles SET status = 'finished', winner_id = ? WHERE raffle_id = ?
            """, (winner_id, raffle_id))

    def close(self):
        self.conn.close()


# ============================================================
# МОДУЛЬНЫЕ ФУНКЦИИ-ОБЕРТКИ (для совместимости с main.py)
# ============================================================
def get_guest(vk_id):
    db = Database()
    return db.get_guest(vk_id)

def add_guest(vk_id, name):
    db = Database()
    return db.add_guest(vk_id, name)

def update_guest(vk_id, **kwargs):
    db = Database()
    return db.update_guest(vk_id, **kwargs)

def delete_guest(vk_id):
    db = Database()
    return db.delete_guest(vk_id)

def get_all_guests():
    db = Database()
    return db.get_all_guests()

def update_activity(vk_id):
    db = Database()
    return db.update_activity(vk_id)

def get_last_request_time(vk_id):
    db = Database()
    return db.get_last_request_time(vk_id)

def update_last_request_time(vk_id):
    db = Database()
    return db.update_last_request_time(vk_id)

def use_free_visit(vk_id):
    db = Database()
    return db.use_free_visit(vk_id)

def increment_cycle(vk_id):
    db = Database()
    return db.increment_cycle(vk_id)

def get_cycle_info(vk_id):
    db = Database()
    return db.get_cycle_info(vk_id)

def add_code(code, vk_id):
    db = Database()
    return db.add_code(code, vk_id)

def get_valid_code(code):
    db = Database()
    return db.get_valid_code(code)

def mark_code_used(code):
    db = Database()
    return db.mark_code_used(code)

def set_awaiting_review(vk_id, awaiting):
    db = Database()
    return db.set_awaiting_review(vk_id, awaiting)

def get_awaiting_review(vk_id):
    db = Database()
    return db.get_awaiting_review(vk_id)

def create_raffle(prize=None):
    db = Database()
    return db.create_raffle(prize)

def get_active_raffle():
    db = Database()
    return db.get_active_raffle()

def get_raffle_participants(raffle_id):
    db = Database()
    return db.get_raffle_participants(raffle_id)

def add_raffle_participant(raffle_id, vk_id):
    db = Database()
    return db.add_raffle_participant(raffle_id, vk_id)

def is_raffle_participant(raffle_id, vk_id):
    db = Database()
    return db.is_raffle_participant(raffle_id, vk_id)

def finish_raffle(raffle_id, winner_id):
    db = Database()
    return db.finish_raffle(raffle_id, winner_id)

def get_guest_column_value(guest, column_name):
    """
    Возвращает значение колонки по имени для гостя (кортежа).
    Использует глобальный экземпляр базы данных.
    """
    return _global_db.get_guest_column_value(guest, column_name)

# ============================================================
# ГЛОБАЛЬНЫЙ ИНСТАНС ДЛЯ СОВМЕСТИМОСТИ С main.py (db.conn, db.cursor)
# ============================================================
_global_db = Database()
conn = _global_db.conn
cursor = _global_db.cursor