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
import keyboards as kb

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

                        # ===== ПОЛУЧАЕМ ГОСТЯ =====
                        guest = db.get_guest(user_id)
                        
                        # ===== НОВЫЙ ГОСТЬ =====
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
                            # Для новых гостей показываем согласие
                            handlers.handle_new_guest(vk, user_id, guest, send_func)
                            continue

                        # ===== ОБНОВЛЯЕМ АКТИВНОСТЬ =====
                        db.update_activity(user_id)
                        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        gs.update_guest_sheet(user_id, last_activity=now_str)
                        gs.ensure_guest_in_sheet(user_id, guest)

                        # ===== ОБРАБОТКА РЕГИСТРАЦИИ (только для новых гостей) =====
                        # Проверяем, есть ли у гостя телефон и согласие
                        has_phone = guest[2] is not None and guest[2] != ''
                        has_agreement = len(guest) > 14 and guest[14] == 1
                        
                        # Если это НОВЫЙ гость (нет телефона) - показываем регистрацию
                        if not has_phone and not has_agreement:
                            if handlers.handle_registration_step(vk, user_id, guest, message, send_func):
                                guest = db.get_guest(user_id)
                                continue
                        elif not has_agreement and has_phone:
                            # Уже зарегистрированный гость без согласия - показываем только согласие
                            # Не обрабатываем registration_step, идем в главное меню
                            pass

                        # ===== ОБНОВЛЯЕМ guest ПЕРЕД МЕНЮ =====
                        guest = db.get_guest(user_id)
                        
                        # ===== ОБРАБОТКА СОГЛАСИЯ =====
                        if message == '✅ Принимаю':
                            db.update_guest(user_id, agreement_given=1)
                            gs.update_guest_sheet(user_id, agreement_given=1)
                            guest = db.get_guest(user_id)
                            
                            # Если у гостя нет телефона - просим его
                            if not guest[2]:
                                from handlers_modules.registration import PHONE_REQUEST_MESSAGES
                                phone_text = random.choice(PHONE_REQUEST_MESSAGES)
                                send_func(user_id, phone_text, keyboard=None)
                            else:
                                # Если телефон уже есть - просто показываем меню
                                send_func(
                                    user_id,
                                    "✅ Согласие принято! Теперь ты можешь пользоваться всеми функциями бота.",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                            continue

                        if message == '❌ Отказываюсь':
                            text = (
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                "🧞 ОЙ, А Я УЖЕ ХОТЕЛ НАКОЛДОВАТЬ ТЕБЕ ПЛЮШКИ…\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                "Без твоего согласия я не могу обрабатывать данные,\n"
                                "а значит — не могу начислять тебе визиты,\n"
                                "дарить бонусы и звать на розыгрыши.\n\n"
                                "Это как пытаться заварить чай без чайника — ну никак! 😈\n\n"
                                "Но если хочешь просто задать вопрос администратору\n"
                                "или узнать что‑то о заведении — напиши создателю:\n"
                                "https://vk.com/im?sel=57703251\n\n"
                                "Он не такой волшебный, как я, но отвечает быстрее.\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                            )
                            send_func(user_id, text, keyboard=kb.get_main_keyboard(user_id))
                            continue

                        # ===== ГЛАВНОЕ МЕНЮ =====
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