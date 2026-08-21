# database.py
import sqlite3
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="bot_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Создание таблицы, если её нет"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guests (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT,
                    birth_date TEXT,
                    consent INTEGER DEFAULT 0,
                    visits INTEGER DEFAULT 0,
                    free_visits INTEGER DEFAULT 0,
                    active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        logger.info("✅ База данных SQLite инициализирована")

    def add_guest(self, guest_data):
        """Добавить гостя в БД"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO guests 
                    (id, name, phone, birth_date, consent, visits, free_visits, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    guest_data["id"],
                    guest_data["name"],
                    guest_data.get("phone", ""),
                    guest_data.get("birth_date", ""),
                    guest_data.get("consent", 0),
                    guest_data.get("visits", 0),
                    guest_data.get("free_visits", 0),
                    guest_data.get("active", 1),
                    guest_data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                ))
                conn.commit()
            logger.info(f"✅ Гость {guest_data['id']} добавлен в SQLite")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в SQLite: {e}")
            return False

    def get_guest(self, guest_id):
        """Получить гостя по ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guests WHERE id = ?", (guest_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "phone": row[2],
                    "birth_date": row[3],
                    "consent": row[4],
                    "visits": row[5],
                    "free_visits": row[6],
                    "active": row[7],
                    "created_at": row[8]
                }
            return None

    def delete_guest(self, guest_id):
        """Удалить гостя из БД"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM guests WHERE id = ?", (guest_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка удаления из SQLite: {e}")
            return False

    def update_guest(self, guest_id, updates):
        """Обновить данные гостя"""
        try:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            values = list(updates.values()) + [guest_id]
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE guests SET {set_clause} WHERE id = ?", values)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"❌ Ошибка обновления: {e}")
            return False

    def get_all_guests(self):
        """Получить всех гостей"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guests")
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0], "name": r[1], "phone": r[2],
                    "birth_date": r[3], "consent": r[4],
                    "visits": r[5], "free_visits": r[6],
                    "active": r[7], "created_at": r[8]
                }
                for r in rows
            ]