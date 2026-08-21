# database.py
import sqlite3
from datetime import datetime, timedelta
import json
from config import logger, FREE_HOOKAH_VISITS

conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()


def init_db():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS guests (
        vk_id INTEGER PRIMARY KEY,
        name TEXT,
        phone TEXT,
        birth TEXT,
        created_at TEXT,
        visits INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        updated_at TEXT,
        registration_step INTEGER DEFAULT 0,
        last_activity TEXT,
        last_reminder TEXT,
        visits_in_cycle INTEGER DEFAULT 0,
        free_visit_available INTEGER DEFAULT 0,
        total_messages INTEGER DEFAULT 0,
        unique_days TEXT DEFAULT '',
        command_counts TEXT DEFAULT '{}',
        raffle_participations INTEGER DEFAULT 0,
        raffle_wins INTEGER DEFAULT 0,
        free_visits_used INTEGER DEFAULT 0,
        cycles_completed INTEGER DEFAULT 0,
        wrong_phone_attempts INTEGER DEFAULT 0,
        last_request_time TEXT,
        awaiting_review INTEGER DEFAULT 0,
        agreement_given INTEGER DEFAULT 0,
        admin_chat_mode INTEGER DEFAULT 0
    )
    ''')

    columns_to_add = {
        'registration_step': 'INTEGER DEFAULT 0',
        'last_activity': 'TEXT',
        'last_reminder': 'TEXT',
        'visits_in_cycle': 'INTEGER DEFAULT 0',
        'free_visit_available': 'INTEGER DEFAULT 0',
        'total_messages': 'INTEGER DEFAULT 0',
        'unique_days': 'TEXT DEFAULT ""',
        'command_counts': 'TEXT DEFAULT "{}"',
        'raffle_participations': 'INTEGER DEFAULT 0',
        'raffle_wins': 'INTEGER DEFAULT 0',
        'free_visits_used': 'INTEGER DEFAULT 0',
        'cycles_completed': 'INTEGER DEFAULT 0',
        'wrong_phone_attempts': 'INTEGER DEFAULT 0',
        'last_request_time': 'TEXT',
        'awaiting_review': 'INTEGER DEFAULT 0',
        'agreement_given': 'INTEGER DEFAULT 0',
        'admin_chat_mode': 'INTEGER DEFAULT 0'
    }
    
    for col, col_type in columns_to_add.items():
        try:
            cursor.execute(f'ALTER TABLE guests ADD COLUMN {col} {col_type}')
            logger.info(f"✅ Добавлена колонка {col}")
        except sqlite3.OperationalError:
            logger.info(f"ℹ️ Колонка {col} уже существует")

    # Таблицы для кодов, розыгрышей и отзывов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS visit_codes (
        code INTEGER PRIMARY KEY,
        guest_id INTEGER,
        generated_at TEXT,
        expires_at TEXT,
        used BOOLEAN DEFAULT FALSE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS raffles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prize TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT,
        end_at TEXT,
        winner_id INTEGER
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS raffle_participants (
        raffle_id INTEGER,
        user_id INTEGER,
        PRIMARY KEY (raffle_id, user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rating INTEGER,
        text TEXT,
        created_at TEXT,
        posted_to_vk BOOLEAN DEFAULT 0
    )
    ''')

    # Индексы
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_guest_vk ON guests(vk_id);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_activity ON guests(last_activity);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_request_time ON guests(last_request_time);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_phone ON guests(phone);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_agreement ON guests(agreement_given);')
        conn.commit()
        logger.info("✅ Индексы созданы")
    except Exception as e:
        logger.error(f"Ошибка при создании индексов: {e}")

    conn.commit()
    logger.info("✅ База данных инициализирована")


def get_guest(vk_id):
    cursor.execute("SELECT * FROM guests WHERE vk_id=?", (vk_id,))
    return cursor.fetchone()


def add_guest(vk_id, name):
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO guests (vk_id, name, created_at, updated_at, registration_step, last_activity, visits_in_cycle, free_visit_available) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (vk_id, name, now, now, 1, now, 0, 0)
    )
    conn.commit()


def update_guest(vk_id, **kwargs):
    if not kwargs:
        return
    set_clause = ", ".join([f"{k}=?" for k in kwargs.keys()])
    values = list(kwargs.values()) + [vk_id]
    cursor.execute(
        f"UPDATE guests SET {set_clause}, updated_at=? WHERE vk_id=?",
        values + [datetime.now().isoformat()]
    )
    conn.commit()


def update_activity(vk_id):
    now = datetime.now().isoformat()
    cursor.execute("UPDATE guests SET last_activity=? WHERE vk_id=?", (now, vk_id))
    conn.commit()


def get_cycle_info(vk_id):
    cursor.execute("SELECT visits_in_cycle, free_visit_available FROM guests WHERE vk_id=?", (vk_id,))
    row = cursor.fetchone()
    if row:
        return (row[0] or 0, row[1] or 0)
    return (0, 0)


