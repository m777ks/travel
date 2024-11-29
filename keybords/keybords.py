from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.models import DealStatus, DealORM


def create_deals_keyboard(user_id: int, deals: list[DealORM], page: int, status: DealStatus) -> InlineKeyboardMarkup:
    """Создает клавиатуру с сделками пользователя."""
    USERS_PER_PAGE = 10
    start_index = (page - 1) * USERS_PER_PAGE
    end_index = start_index + USERS_PER_PAGE
    deals_on_page = deals[start_index:end_index]


    buttons = []

    # Добавление кнопок для сделок
    for deal in deals_on_page:
        status_user = '🛒' if user_id == deal.user_id else '💼'
        button_text = f"{status_user} {deal.deal_name[:10]} | {deal.deal_amount} | {deal.created_at.strftime('%Y-%m-%d')}"
        callback_data = f"deal_{deal.id}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        buttons.append([button])

    # Добавление кнопок пагинации
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page - 1}_{status.value}"))
    if end_index < len(deals):
        pagination_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page + 1}_{status.value}"))

    if pagination_buttons:
        buttons.append(pagination_buttons)
    buttons.append([InlineKeyboardButton(text='Back', callback_data='my_deals')])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard


def create_deals_all_keyboard(deals: list[DealORM], page: int, status: DealStatus) -> InlineKeyboardMarkup:
    """Создает клавиатуру с сделками пользователя."""
    USERS_PER_PAGE = 10
    start_index = (page - 1) * USERS_PER_PAGE
    end_index = start_index + USERS_PER_PAGE
    deals_on_page = deals[start_index:end_index]


    buttons = []

    # Добавление кнопок для сделок
    for deal in deals_on_page:
        button_text = f"{deal.user_id} | {deal.deal_name[:10]} | {deal.deal_amount} | {deal.created_at.strftime('%Y-%m-%d')}"
        callback_data = f"deal_{deal.id}"
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        buttons.append([button])

    # Добавление кнопок пагинации
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"pages_{page - 1}_{status.value}"))
    if end_index < len(deals):
        pagination_buttons.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"pages_{page + 1}_{status.value}"))

    if pagination_buttons:
        buttons.append(pagination_buttons)
    buttons.append([InlineKeyboardButton(text='Back', callback_data='my_deals')])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard