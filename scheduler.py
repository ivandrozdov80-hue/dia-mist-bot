# scheduler.py
import schedule
import time
import threading
import random
from datetime import datetime, timedelta
import database as db
import google_sheets as gs
from config import GROUP_ID, logger

REMINDER_MESSAGES = [
    "🧞 Эй, {name}! Я тут скучаю по твоему дыму! Давно не виделись. У нас новый вкус – «Черничный бум». Приходи, попробуем вместе?",
    "🍃 {name}, ты где пропал? Джинн Dia Mist уже заждался! Кстати, на этой неделе розыгрыш – может, повезёт? 😉",
    "🔥 О, {name}! Ты забыл, что у нас самый вкусный кальян в городе? Напоминаю: скидка 10% для старых друзей. Жду!",
    "💨 {name}, хочешь прокачать свой уровень? Тебе не хватает всего пары визитов до следующего звания. Приходи, дым ждёт!",
    "🎁 {name}, ты в курсе, что скоро розыгрыш? Участвуют все, кто был за неделю. Запишись скорее!",
    "👀 {name}, а мы тут новый кальянщик появился, классно шарит. Приходи оценить. Или просто пообщаемся? 😄"
]

def weekly_raffle(vk, send_func):
    active_raffle = db.get_active_raffle()
    if not active_raffle:
        logger.info("Нет активного розыгрыша для завершения.")
        return
    raffle_id = active_raffle[0]
    prize = active_raffle[1]
    participants = db.get_raffle_participants(raffle_id)
    if not participants:
        logger.info("Нет участников в розыгрыше.")
        return
    winner = random.choice(participants)
    db.finish_raffle(raffle_id, winner)
    send_func(winner, f"🎉 ПОЗДРАВЛЯЮ! Ты выиграл **{prize}**! Приходи в течение 7 дней!")
    try:
        vk.wall.post(
            owner_id=-int(GROUP_ID),
            message=f"🎊 Розыгрыш завершён! Победитель получил **{prize}**."
        )
    except Exception as e:
        logger.error(f"Не удалось опубликовать пост: {e}")
    db.create_raffle()
    logger.info(f"✅ Новый розыгрыш создан с призом: {db.get_active_raffle()[1]}")

def remind_inactive_guests(vk, send_func):
    now = datetime.now()
    week_ago = (now - timedelta(days=7)).isoformat()
    two_weeks_ago = (now - timedelta(days=14)).isoformat()
    db.cursor.execute('''
        SELECT vk_id, name FROM guests 
        WHERE (last_activity IS NULL OR last_activity < ?) 
          AND (last_reminder IS NULL OR last_reminder < ?)
    ''', (week_ago, two_weeks_ago))
    rows = db.cursor.fetchall()
    for vk_id, name in rows:
        msg = random.choice(REMINDER_MESSAGES).format(name=name or "Гость")
        try:
            send_func(vk_id, msg)
            db.cursor.execute("UPDATE guests SET last_reminder=? WHERE vk_id=?", (now.isoformat(), vk_id))
            db.conn.commit()
            now_str = now.strftime("%d.%m.%Y %H:%M:%S")
            gs.update_guest_sheet(vk_id, last_reminder=now_str)
            logger.info(f"📨 Напоминание отправлено гостю {vk_id}")
        except Exception as e:
            logger.error(f"❌ Не удалось отправить напоминание {vk_id}: {e}")

def run_scheduler(vk, send_func):
    schedule.every().day.at("12:00").do(remind_inactive_guests, vk, send_func)
    schedule.every().sunday.at("20:00").do(weekly_raffle, vk, send_func)
    # Резервное копирование убрано (функция backup_database не используется)
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler(vk, send_func):
    thread = threading.Thread(target=run_scheduler, args=(vk, send_func), daemon=True)
    thread.start()