def increment_cycle(vk_id):
    cursor.execute("SELECT visits_in_cycle FROM guests WHERE vk_id=?", (vk_id,))
    row = cursor.fetchone()
    if row:
        current = row[0] or 0
        new_val = current + 1
        if new_val >= FREE_HOOKAH_VISITS:
            cursor.execute(
                "UPDATE guests SET visits_in_cycle=?, free_visit_available=1 WHERE vk_id=?",
                (FREE_HOOKAH_VISITS, vk_id)
            )
            conn.commit()
            return True
        else:
            cursor.execute("UPDATE guests SET visits_in_cycle=? WHERE vk_id=?", (new_val, vk_id))
            conn.commit()
            return False
    return False


def reset_cycle(vk_id):
    cursor.execute("UPDATE guests SET visits_in_cycle=0, free_visit_available=0 WHERE vk_id=?", (vk_id,))
    conn.commit()


def use_free_visit(vk_id):
    cursor.execute("SELECT free_visit_available FROM guests WHERE vk_id=?", (vk_id,))
    row = cursor.fetchone()
    if row and row[0] == 1:
        reset_cycle(vk_id)
        return True
    return False


def add_code(code, guest_id):
    expires = datetime.now() + timedelta(hours=1)
    cursor.execute(
        "INSERT INTO visit_codes (code, guest_id, generated_at, expires_at, used) VALUES (?,?,?,?,?)",
        (code, guest_id, datetime.now().isoformat(), expires.isoformat(), False)
    )
    conn.commit()
    return code


def get_valid_code(code):
    cursor.execute(
        "SELECT * FROM visit_codes WHERE code=? AND used=0 AND expires_at > ?",
        (code, datetime.now().isoformat())
    )
    return cursor.fetchone()


def mark_code_used(code):
    cursor.execute("UPDATE visit_codes SET used=1 WHERE code=?", (code,))
    conn.commit()


def get_last_request_time(vk_id):
    cursor.execute("SELECT last_request_time FROM guests WHERE vk_id=?", (vk_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def update_last_request_time(vk_id):
    now = datetime.now().isoformat()
    cursor.execute("UPDATE guests SET last_request_time=? WHERE vk_id=?", (now, vk_id))
    conn.commit()


def set_awaiting_review(user_id, status):
    cursor.execute("UPDATE guests SET awaiting_review=? WHERE vk_id=?", (1 if status else 0, user_id))
    conn.commit()


def get_awaiting_review(user_id):
    cursor.execute("SELECT awaiting_review FROM guests WHERE vk_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] == 1 if row else False


def add_review(user_id, rating=None, text=None):
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO reviews (user_id, rating, text, created_at, posted_to_vk) VALUES (?,?,?,?,?)",
        (user_id, rating, text, now, 0)
    )
    conn.commit()
    return cursor.lastrowid


def get_unposted_reviews():
    cursor.execute("SELECT id, user_id, rating, text, created_at FROM reviews WHERE posted_to_vk=0")
    return cursor.fetchall()


def mark_review_posted(review_id):
    cursor.execute("UPDATE reviews SET posted_to_vk=1 WHERE id=?", (review_id,))
    conn.commit()


def get_all_reviews(limit=50):
    cursor.execute(
        "SELECT id, user_id, rating, text, created_at, posted_to_vk FROM reviews ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    return cursor.fetchall()


def get_active_raffle():
    cursor.execute("SELECT * FROM raffles WHERE status='active' ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


def create_raffle(prize=None):
    if prize is None:
        from config import PRIZES
        import random
        prize = random.choice(PRIZES)
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO raffles (prize, status, created_at) VALUES (?, 'active', ?)",
        (prize, now)
    )
    conn.commit()
    return cursor.lastrowid


def get_raffle_participants(raffle_id):
    cursor.execute("SELECT user_id FROM raffle_participants WHERE raffle_id=?", (raffle_id,))
    return [row[0] for row in cursor.fetchall()]


def add_raffle_participant(raffle_id, user_id):
    try:
        cursor.execute("INSERT INTO raffle_participants (raffle_id, user_id) VALUES (?,?)", (raffle_id, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def is_raffle_participant(raffle_id, user_id):
    cursor.execute("SELECT 1 FROM raffle_participants WHERE raffle_id=? AND user_id=?", (raffle_id, user_id))
    return cursor.fetchone() is not None


def finish_raffle(raffle_id, winner_id):
    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE raffles SET status='finished', end_at=?, winner_id=? WHERE id=?",
        (now, winner_id, raffle_id)
    )
    conn.commit()


def get_last_finished_raffle():
    cursor.execute("SELECT * FROM raffles WHERE status='finished' ORDER BY id DESC LIMIT 1")
    return cursor.fetchone()


init_db()