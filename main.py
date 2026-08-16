# main.py
import vk_api
import random
import time
from datetime import datetime
from vk_api.longpoll import VkLongPoll, VkEventType
from config import VK_TOKEN, logger, MAX_MESSAGE_LENGTH
import database as db
import google_sheets as gs
import handlers
import scheduler

scheduler_started = False
_last_msg_time = {}

def run_bot():
    global scheduler_started
    while True:
        try:
            logger.info("🔄 Подключение к VK...")
            vk_session = vk_api.VkApi(token=VK_TOKEN)
            vk = vk_session.get_api()
            longpoll = VkLongPoll(vk_session)

            vk.users.get(user_ids=1)

            logger.info("✅ Джинн запущен, Господин! Жду сообщений...")

            def send_func(uid, txt, attachment=None, keyboard=None):
                return handlers.send_message(vk, uid, txt, attachment, keyboard)

            if not scheduler_started:
                scheduler.start_scheduler(vk, send_func)
                scheduler_started = True

            for event in longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                    try:
                        user_id = event.user_id
                        message = event.text.strip()

                        now = time.time()
                        if user_id in _last_msg_time:
                            if now - _last_msg_time[user_id] < 1.0:
                                logger.debug(f"Антиспам: пропущено сообщение от {user_id}")
                                continue
                        _last_msg_time[user_id] = now

                        if hasattr(event, 'sticker') and event.sticker:
                            handlers.handle_sticker(vk, user_id, event.sticker, send_func)
                            continue

                        if not message or len(message) > MAX_MESSAGE_LENGTH:
                            continue

                        guest = db.get_guest(user_id)
                        
                        if not guest:
                            try:
                                user_info = vk.users.get(user_ids=user_id)[0]
                                name = f"{user_info['first_name']} {user_info['last_name']}"
                            except:
                                name = f"Гость_{user_id}"
                            db.add_guest(user_id, name)
                            gs.add_guest_to_sheet(user_id, name)
                            guest = db.get_guest(user_id)
                            db.update_activity(user_id)
                            now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                            gs.update_guest_sheet(user_id, last_activity=now_str)
                            handlers.handle_new_guest(vk, user_id, guest, send_func)
                            continue

                        db.update_activity(user_id)
                        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        gs.update_guest_sheet(user_id, last_activity=now_str)
                        gs.ensure_guest_in_sheet(user_id, guest)

                        if handlers.handle_registration_step(vk, user_id, guest, message, send_func):
                            guest = db.get_guest(user_id)
                            continue

                        guest = db.get_guest(user_id)
                        handlers.handle_main_menu(vk, user_id, guest, message, send_func)

                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения: {e}")

        except Exception as e:
            logger.error(f"Ошибка подключения к VK: {e}")
            logger.info("🔄 Переподключение через 10 секунд...")
            time.sleep(10)
            continue

if __name__ == "__main__":
    run_bot()