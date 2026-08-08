# handlers_modules/reviews.py
import database as db
import keyboards as kb
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from config import logger

YANDEX_REVIEWS_URL = "https://yandex.ru/maps/org/dia_mist/21541680050/reviews/?add-review=true&ll=54.118043%2C56.769301&tab=reviews&z=16.53"

def ask_review(vk, user_id, send_func):
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('✏️ Написать отзыв', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('🚫 Пропустить', color=VkKeyboardColor.SECONDARY)
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🧞 ОТЗЫВ О ЗАВЕДЕНИИ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Как тебе у нас? Нам важно твоё мнение –\n"
        "об атмосфере, кальяне, сервисе и всём,\n"
        "что делает наш лаунж особенным.\n\n"
        "Нажми «Написать отзыв», чтобы перейти\n"
        "к публикации.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    send_func(user_id, text, keyboard=keyboard)

def handle_review_response(vk, user_id, guest, message, send_func):
    awaiting = db.get_awaiting_review(user_id)
    if not awaiting:
        return False

    if message == '✏️ Написать отзыв':
        text = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🧞 СПАСИБО ЗА ОТЗЫВ!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Ты можешь оставить отзыв на любой из площадок:\n\n"
            "📱 ВКонтакте:\n"
            "   https://vk.com/reviews-228843265\n\n"
            "🗺️ Яндекс Карты:\n"
            f"   {YANDEX_REVIEWS_URL}\n\n"
            "📝 Расскажи о нас пару слов – о кальяне,\n"
            "атмосфере, обслуживании.\n"
            "Мы будем очень благодарны! 😊\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        send_func(user_id, text, keyboard=kb.get_main_keyboard())
        db.set_awaiting_review(user_id, False)
        return True

    if message == '🚫 Пропустить':
        db.set_awaiting_review(user_id, False)
        send_func(user_id, "Хорошо, в следующий раз! 😉", keyboard=kb.get_main_keyboard())
        return True

    return False