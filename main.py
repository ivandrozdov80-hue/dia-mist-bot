# main.py
import vk_api
import random
import time
import re
from datetime import datetime
from vk_api.longpoll import VkLongPoll, VkEventType
from config import VK_TOKEN, logger, MAX_MESSAGE_LENGTH
import database as db
import google_sheets as gs
import handlers
import scheduler
import keyboards as kb

from handlers_modules.registration import get_agreement_keyboard, AGREEMENT_TEXT_OLD, AGREEMENT_TEXT_NEW, PHONE_REQUEST_MESSAGES

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

                        # ============================================================
                        # 1. ПОЛУЧАЕМ ГОСТЯ ИЗ БАЗЫ
                        # ============================================================
                        guest = db.get_guest(user_id)
                        
                        # ============================================================
                        # 2. НОВЫЙ ГОСТЬ
                        # ============================================================
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
                            
                            send_func(
                                user_id,
                                AGREEMENT_TEXT_NEW,
                                keyboard=get_agreement_keyboard()
                            )
                            continue

                        # ============================================================
                        # 3. ОБНОВЛЯЕМ АКТИВНОСТЬ
                        # ============================================================
                        db.update_activity(user_id)
                        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                        gs.update_guest_sheet(user_id, last_activity=now_str)
                        gs.ensure_guest_in_sheet(user_id, guest)

                        # ============================================================
                        # 4. ПОЛУЧАЕМ СВЕЖИЕ ДАННЫЕ ГОСТЯ
                        # ============================================================
                        guest = db.get_guest(user_id)
                        
                        # Индексы колонок в БД:
                        # 2 - phone, 3 - birth, 9 - registration_step, 25 - agreement_given
                        agreement_given = guest[25] if len(guest) > 25 and guest[25] is not None else 0
                        has_phone = guest[2] is not None and guest[2] != ''
                        has_birth = guest[3] is not None and guest[3] != ''
                        reg_step = guest[9] if len(guest) > 9 and guest[9] is not None else 0

                        logger.info(f"📊 Статус: user={user_id}, agreement={agreement_given}, phone={has_phone}, birth={has_birth}, reg_step={reg_step}")

                        # ============================================================
                        # 5. ОБРАБОТКА КОМАНДЫ /birth (вручную)
                        # ============================================================
                        if message.lower().startswith('/birth '):
                            birth = message[7:].strip()
                            if re.match(r'^\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})$', birth):
                                db.cursor.execute(
                                    "UPDATE guests SET birth=?, registration_step=3 WHERE vk_id=?",
                                    (birth, user_id)
                                )
                                db.conn.commit()
                                gs.update_guest_sheet(user_id, birth=birth, registration_step=3)
                                guest = db.get_guest(user_id)
                                send_func(
                                    user_id,
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎂 ДЕНЬ РОЖДЕНИЯ СОХРАНЁН!\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                    f"Отлично! Записал: {birth}\n"
                                    f"Теперь подарок точно найдёт своего хозяина! 😎\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                            else:
                                send_func(
                                    user_id,
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    "❌ НЕВЕРНЫЙ ФОРМАТ\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Формат даты: ДД.ММ.ГГГГ\n"
                                    "Например: /birth 15.05.1999\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                            continue

                        # ============================================================
                        # 6. ОБРАБОТКА КНОПОК СОГЛАСИЯ
                        # ============================================================
                        if message == '✅ Принимаю':
                            logger.info(f"✅ Гость {user_id} принял согласие")
                            db.cursor.execute("UPDATE guests SET agreement_given = 1 WHERE vk_id = ?", (user_id,))
                            db.conn.commit()
                            gs.update_guest_sheet(user_id, agreement_given=1)
                            guest = db.get_guest(user_id)
                            
                            if not guest[2]:
                                phone_text = random.choice(PHONE_REQUEST_MESSAGES)
                                send_func(user_id, phone_text, keyboard=None)
                            else:
                                send_func(
                                    user_id,
                                    "✅ Согласие принято! Теперь ты можешь пользоваться всеми функциями бота.",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                            continue

                        if message == '❌ Отказываюсь':
                            logger.info(f"❌ Гость {user_id} отказался от согласия")
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

                        # ============================================================
                        # 7. ЕСЛИ НЕТ СОГЛАСИЯ — ПОКАЗЫВАЕМ
                        # ============================================================
                        if agreement_given != 1:
                            logger.info(f"⚠️ Гость {user_id} не дал согласие, показываем")
                            if has_phone:
                                send_func(user_id, AGREEMENT_TEXT_OLD, keyboard=get_agreement_keyboard())
                            else:
                                send_func(user_id, AGREEMENT_TEXT_NEW, keyboard=get_agreement_keyboard())
                            continue

                        # ============================================================
                        # 8. ЕСЛИ НЕТ ТЕЛЕФОНА — ЗАПУСКАЕМ РЕГИСТРАЦИЮ
                        # ============================================================
                        if not has_phone:
                            logger.info(f"📝 Гость {user_id} без телефона, запускаем регистрацию")
                            if handlers.handle_registration_step(vk, user_id, guest, message, send_func):
                                guest = db.get_guest(user_id)
                                continue
                            # Если не обработано — ждём ввод
                            continue

                        # ============================================================
                        # 9. ЕСЛИ НЕТ ДАТЫ РОЖДЕНИЯ — ПРЕДЛАГАЕМ ВВЕСТИ
                        # ============================================================
                        if not has_birth and has_phone:
                            logger.info(f"📝 Гость {user_id} без даты рождения, предлагаем ввести")
                            send_func(
                                user_id,
                                "📅 **УКАЖИ ДАТУ РОЖДЕНИЯ**\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                "Чтобы я мог поздравить тебя с днём рождения и подарить подарок,\n"
                                "напиши дату в формате: **ДД.ММ.ГГГГ**\n\n"
                                "Например: **15.05.1990**\n\n"
                                "Если не хочешь указывать — напиши **'пропустить'**\n"
                                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                                keyboard=None
                            )
                            continue

                        # ============================================================
                        # 10. ОБРАБОТКА ВВОДА ДАТЫ РОЖДЕНИЯ (когда гость отвечает)
                        # ============================================================
                        if has_phone and not has_birth:
                            if re.match(r'^\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})$', message):
                                birth = message
                                db.cursor.execute("UPDATE guests SET birth=?, registration_step=3 WHERE vk_id=?", (birth, user_id))
                                db.conn.commit()
                                gs.update_guest_sheet(user_id, birth=birth, registration_step=3)
                                guest = db.get_guest(user_id)
                                
                                send_func(
                                    user_id,
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                                    f"🎂 ДАТА СОХРАНЕНА!\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                    f"Запомним: {birth}.\n"
                                    f"В твой день рождения мы подарим тебе подарок! 🎁\n"
                                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                                continue
                            elif message.lower() in ('пропустить', 'skip', 'нет'):
                                db.cursor.execute("UPDATE guests SET registration_step=3 WHERE vk_id=?", (user_id,))
                                db.conn.commit()
                                gs.update_guest_sheet(user_id, registration_step=3)
                                guest = db.get_guest(user_id)
                                
                                send_func(
                                    user_id,
                                    "🎂 Хорошо, не скажешь дату — не скажешь.\n"
                                    "Но если вдруг захочешь подарок, я буду ждать 👀\n\n"
                                    "💡 Если передумаешь, напиши: /birth 15.05.1999",
                                    keyboard=kb.get_main_keyboard(user_id)
                                )
                                continue
                            else:
                                send_func(
                                    user_id,
                                    "❌ **НЕВЕРНЫЙ ФОРМАТ**\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                    "Используй формат: **ДД.ММ.ГГГГ**\n"
                                    "Например: **15.05.1990**\n\n"
                                    "Или напиши **'пропустить'**\n"
                                    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                                    keyboard=None
                                )
                                continue

                        # ============================================================
                        # 11. ГЛАВНОЕ МЕНЮ
                        # ============================================================
                        guest = db.get_guest(user_id)
                        handlers.handle_main_menu(vk, user_id, guest, message, send_func)

                    except Exception as e:
                        logger.error(f"Ошибка при обработке сообщения: {e}")
                        import traceback
                        traceback.print_exc()

        except Exception as e:
            logger.error(f"Ошибка подключения к VK: {e}")
            logger.info("🔄 Переподключение через 10 секунд...")
            time.sleep(10)
            continue

if __name__ == "__main__":
    run_bot()