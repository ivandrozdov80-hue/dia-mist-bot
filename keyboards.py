# keyboards.py
"""
Модуль с клавиатурами для VK-бота Dia Mist.
Содержит все основные и административные клавиатуры.
"""
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from config import ADMIN_IDS


def get_main_keyboard(user_id=None):
    """
    Главное меню для всех пользователей.
    Если пользователь администратор — добавляет кнопку "Админ-меню".
    
    Args:
        user_id (int, optional): ID пользователя ВКонтакте.
        
    Returns:
        VkKeyboard: Готовая клавиатура.
    """
    keyboard = VkKeyboard(one_time=False)
    
    # Ряд 1: Профиль, Визит, Акции
    keyboard.add_button('👤 Профиль', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('✅ Визит', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('🔥 Акции', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    
    # Ряд 2: Мастер/Бронь, Розыгрыш
    keyboard.add_button('🤵 Мастер/Бронь', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('🎁 Розыгрыш', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    
    # Ряд 3: Отзывы, Создатель, Помощь
    keyboard.add_button('⭐ Отзывы', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('✍️ Создатель', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('❓ Помощь', color=VkKeyboardColor.SECONDARY)
    
    # Ряд 4 (только для администраторов)
    if user_id in ADMIN_IDS:
        keyboard.add_line()
        keyboard.add_button('📊 Админ-меню', color=VkKeyboardColor.PRIMARY)
    
    return keyboard


def get_admin_menu_keyboard():
    """
    Администраторское меню (видно только админам).
    Содержит кнопки для управления ботом.
    
    Returns:
        VkKeyboard: Готовая клавиатура.
    """
    keyboard = VkKeyboard(one_time=False)
    
    # Ряд 1: Рассылка, Статистика
    keyboard.add_button('📨 Рассылка', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('📊 Статистика', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    
    # Ряд 2: Статус, Все гости, Удалить гостя
    keyboard.add_button('🔍 Статус', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('👥 Все гости', color=VkKeyboardColor.SECONDARY)
    keyboard.add_button('🗑️ Удалить гостя', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    
    # Ряд 3: Назад
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    
    return keyboard


def get_agreement_keyboard():
    """
    Клавиатура для согласия на обработку персональных данных.
    Используется при первом обращении нового гостя или для старых гостей без согласия.
    
    Returns:
        VkKeyboard: Готовая клавиатура с кнопками "Принимаю" и "Отказываюсь".
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('✅ Принимаю', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('❌ Отказываюсь', color=VkKeyboardColor.NEGATIVE)
    return keyboard


def get_confirm_visit_keyboard(code):
    """
    Клавиатура для подтверждения визита по QR-коду.
    
    Args:
        code (int): Код визита, который нужно вставить в кнопку.
        
    Returns:
        VkKeyboard: Готовая клавиатура с одной кнопкой "/visit [код]".
    """
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button(f'/visit {code}', color=VkKeyboardColor.POSITIVE)
    return keyboard