# keyboards.py
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from config import ADMIN_IDS


def get_main_keyboard(user_id=None):
    """Главное меню. Если пользователь администратор – показывает админ-кнопки."""
    keyboard = VkKeyboard(one_time=False)
    
    keyboard.add_button('👤 Профиль', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('✅ Визит', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('🔥 Акции', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('🤵 Твой Мастер', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('🎁 Розыгрыш', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('✍️ Создатель', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('❓ Помощь', color=VkKeyboardColor.SECONDARY)
    
    if user_id in ADMIN_IDS:
        keyboard.add_line()
        keyboard.add_button('📊 Админ-меню', color=VkKeyboardColor.PRIMARY)
    
    return keyboard


def get_admin_menu_keyboard():
    """Администраторское меню (скрытое от гостей)"""
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📨 Рассылка', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('📊 Статистика', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🔍 Статус', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('👥 Все гости', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('🗑️ Удалить гостя', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard


def get_agreement_keyboard():
    """Клавиатура для согласия на обработку ПД"""
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('✅ Принимаю', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('❌ Отказываюсь', color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_chat_keyboard():
    return None


def get_phone_keyboard():
    return None


def get_confirm_visit_keyboard(code):
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(f'/visit {code}', color=VkKeyboardColor.POSITIVE)
    return keyboard