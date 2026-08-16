# handlers_modules/registration.py
import re
import random
from datetime import datetime
import database as db
import google_sheets as gs
import keyboards as kb
import utils
from config import logger
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ===== ТЕКСТ СОГЛАСИЯ =====
AGREEMENT_TEXT = (
    "🔒 **СОГЛАСИЕ НА ОБРАБОТКУ ПЕРСОНАЛЬНЫХ ДАННЫХ**\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🧞 Привет! Чтобы я мог начислять тебе визиты,\n"
    "дарить скидки и приглашать на розыгрыши,\n"
    "мне нужно немного магии — твой номер телефона\n"
    "и дата рождения.\n\n"
    "📌 Твои данные в надёжных руках (моих!) и нужны только для:\n"
    "   • учёта визитов и бонусов\n"
    "   • розыгрышей и акций\n"
    "   • твоего дня рождения (подарки будут!)\n\n"
    "🔐 Мы никому не передаём твои данные.\n"
    "Это наше джиннское обещание!\n\n"
    "Нажми **«Принимаю»**, чтобы продолжить.\n"
    "Нажми **«Отказываюсь»**, если передумал.\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
)

WELCOME_MESSAGES = [
    (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧞 ПРИВЕТСТВУЮ, ПУТНИК!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👋 Привет, {name}!\n"
        "Я Джинн Dia Mist – хранитель дыма и повелитель углей! 🧞💨\n\n"
        "Чтобы я мог колдовать тебе скидки и подарки,\n"
        "давай познакомимся поближе.\n\n"
        "Не бойся, я не буду звонить тебе в 3 часа ночи...\n"
        "или буду? 😈\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🍃 ДОБРО ПОЖАЛОВАТЬ!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "О, {name}! Ты нашёл путь к Джинну Dia Mist!\n"
        "Я тут главный по дыму и хорошему настроению.\n\n"
        "Чтобы я мог исполнять твои желания\n"
        "(ну, хотя бы скидки и бонусы),\n"
        "давай познакомимся поближе.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧞‍♂️ А ВОТ И Я!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Ты, наверное, уже почувствовал\n"
        "аромат настоящего кальяна?\n\n"
        "Чтобы стать частью нашей дымной семьи,\n"
        "нужно всего лишь оставить свой номер телефона.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 ПРИВЕТ, НОВОБРАНЕЦ!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Ты попал в лапы Джинна Dia Mist –\n"
        "самого обаятельного духа кальянной!\n\n"
        "Хочешь получать секретные скидки\n"
        "и участвовать в розыгрышах?\n"
        "Тогда давай заполним твой профиль.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
]

PHONE_REQUEST_MESSAGES = [
    (
        "📱 **А ТЕПЕРЬ – САМОЕ ВАЖНОЕ!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🧞 Чтобы я мог записывать твои визиты,\n"
        "дарить бонусы и звать на розыгрыши,\n"
        "мне нужен твой номер телефона.\n\n"
        "📌 Не переживай, я не буду звонить в 3 часа ночи\n"
        "(хотя могу, если ты задолжаешь мне уголь 😈).\n\n"
        "Напиши свой номер в ответ.\n"
        "Подойдёт любой формат: 7XXXXXXXXXX, +7XXXXXXXXXX, 8XXXXXXXXXX.\n"
        "Я сам приведу его к нужному виду.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    (
        "📞 **ОТКРОЙ МНЕ СВОЙ СЕКРЕТ!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🧞 Чтобы я мог исполнять твои желания,\n"
        "мне нужно знать твой номер телефона.\n\n"
        "🔐 Обещаю: никакого спама, только дым и магия!\n"
        "Твои данные в надёжных руках (ну, лапах).\n\n"
        "Напиши номер в ответ – и мы начнём!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ),
    (
        "📲 **ПОСЛЕДНИЙ ШАГ!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🧞 Я почти готов колдовать для тебя скидки!\n"
        "Осталось только узнать твой номер телефона.\n\n"
        "✍️ Напиши его в ответ (можно с +7, можно без).\n"
        "Я сам приведу его к нужному виду.\n\n"
        "И не бойся – я джинн, а не коллектор. 😄\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
]

def get_agreement_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('✅ Принимаю', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('❌ Отказываюсь', color=VkKeyboardColor.NEGATIVE)
    return keyboard

def handle_new_guest(vk, user_id, guest, send_func):
    name = guest[1] if guest[1] else "Гость"
    if len(guest) > 14 and guest[14] == 1:
        phone_text = random.choice(PHONE_REQUEST_MESSAGES)
        send_func(user_id, phone_text, keyboard=None)
    else:
        send_func(
            user_id,
            AGREEMENT_TEXT,
            keyboard=get_agreement_keyboard()
        )

def handle_registration_step(vk, user_id, guest, message, send_func):
    reg_step_raw = guest[9] if len(guest) > 9 else 0
    try:
        reg_step = int(reg_step_raw) if reg_step_raw is not None else 0
    except (ValueError, TypeError):
        reg_step = 0

    phone = guest[2] if len(guest) > 2 else ''

    if reg_step >= 3 and not phone:
        db.cursor.execute("UPDATE guests SET registration_step=1 WHERE vk_id=?", (user_id,))
        db.conn.commit()
        gs.update_guest_sheet(user_id, registration_step=1)
        guest = db.get_guest(user_id)
        name = guest[1] if guest[1] else "Гость"
        phone_text = random.choice(PHONE_REQUEST_MESSAGES)
        send_func(user_id, phone_text, keyboard=None)
        return True

    if reg_step == 0:
        db.cursor.execute("UPDATE guests SET registration_step=1 WHERE vk_id=?", (user_id,))
        db.conn.commit()
        gs.update_guest_sheet(user_id, registration_step=1)
        guest = db.get_guest(user_id)
        name = guest[1] if guest[1] else "Гость"
        phone_text = random.choice(PHONE_REQUEST_MESSAGES)
        send_func(user_id, phone_text, keyboard=None)
        return True

    if reg_step == 1:
        raw_phone = re.sub(r'[^0-9]', '', message)
        if len(raw_phone) >= 10 and raw_phone[0] in ('7', '8'):
            if raw_phone[0] == '8':
                raw_phone = '7' + raw_phone[1:]
            if len(raw_phone) == 10:
                raw_phone = '7' + raw_phone
            if len(raw_phone) == 11:
                db.cursor.execute("UPDATE guests SET phone=?, registration_step=2 WHERE vk_id=?", (raw_phone, user_id))
                db.conn.commit()
                now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                gs.update_guest_sheet(user_id, phone=raw_phone, registration_step=2, updated_at=now_str)
                send_func(
                    user_id,
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✅ НОМЕР СОХРАНЁН\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📱 Номер: {raw_phone}\n\n"
                    "Теперь укажи дату рождения\n"
                    "(например, 15.05.1990).\n"
                    "Если не хочешь – напиши 'пропустить'.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    keyboard=kb.get_main_keyboard()
                )
                return True
            else:
                send_func(user_id, "❌ Номер должен содержать 11 цифр (например, 79161234567). Попробуй ещё раз.")
                return True
        else:
            send_func(user_id, "❌ Номер должен начинаться с 7 или 8 и содержать не менее 10 цифр. Попробуй ещё раз.")
            return True

    if reg_step == 2:
        if message.lower() in ('пропустить', 'skip', 'нет'):
            birth = None
            skip_messages = [
                "🎂 Эх, а как же подарок на день рождения? Ну ладно, тайну возраста оставим при тебе 😏",
                "🧞 Я бы приготовил тебе сюрприз на день рождения... но кто я такой, чтобы лезть в чужие секреты?",
                "🎁 Отказываешься от даты рождения? Смело. Но потом не говори, что Джинн оставил тебя без подарка 😈",
                "🤔 Хитро-хитро... возраст скрыт, паспорт не показан. Ладно, принимается!",
                "🎂 Хорошо, не скажешь дату — не скажешь. Но если вдруг захочешь подарок, я буду ждать 👀",
                "🧞 Некоторые скрывают возраст, некоторые скрывают вкусы кальяна. Я уже ничему не удивляюсь.",
                "🎁 Ну вот, подарок на день рождения снова остался без хозяина..."
            ]
            send_func(
                user_id,
                random.choice(skip_messages) +
                "\n\n💡 Если передумаешь, напиши:\n/birth 15.05.1999"
            )
        else:
            if re.match(r'^\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})$', message):
                birth = message
                send_func(
                    user_id,
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🎂 ДАТА СОХРАНЕНА!\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Запомним: {birth}.\n"
                    "В твой день рождения мы подарим тебе подарок! 🎁\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
            else:
                send_func(
                    user_id,
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "❌ НЕВЕРНЫЙ ФОРМАТ\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Используй формат ДД.ММ.ГГГГ\n"
                    "(например, 15.05.1990)\n"
                    "или напиши 'пропустить'.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                return True

        db.cursor.execute(
            "UPDATE guests SET birth=?, registration_step=3 WHERE vk_id=?",
            (birth, user_id)
        )
        db.conn.commit()
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        gs.update_guest_sheet(user_id, birth=birth, registration_step=3, updated_at=now_str)

        guest_after = db.get_guest(user_id)
        current_visits = int(guest_after[5]) if guest_after[5] is not None else 0
        if current_visits == 0:
            new_visits = 1
            new_visits_in_cycle = 1
            new_level = utils.get_level_by_visits(new_visits)
            db.cursor.execute(
                "UPDATE guests SET visits=?, visits_in_cycle=?, level=?, updated_at=? WHERE vk_id=?",
                (new_visits, new_visits_in_cycle, new_level, datetime.now().isoformat(), user_id)
            )
            db.conn.commit()
            gs.update_guest_sheet(user_id, visits=new_visits, visits_in_cycle=new_visits_in_cycle, level=new_level)
            bonus_messages = [
                "🎉 Ты просто огонь! Я, Джинн Dia Mist, дарю тебе +1 визит за то, что ты решил стать частью нашей дымной семьи! Осталось всего 5 визитов до бесплатного кальяна – ты справишься! 💨",
                "🔥 О, я чувствую твою энергетику! Ты точно наш человек. Держи +1 визит в подарок – это чтоб ты сразу понял: у нас тут весело! Осталось 5 шагов до халявного дыма! 🧞",
                "🧞 А ты смелый! За это я начисляю тебе +1 визит – магия начинает работать! Теперь осталось 5 визитов, и твой бесплатный кальян будет ждать тебя! Не подведи! 😎",
                "👋 Привет, новобранец! Ты сделал первый шаг. Я, Джинн, даю тебе +1 визит просто за то, что ты появился! Запомни: осталось 5 визитов – и ты в игре! 🎁",
                "🍃 Ветер перемен? Или просто ты? В любом случае – ты с нами! Получай +1 визит в подарок – это мой тебе знак внимания. Осталось 5 визитов до бесплатного кальяна! Не профукай! 😈",
                "💨 Ты только что вошёл – а уже на шаг ближе к бесплатному кальяну! Джинн дарит тебе +1 визит! Осталось 5 – и твой дым будет за наш счёт! 🔥",
                "🎁 Сюрприз! Ты зарегистрировался, и я, Джинн, решил отметить это +1 визитом в подарок! Осталось всего 5 визитов до твоего первого бесплатного кальяна! Удачи! 🍀"
            ]
            send_func(user_id, random.choice(bonus_messages), keyboard=kb.get_main_keyboard())
        else:
            send_func(
                user_id,
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🎉 РЕГИСТРАЦИЯ ЗАВЕРШЕНА!\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Теперь ты полноправный гость.\n"
                "Вот главное меню:\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                keyboard=kb.get_main_keyboard()
            )
        return True

    return False


def ensure_agreement(vk, user_id, guest, send_func):
    if not guest:
        return True
    agreement_given = guest[14] if len(guest) > 14 and guest[14] is not None else 0
    if agreement_given == 1:
        return True
    send_func(
        user_id,
        AGREEMENT_TEXT,
        keyboard=get_agreement_keyboard()
    )
    return False


__all__ = [
    'handle_new_guest',
    'handle_registration_step',
    'get_agreement_keyboard',
    'AGREEMENT_TEXT',
    'PHONE_REQUEST_MESSAGES',
    'ensure_agreement'
]