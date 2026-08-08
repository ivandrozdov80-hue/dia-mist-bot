# utils.py
import random
import qrcode
from io import BytesIO
from datetime import datetime  # ← Добавляем импорт
import database as db
import google_sheets as gs
from config import LEVELS, LEVEL_NAMES, GROUP_ID, logger, FREE_HOOKAH_VISITS

def get_level_by_visits(visits):
    lvl = 1
    for lvl_num, need in sorted(LEVELS.items(), key=lambda x: x[1]):
        if visits >= need:
            lvl = lvl_num
    return lvl

def generate_visit_code(guest_id):
    code = random.randint(100000, 999999)
    db.add_code(code, guest_id)
    return code

def create_qr_image(code):
    link = f"https://vk.me/club{GROUP_ID}?text=визит%20{code}"
    qr = qrcode.make(link)
    bio = BytesIO()
    qr.save(bio, 'PNG')
    bio.seek(0)
    return bio

def apply_visit(user_id, code=None, send_message_func=None):
    guest = db.get_guest(user_id)
    if not guest:
        logger.error(f"Гость {user_id} не найден при попытке засчитать визит")
        return None

    visits = int(guest[5]) if guest[5] is not None else 0
    current_level = int(guest[6]) if guest[6] is not None else 1
    free_visits_used = int(guest[19]) if len(guest) > 19 and guest[19] is not None else 0
    cycles_completed = int(guest[20]) if len(guest) > 20 and guest[20] is not None else 0

    if code is not None:
        row = db.get_valid_code(code)
        if not row:
            if send_message_func:
                send_message_func(user_id, "❌ Неверный или просроченный код.")
            return None
        if row[1] != user_id:
            if send_message_func:
                send_message_func(user_id, "😤 Этот код не для тебя!")
            return None

    free_used = db.use_free_visit(user_id)

    if free_used:
        new_visits = visits + 1
        new_level = get_level_by_visits(new_visits)
        db.cursor.execute(
            "UPDATE guests SET visits=?, level=?, updated_at=? WHERE vk_id=?",
            (new_visits, new_level, datetime.now().isoformat(), user_id)
        )
        db.conn.commit()
        if code is not None:
            db.mark_code_used(code)
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        gs.update_guest_sheet(user_id, visits=new_visits, level=new_level, free_visit_available=0, visits_in_cycle=0, updated_at=now_str)
        db.update_guest(user_id, free_visits_used=free_visits_used + 1)
        guest = db.get_guest(user_id)

        level_name = LEVEL_NAMES.get(new_level, "Новичок")
        ach_count = 0
        promo_line = f"🔥 Следующий бесплатный кальян: 0/{FREE_HOOKAH_VISITS} визитов"
        reached_six = False

        return (new_visits, new_level, level_name, ach_count, promo_line, reached_six, True)

    reached_six = db.increment_cycle(user_id)
    new_visits = visits + 1
    new_level = get_level_by_visits(new_visits)
    db.cursor.execute(
        "UPDATE guests SET visits=?, level=?, updated_at=? WHERE vk_id=?",
        (new_visits, new_level, datetime.now().isoformat(), user_id)
    )
    db.conn.commit()
    if code is not None:
        db.mark_code_used(code)

    cycle_info = db.get_cycle_info(user_id)
    visits_in_cycle, free_available = cycle_info
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    gs.update_guest_sheet(
        user_id,
        visits=new_visits,
        level=new_level,
        visits_in_cycle=visits_in_cycle,
        free_visit_available=free_available,
        updated_at=now_str
    )
    if reached_six:
        db.update_guest(user_id, cycles_completed=cycles_completed + 1)

    guest = db.get_guest(user_id)

    level_name = LEVEL_NAMES.get(new_level, "Новичок")
    ach_count = 0

    if free_available == 1:
        promo_line = "🎁 Ты накопил на бесплатный кальян! Следующий визит – бесплатный!"
    else:
        remaining = FREE_HOOKAH_VISITS - visits_in_cycle
        promo_line = f"🔥 Бесплатный кальян: {visits_in_cycle}/{FREE_HOOKAH_VISITS} визитов (осталось {remaining})"

    return (new_visits, new_level, level_name, ach_count, promo_line, reached_six, False)