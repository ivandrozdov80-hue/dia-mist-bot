# database.py
import sqlite3
from datetime import datetime
import logging
from config import FREE_HOOKAH_VISITS

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="bot_data.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        """Создание таблиц, если их нет."""
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
                    cycles_completed INTEGER DEFAULT 0
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
        logger.info("✅ База данных инициализирована")

    # ==================== ГОСТИ ====================
    def add_guest(self, vk_id, name):
        """Добавляет нового гостя."""
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
        """Возвращает гостя как кортеж."""
        self.cursor.execute("SELECT * FROM guests WHERE vk_id = ?", (vk_id,))
        row = self.cursor.fetchone()
        if row:
            return tuple(row)
        return None

    def update_guest(self, vk_id, **kwargs):
        """Обновляет поля гостя."""
        if not kwargs:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [vk_id]
        with self.conn:
            self.cursor.execute(f"UPDATE guests SET {set_clause} WHERE vk_id = ?", values)
        return True

    def delete_guest(self, vk_id):
        """Удаляет гостя."""
        with self.conn:
            self.cursor.execute("DELETE FROM guests WHERE vk_id = ?", (vk_id,))
        return self.cursor.rowcount > 0

    def get_all_guests(self):
        """Возвращает список всех гостей (кортежи)."""
        self.cursor.execute("SELECT * FROM guests")
        rows = self.cursor.fetchall()
        return [tuple(r) for r in rows]

    def update_activity(self, vk_id):
        """Обновляет время последней активности."""
        now = datetime.now().isoformat()
        self.update_guest(vk_id, last_activity=now, updated_at=now)

    # ==================== ВИЗИТЫ ====================
    def get_last_request_time(self, vk_id):
        """Возвращает время последнего запроса на визит."""
        self.cursor.execute("SELECT last_request_time FROM guests WHERE vk_id = ?", (vk_id,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None

    def update_last_request_time(self, vk_id):
        """Обновляет время последнего запроса."""
        self.update_guest(vk_id, last_request_time=datetime.now().isoformat())

    def use_free_visit(self, vk_id):
        """Использует бесплатный визит, если доступен."""
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        free_available = guest[13] if len(guest) > 13 else 0
        if free_available == 1:
            self.update_guest(vk_id, free_visit_available=0, visits_in_cycle=0)
            return True
        return False

    def increment_cycle(self, vk_id):
        """Увеличивает счётчик цикла и возвращает True, если достигнут бесплатный визит."""
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        visits_in_cycle = guest[12] if len(guest) > 12 else 0
        new_visits_in_cycle = visits_in_cycle + 1
        if new_visits_in_cycle >= FREE_HOOKAH_VISITS:
            self.update_guest(vk_id, visits_in_cycle=0, free_visit_available=1)
            return True
        else:
            self.update_guest(vk_id, visits_in_cycle=new_visits_in_cycle)
            return False

    def get_cycle_info(self, vk_id):
        """Возвращает (visits_in_cycle, free_available)."""
        guest = self.get_guest(vk_id)
        if not guest:
            return (0, 0)
        return (guest[12] if len(guest) > 12 else 0, guest[13] if len(guest) > 13 else 0)

    # ==================== КОДЫ ВИЗИТОВ ====================
    def add_code(self, code, vk_id):
        """Добавляет код визита."""
        with self.conn:
            self.cursor.execute("""
                INSERT INTO visit_codes (code, vk_id, created_at, used)
                VALUES (?, ?, ?, 0)
            """, (code, vk_id, datetime.now().isoformat()))

    def get_valid_code(self, code):
        """Возвращает кортеж (code, vk_id) для неиспользованного кода."""
        self.cursor.execute("SELECT code, vk_id FROM visit_codes WHERE code = ? AND used = 0", (code,))
        row = self.cursor.fetchone()
        if row:
            return (row[0], row[1])
        return None

    def mark_code_used(self, code):
        """Помечает код использованным."""
        with self.conn:
            self.cursor.execute("UPDATE visit_codes SET used = 1 WHERE code = ?", (code,))

    # ==================== ОТЗЫВЫ ====================
    def set_awaiting_review(self, vk_id, awaiting):
        """Устанавливает флаг ожидания отзыва."""
        self.update_guest(vk_id, awaiting_review=1 if awaiting else 0)

    def get_awaiting_review(self, vk_id):
        """Возвращает True, если гость ожидает отзыва."""
        guest = self.get_guest(vk_id)
        if not guest:
            return False
        return guest[20] == 1 if len(guest) > 20 else False

    # ==================== РОЗЫГРЫШИ ====================
    def create_raffle(self, prize=None):
        """Создаёт новый активный розыгрыш."""
        if not prize:
            prize = "Приз"
        with self.conn:
            self.cursor.execute("""
                INSERT INTO raffles (prize, status, created_at)
                VALUES (?, 'active', ?)
            """, (prize, datetime.now().isoformat()))
        return self.cursor.lastrowid

    def get_active_raffle(self):
        """Возвращает (raffle_id, prize) активного розыгрыша или None."""
        self.cursor.execute("SELECT raffle_id, prize FROM raffles WHERE status = 'active' LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            return (row[0], row[1])
        return None

    def get_raffle_participants(self, raffle_id):
        """Возвращает список vk_id участников розыгрыша."""
        self.cursor.execute("SELECT vk_id FROM raffle_participants WHERE raffle_id = ?", (raffle_id,))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows]

    def add_raffle_participant(self, raffle_id, vk_id):
        """Добавляет участника в розыгрыш."""
        with self.conn:
            self.cursor.execute("""
                INSERT OR IGNORE INTO raffle_participants (raffle_id, vk_id)
                VALUES (?, ?)
            """, (raffle_id, vk_id))
        return self.cursor.rowcount > 0

    def is_raffle_participant(self, raffle_id, vk_id):
        """Проверяет, участвует ли гость в розыгрыше."""
        self.cursor.execute("SELECT 1 FROM raffle_participants WHERE raffle_id = ? AND vk_id = ?", (raffle_id, vk_id))
        return self.cursor.fetchone() is not None

    def finish_raffle(self, raffle_id, winner_id):
        """Завершает розыгрыш, сохраняет победителя."""
        with self.conn:
            self.cursor.execute("""
                UPDATE raffles SET status = 'finished', winner_id = ? WHERE raffle_id = ?
            """, (winner_id, raffle_id))

    # ==================== ДОПОЛНИТЕЛЬНО ====================
    def close(self):
        self.conn.close()


# ===== Модульная функция для совместимости =====
def get_all_guests():
    """Возвращает список всех гостей."""
    db = Database()
    return db.get_all_guests()