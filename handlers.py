import asyncio
import logging
from decimal import Decimal
import re

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from aiogram.fsm.state import StatesGroup, State, default_state

from config_data.config import ConfigEnv, load_config
from database.databaseORM import DataBase
from database.models import DealStatus
from functions import profile_user, sender_admin, escrow_window, check_throttle, send_accounts, sender_admin_account
from keybords.keybords import create_deals_keyboard, create_deals_all_keyboard

config: ConfigEnv = load_config()

router = Router()

logger = logging.getLogger(__name__)


class FSMFillForm(StatesGroup):
    state_amount = State()
    state_address = State()
    state_amount_deposit = State()
    state_address_deposit = State()
    state_user = State()
    name_deal = State()
    terms_deal = State()
    amount_deal = State()
    account_name = State()
CHAT_ID = -1002300500323

@router.message(CommandStart(), (lambda message: message.chat.type == 'private'))
async def process_start(message: Message, state: FSMContext, bot: Bot):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)

    # Достаем статус пользователя
    user_status = chat_member.status.split('.')[-1]
    if user_status not in ['member', 'administrator', 'creator']:
        await message.answer('you must be subscribed to discountravel chat to access bot, contact admin @Yacobovitz')
        return
    user_name = message.from_user.username or "NO_username"
    name = message.from_user.full_name or "NO_name"
    await DataBase.insert_user(user_id=message.from_user.id, user_name=user_name, name=name)
    await state.clear()
    escrow = InlineKeyboardButton(
        text='ESCROW',
        callback_data='escrow'
    )
    profile = InlineKeyboardButton(
        text='PROFILE',
        callback_data='profile'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[escrow, profile]])
    await message.answer(text='MENU', reply_markup=kb)


@router.message(Command(commands='profile'), (lambda message: message.chat.type == 'private'))
async def process_profile_msg(message: Message, state: FSMContext, bot: Bot):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)

    # Достаем статус пользователя
    user_status = chat_member.status.split('.')[-1]
    if user_status not in ['member', 'administrator', 'creator']:
        await message.answer('you must be subscribed to discountravel chat to access bot, contact admin @Yacobovitz')
        return
    await state.clear()
    await message.delete()
    user_name = message.from_user.username or "NO_username"
    await profile_user(message.from_user.id, user_name, bot)


@router.callback_query((F.data == 'profile'), (lambda callback: callback.message.chat.type == 'private'))
async def process_profile(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=callback.from_user.id)

    # Достаем статус пользователя
    user_status = chat_member.status.split('.')[-1]
    if user_status not in ['member', 'administrator', 'creator']:
        await callback.message.answer('you must be subscribed to discountravel chat to access bot, contact admin @Yacobovitz')
        return
    await state.clear()
    await callback.message.delete()
    user_name = callback.from_user.username or "NO_username"
    await profile_user(callback.from_user.id, user_name, bot)


@router.callback_query(F.data == 'withdraw')
async def process_withdraw(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    user_id = callback.from_user.id
    user = await DataBase.get_user_by_id(user_id)
    balance = user.balance
    commission = 8
    message = (
        f'<b>WITHDRAW</b>\n'
        f'On your balance: <b>{balance}</b>\n'
        f'Commission for withdraw: <b>{commission}</b>%\n'
    )
    back = InlineKeyboardButton(
        text='Back',
        callback_data='profile'
    )
    continue_withdraw = InlineKeyboardButton(
        text='CONTINUE',
        callback_data='continue_withdraw'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[back, continue_withdraw]])

    await callback.message.answer(text=message, reply_markup=kb, parse_mode='html')


@router.callback_query(F.data == 'continue_withdraw')
async def process_continue_withdraw(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()

    message = 'Enter the amount in USDT TRC20'

    await callback.message.answer(text=message)
    await state.set_state(FSMFillForm.state_amount)


@router.message(StateFilter(FSMFillForm.state_amount), F.text.isdigit())
async def process_continue_withdraw_address(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await message.delete()
    await state.update_data(amount=message.text)
    user = await DataBase.get_user_by_id(user_id=message.from_user.id)
    balance = user.balance
    if balance < float(message.text):
        text_msg = '❌ Insufficient funds in the account'
        await message.answer(text_msg)
        await state.clear()
        return

    messages = 'Enter the address in USDT TRC20)'

    await message.answer(text=messages)
    await state.set_state(FSMFillForm.state_address)


@router.message(StateFilter(FSMFillForm.state_amount))
async def process_continue_withdraw_error(message: Message):
    await message.delete()
    messages = 'Enter the amount in USDT TRC20'

    await message.answer(text=messages)


@router.message(StateFilter(FSMFillForm.state_address))
async def process_withdraw_complied(message: Message, state: FSMContext, bot: Bot):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await state.update_data(address=message.text)

    user_dict = await state.get_data()

    amount = user_dict.get('amount')
    address = user_dict.get('address')
    reduced_amount = float(amount) * 0.92

    text = (f'Withdrawal✅ \n\n'
            f'<b>Amount to withdraw:</b> {amount} USDT\n\n'
            f'<b>Commission:</b> 8%\n'
            f'<b>Amount to be received:</b> {reduced_amount:.2f} USDT\n\n'
            f'<b>USDT TRC20 address:</b> {address}'
            )
    back = InlineKeyboardButton(
        text='Back',
        callback_data='profile'
    )
    make_deal = InlineKeyboardButton(
        text='Order withdrawal',
        callback_data='order withdrawal'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[back, make_deal]])
    await message.answer(text=text, reply_markup=kb, parse_mode='html')


@router.callback_query(StateFilter(FSMFillForm.state_address), F.data == 'order withdrawal')
async def withdraw_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    user_dict = await state.get_data()
    await state.clear()

    amount = user_dict.get('amount')
    address = user_dict.get('address')
    reduced_amount = float(amount) * 0.92

    text = (
        f'👤 <b>WITHDRAW</b>\n'
        f'├User fullname: <b>{callback.from_user.full_name}</b>\n'
        f'├Username: <b>@{callback.from_user.username}</b>\n'
        f'├ID: <b>{callback.from_user.id}</b>\n'
        f'├Amount to withdraw: <b>{amount}</b>USDT\n'
        f'├Amount to be received: <b>{reduced_amount:.2f}</b>USDT\n'
        f'├Address: <code>{address}</code>\n'
    )
    await bot.send_message(chat_id=717150843, text=text, parse_mode='html')
    await bot.send_message(chat_id=config.tg_bot.admin, text=text, parse_mode='html')

    text_m = (f'Withdrawal successfully  ordered ✅ \n'
              f'This may take up to 24 hrs ✅\n\n'
              f'<b>Amount to withdraw:</b> {amount} USDT\n\n'
              f'<b>Amount to be received:</b> {reduced_amount:.2f} USDT\n'
              f'<b>USDT TRC20 address:</b> {address}'
              )
    del_message = await callback.message.answer(text=text_m, parse_mode='html')
    await DataBase.update_user_balance_reduce(user_id=callback.from_user.id, amount=float(amount))
    await asyncio.sleep(10)
    await del_message.delete()


""" Отсюда начинается ветка депозит """


@router.callback_query(F.data == 'deposit')
async def process_deposit(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    message = 'Enter the amount in USDT TRC20'

    await callback.message.answer(text=message)
    await state.set_state(FSMFillForm.state_amount_deposit)


@router.message(StateFilter(FSMFillForm.state_amount_deposit), F.text.isdigit())
async def process_deposit_address(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await message.delete()

    await state.update_data(amount=message.text)
    messages = ('<code>TMPZ28h4GWpAnxJiE3Vq5G8dbRPncxJ9mU</code>\nTRC20 network\n'
                'After replenishment, click on the "Completed" button\n'
                'To return to the "Back" profile')

    completed = InlineKeyboardButton(
        text='Completed',
        callback_data='completed'
    )
    back_profile = InlineKeyboardButton(
        text='Back',
        callback_data='profile'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[back_profile, completed]])

    await message.answer(text=messages, reply_markup=kb, parse_mode='html')


@router.message(StateFilter(FSMFillForm.state_amount_deposit))
async def process_deposit_error(message: Message):
    await message.delete()

    messages = 'Enter the amount in USDT'

    await message.answer(text=messages)


@router.callback_query(F.data == 'completed')
async def process_deposit_completed(callback: CallbackQuery, bot: Bot, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()

    user_dict = await state.get_data()
    amount = user_dict.get('amount')
    username = callback.from_user.username
    fullname = callback.from_user.full_name
    user_id = callback.from_user.id
    text = 'DEPOSIT'

    await sender_admin(bot, text, amount, username, fullname, user_id)

    text = '“The deposit has been successfully completed ✅ \nthis may take up to 24 hours ✅”'
    message_del = await callback.message.answer(text=text)
    await asyncio.sleep(10)
    await message_del.delete()

    await state.clear()


""" ESCROW """


@router.message(Command(commands='escrow'), (lambda message: message.chat.type == 'private'))
async def process_escrow_msg(message: Message, state: FSMContext, bot: Bot):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)

    # Достаем статус пользователя
    user_status = chat_member.status.split('.')[-1]
    if user_status not in ['member', 'administrator', 'creator']:
        await message.answer('you must be subscribed to discountravel chat to access bot, contact admin @Yacobovitz')
        return
    await state.clear()
    await message.delete()
    await escrow_window(bot, message.from_user.id)


@router.callback_query(F.data == 'escrow')
async def process_escrow(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await state.clear()
    await callback.message.delete()
    await escrow_window(bot, callback.from_user.id)


@router.callback_query(F.data == 'my_deals')
async def deals_categories(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    status_count = await DataBase.get_deals_count_by_status(callback.from_user.id)
    text = '🤝My deals\n\n👉Select a deal category:'
    in_progress = InlineKeyboardButton(
        text=f'In progress ({status_count.get("in_progress")})',
        callback_data="in_progress_deal"
    )
    completed = InlineKeyboardButton(
        text=f'Completed ({status_count.get("completed")})',
        callback_data="completed_deal"
    )
    in_arbitration = InlineKeyboardButton(
        text=f'In arbitration ({status_count.get("in_arbitration")})',
        callback_data="in_arbitration_deal"
    )
    back = InlineKeyboardButton(
        text='Back',
        callback_data='escrow'
    )
    # Основные кнопки
    buttons = [[in_progress], [completed], [in_arbitration], [back]]

    if callback.from_user.id in config.tg_bot.admin_ids:
        in_arbitration_all = InlineKeyboardButton(
            text='All in arbitration',
            callback_data='in_arbitration_all'
        )
        buttons.insert(-1, [in_arbitration_all])  # Вставляем кнопку перед кнопкой "Back"

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(text=text, reply_markup=kb)


@router.callback_query(F.data.in_(["in_progress_deal", "completed_deal", "in_arbitration_deal", "in_arbitration_all"]))
async def select_deal(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    user_id = callback.from_user.id

    # В зависимости от того, какой тип сделки был выбран, выполняем соответствующие действия
    if callback.data == "in_progress_deal":
        text = ('🔧  In progress\n\n'
                'ℹ️ List of pending transactions\n\n'
                'Status:\n'
                '🛒 - You are a <b>buyer</b>\n'
                '💼 - You are a <b>seller</b>\n\n'
                'Deal in the format:\n'
                'Status Title | amount in USDT | date')
        # Логика для обработки сделок в процессе
        status = DealStatus.IN_PROGRESS
        deals = await DataBase.get_deals(user_id=user_id, status=status)
        kb = create_deals_keyboard(user_id=user_id, deals=deals, page=1, status=status)

        await callback.message.answer(text=text, reply_markup=kb, parse_mode='html')
    elif callback.data == "completed_deal":
        text = ('🤝  Completed\n\n'
                'ℹ️ List of completed deal\n\n'
                'Status:\n'
                '🛒 - You are a <b>buyer</b>\n'
                '💼 - You are a <b>seller</b>\n\n'
                'Deal in the format:\n'
                'Status Title | amount in USDT | date')
        # Логика для обработки сделок в процессе
        status = DealStatus.COMPLETED
        deals = await DataBase.get_deals(user_id=user_id, status=status)
        kb = create_deals_keyboard(user_id=user_id, deals=deals, page=1, status=status)

        await callback.message.answer(text=text, reply_markup=kb, parse_mode='html')
    elif callback.data == "in_arbitration_deal":
        text = ('🤝  In arbitration\n\n'
                'ℹ️ List of arbitration transactions\n\n'
                'Status:\n'
                '🛒 - You are a <b>buyer</b>\n'
                '💼 - You are a <b>seller</b>\n\n'
                'Deal in the format:\n'
                'Status Title | amount in USDT | date')
        # Логика для обработки сделок в процессе
        status = DealStatus.IN_ARBITRATION
        deals = await DataBase.get_deals(user_id=user_id, status=status)
        kb = create_deals_keyboard(user_id=user_id, deals=deals, page=1, status=status)

        await callback.message.answer(text=text, reply_markup=kb, parse_mode='html')
    elif callback.data == "in_arbitration_all":
        text = ('🤝  All in arbitration\n\n'
                'ℹ️ List of arbitration transactions\n\n'
                'Deal in the format:\n'
                'Buyer ID | Title | amount in USDT | date')
        status = DealStatus.IN_ARBITRATION
        deals = await DataBase.get_deals_all(status=status)
        kb = create_deals_all_keyboard(deals=deals, page=1, status=status)
        await callback.message.answer(text=text, reply_markup=kb, parse_mode='html')


@router.callback_query(F.data.startswith("pages_"))
async def process_pagination_all(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    _, page, status = callback.data.split("_")
    page = int(page)
    status = DealStatus(status)

    # Получение данных из базы
    deals = await DataBase.get_deals(
        user_id=callback.from_user.id,
        status=status)
    # Создание клавиатуры
    keyboard = create_deals_all_keyboard(deals=deals, page=page, status=status)

    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("page_"))
async def process_pagination(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    _, page, status = callback.data.split("_")
    page = int(page)
    status = DealStatus(status)

    # Получение данных из базы
    deals = await DataBase.get_deals(
        user_id=callback.from_user.id,
        status=status)
    # Создание клавиатуры
    keyboard = create_deals_keyboard(user_id=callback.from_user.id, deals=deals, page=page, status=status)

    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("deal_"))
async def process_deal_info(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    """Обрабатывает выбор сделки и отправляет информацию о ней."""
    deal_id = int(callback.data.split("_")[1])  # Извлекаем ID сделки из callback_data

    # Получаем сделку из базы данных
    deal = await DataBase.get_deal_by_id(deal_id)

    if not deal:
        await callback.message.answer("⚠️ Сделка не найдена.")
        return

    # Формируем текст сообщения с деталями сделки
    text = (
        f"📋 <b>Deal name:</b> {deal['deal_name']}\n"
        f"💵 <b>Amount:</b> {deal['deal_amount']} USDT\n"
        f"📝 <b>Deal terms:</b> {deal['deal_terms']}\n\n"

        f"🔄 <b>Status:</b> {deal['status'].value}\n\n"

        f"🕒 <b>Created at:</b> {deal['created_at'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"💼 <b>Seller:</b> @{deal['initiator_name'] or deal['initiator_fullname']}\n"
        f"🛒 <b>Buyer:</b> @{deal['partner_name'] or deal['partner_fullname']}\n"
    )
    close = InlineKeyboardButton(
        text='Close',
        callback_data='close'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[close]])
    # Отправляем сообщение с информацией о сделке
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == 'close')
async def process_close(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()


""" OPEN DEAL"""


@router.callback_query(F.data == 'open_deal')
async def process_open_deal(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    text = 'Find user by "@username" or ID'
    await callback.message.answer(text)
    await state.set_state(FSMFillForm.state_user)


@router.message(StateFilter(FSMFillForm.state_user))
async def handle_user_search(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # Получаем введенное сообщение
    user_input = message.text.strip()

    back = InlineKeyboardButton(
        text='Back',
        callback_data='escrow'
    )
    make_deal = InlineKeyboardButton(
        text='MAKE DEAL',
        callback_data='make_deal'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[back, make_deal]])

    # Проверка, является ли введенный текст ID (цифры)
    if user_input.isdigit():
        # Если это ID, пытаемся найти пользователя по ID
        user_id = int(user_input)
        user = await DataBase.get_user_by_id(user_id)
        if user:
            text_msg = (
                f'👤User fullname: <b>{user.name}</b>\n'
                f'✅Username: <b>@{user.user_name}</b>\n'
                f'👁️ID: <b>{user_id}</b>\n'
                f'🛒Purchase: <b>{user.purchase}</b>\n'
                f'💰Purchase amount: <b>{user.purchase_amount}</b>\n'
                f'⭐Rating: <b>{round(user.rating, 1)}</b>\n'
            )
            await state.update_data(deal_with_username=user.user_name,
                                    deal_with_id=user_id)
            await message.answer(text=text_msg, reply_markup=kb, parse_mode='html')
        else:
            await message.delete()
            text_msg = '👀 User not found. Please try again'
            await message.answer(text_msg)



    elif user_input.startswith('@'):
        # Если это username (начинается с @), пытаемся найти пользователя по username
        username = user_input[1:]  # Убираем @
        user = await DataBase.get_user_by_username(user_name=username)
        if user:
            text_msg = (
                f'👤 User fullname: <b>{user.name}</b>\n'
                f'✅ Username: <b>@{username}</b>\n'
                f'👁️ ID: <b>{user.id}</b>\n'                
                f'🛒Purchase: <b>{user.purchase}</b>\n'
                f'💰Purchase amount: <b>{user.purchase_amount}</b>\n'
                f'⭐ Rating: <b>{round(user.rating, 1)}</b>\n'
            )
            await state.update_data(deal_with_username=user.user_name,
                                    deal_with_id=user.id)
            await message.answer(text=text_msg, reply_markup=kb, parse_mode='html')
        else:
            await message.delete()
            text_msg = '👀 User not found. Please try again'
            await message.answer(text_msg)

    else:
        # Если формат не распознан
        await message.answer("🙏 Please enter a valid username (starting with @) or user ID.")
        return


@router.callback_query(StateFilter(FSMFillForm.state_user), F.data == 'make_deal')
async def process_make_deal(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    user_dict = await state.get_data()
    deal_with_username = user_dict.get('deal_with_username')
    deal_with_id = user_dict.get('deal_with_id')
    if callback.from_user.id == deal_with_id:
        back = InlineKeyboardButton(
            text='Back',
            callback_data='escrow'
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[back]])
        text_msg = "⛔️ You can't make deals with yourself"
        await callback.message.answer(text=text_msg, reply_markup=kb)
        return
    text_msg = (
        f"🛒 <b>OPEN DEAL</b>\n\n"
        f"🤝 <i>Deal with username:</i> @{deal_with_username}\n"
        f"💼 <i>You are a:</i> <b>Buyer</b>\n\n"
        f"✏️ <i>Please enter the name of your deal:</i>"
    )
    await callback.message.answer(text_msg, parse_mode='html')
    await state.set_state(FSMFillForm.name_deal)


@router.message(StateFilter(FSMFillForm.name_deal))
async def process_name_deal(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # await message.delete()
    await state.update_data(deal_name=message.text)
    user_dict = await state.get_data()
    deal_with_username = user_dict.get('deal_with_username')
    deal_with_id = user_dict.get('deal_with_id')
    deal_name = message.text
    text_msg = (
        f"🛒 <b>OPEN DEAL</b>\n\n"
        f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n"
        f"🤝 <i>Deal with username:</i> @{deal_with_username}\n"
        f"💼 <i>You are a:</i> <b>Buyer</b>\n\n"
        f"✏️ <i>Please enter the terms of the transaction:</i>"
    )
    await message.answer(text_msg, parse_mode='html')
    await state.set_state(FSMFillForm.terms_deal)


@router.message(StateFilter(FSMFillForm.terms_deal))
async def process_terms_deal(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # await message.delete()
    await state.update_data(deal_terms=message.text)
    user_dict = await state.get_data()
    deal_with_username = user_dict.get('deal_with_username')
    deal_with_id = user_dict.get('deal_with_id')
    deal_name = user_dict.get('deal_name')
    deal_terms = message.text
    text_msg = (
        f"🛒 <b>OPEN DEAL</b>\n\n"
        f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n"
        f"🤝 <i>Deal with username:</i> @{deal_with_username}\n"
        f"💼 <i>You are a:</i> <b>Buyer</b>\n\n"
        f"📜 <i>Deal terms:</i> <b>{deal_terms}</b>\n\n"
        f"✏️ <i>Please enter the amount in USDT:</i>"
    )

    await message.answer(text_msg, parse_mode='html')
    await state.set_state(FSMFillForm.amount_deal)


@router.message(StateFilter(FSMFillForm.amount_deal), F.text.isdigit())
async def process_amount_deal(message: Message, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # await message.delete()
    await state.update_data(deal_amount=message.text)
    user_dict = await state.get_data()

    user = await DataBase.get_user_by_id(user_id=message.from_user.id)
    balance = user.balance
    if balance < float(message.text):
        text_msg = '❌ Insufficient funds in the account'
        await message.answer(text_msg)
        await state.clear()
        return

    deal_with_username = user_dict.get('deal_with_username')
    deal_with_id = user_dict.get('deal_with_id')
    deal_name = user_dict.get('deal_name')
    deal_terms = user_dict.get('deal_terms')
    deal_amount = message.text
    text_msg = (
        f"🛒 <b>OPEN DEAL</b>\n\n"
        f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n"
        f"🤝 <i>Deal with username:</i> @{deal_with_username}\n"
        f"💼 <i>You are a:</i> <b>Buyer</b>\n\n"
        f"💰 <i>Deal amount:</i> <b>{deal_amount} USDT</b>\n\n"
        f"📜 <i>Deal terms:</i> <b>{deal_terms}</b>\n\n"
        f"✏️ <i>Make all necessary photo or video of your account in case of any issues</i>"
    )

    cancel = InlineKeyboardButton(
        text='Cancel',
        callback_data='escrow'
    )
    accept = InlineKeyboardButton(
        text='Accept',
        callback_data='accept'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[cancel, accept]])

    await message.answer(text_msg, reply_markup=kb, parse_mode='html')


@router.message(StateFilter(FSMFillForm.amount_deal))
async def process_deposit_error(message: Message):
    # await message.delete()

    messages = 'Enter the amount in USDT'

    await message.answer(text=messages)


@router.callback_query(StateFilter(FSMFillForm.amount_deal), F.data == 'accept')
async def process_accept(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    """ Добавить запрос к диллеру """

    await callback.message.delete()
    user_dict = await state.get_data()
    deal_with_username = user_dict.get('deal_with_username')
    deal_with_id = user_dict.get('deal_with_id')
    deal_name = user_dict.get('deal_name')
    deal_terms = user_dict.get('deal_terms')
    deal_amount = user_dict.get('deal_amount')

    deal_id = await DataBase.create_deal(user_id=callback.from_user.id,
                                         deal_with=deal_with_id,
                                         deal_name=deal_name,
                                         deal_terms=deal_terms,
                                         deal_amount=Decimal(deal_amount))

    text_msg = (
        f"🛒 <b>USER OPEN DEAL</b>\n\n"
        f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n"
        f"🤝 <i>Deal with username:</i> @{deal_with_username}\n"
        f"💼 <i>Buyer username:</i> <b>@{callback.from_user.username}</b>\n\n"
        f"💰 <i>Deal amount:</i> <b>{deal_amount} USDT</b>\n\n"
        f"📜 <i>Deal terms:</i> <b>{deal_terms}</b>\n\n"
        f"✏️ <i>Make all necessary photo or video of your account in case of any issues</i>"
    )

    to_arbitration = InlineKeyboardButton(
        text='To arbitration',
        callback_data=f'deal_status:{deal_id}:arb'
    )
    confirm = InlineKeyboardButton(
        text='Confirm',
        callback_data=f'deal-status:{deal_id}:com'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[to_arbitration, confirm]])
    await bot.send_message(chat_id=deal_with_id, text=text_msg, reply_markup=kb, parse_mode='html')
    await callback.message.answer(text="⏳ Wait for the user's decision")
    await state.clear()


@router.callback_query(lambda c: c.data.startswith('deal-status:'))
async def process_deal_status(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    _, deal_id, status = callback.data.split(':')
    deal_id = int(deal_id)

    if status == 'com':
        text_msg = 'Send account to buyer and wait on payment confirmation'
        await callback.message.answer(text_msg)
        deal = await DataBase.get_deal_by_id(deal_id)
        deal_name = deal['deal_name']
        user_id = deal['user_id']
        with_deal = callback.from_user.id
        text = (f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n\n"
                f"Confirm the deal")

        release_funds = InlineKeyboardButton(
            text='Release funds',
            callback_data=f'release_funds:{deal_id}'
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[release_funds]])

        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb, parse_mode='html')

    elif status == 'arb':
        status = DealStatus.IN_ARBITRATION
        await DataBase.update_deal_status(deal_id=deal_id, new_status=status)
        text_msg = '❗️ The deal has been sent to arbitration'
        await callback.message.answer(text_msg)

        deal = await DataBase.get_deal_by_id(deal_id)
        deal_name = deal['deal_name']
        user_id = deal['user_id']
        text = (f"📄 <i>Deal name:</i> <b>{deal_name}</b>\n"
                f"❗️ The deal has been sent to arbitration")

        await bot.send_message(chat_id=user_id, text=text, parse_mode='html')


@router.callback_query(lambda c: c.data.startswith('release_funds:'))
async def release_funds(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    _, deal_id = callback.data.split(':')
    deal_id = int(deal_id)

    await callback.message.delete()

    text_msg = f"👏 Congratulations on a successful transaction ✅"
    await callback.message.answer(text_msg, parse_mode='html')

    deal = await DataBase.get_deal_by_id(deal_id)
    deal_name = deal['deal_name']
    user_id = deal['user_id']
    with_deal = deal['deal_with']
    amount = deal['deal_amount']

    await DataBase.update_user_balance_reduce(user_id=callback.from_user.id, amount=float(amount))

    status = DealStatus.COMPLETED
    await DataBase.update_deal_status(deal_id=deal_id, new_status=status)

    await DataBase.update_purchase(user_id=user_id,
                                   purchase_increment=1, purchase_amount_increment=Decimal(deal['deal_amount']))
    await DataBase.update_purchase(user_id=with_deal,
                                   purchase_increment=1, purchase_amount_increment=Decimal(deal['deal_amount']))

    await DataBase.update_user_balance_add(user_id=with_deal, amount=float(deal['deal_amount']))
    text = f"💰 Your balance has been updated by {amount:.2f} USDT."

    await bot.send_message(chat_id=with_deal, text=text, parse_mode='html')

    buttons_user = [InlineKeyboardButton(text=str(i), callback_data=f'btn:{i}:{user_id}:{deal_id}') for i in
                    range(1, 6)]
    kb_user = InlineKeyboardMarkup(inline_keyboard=[buttons_user])

    buttons_deal = [InlineKeyboardButton(text=str(i), callback_data=f'btn:{i}:{with_deal}:{deal_id}') for i in
                    range(1, 6)]
    kb_deal = InlineKeyboardMarkup(inline_keyboard=[buttons_deal])

    text_rate = '✍🏻 Please rate the deal'
    await bot.send_message(chat_id=user_id, text=text_rate, reply_markup=kb_deal, parse_mode='html')
    await bot.send_message(chat_id=with_deal, text=text_rate, reply_markup=kb_user, parse_mode='html')


@router.callback_query(lambda c: c.data.startswith('btn:'))
async def process_rate(callback: CallbackQuery):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    await callback.message.delete()
    _, rating, user_id, deal_id = callback.data.split(':')
    rating = int(rating)
    user_id = int(user_id)
    deal_id = int(deal_id)
    await DataBase.add_rating(user_id=user_id, deal_id=deal_id, rating=rating)


@router.callback_query(lambda c: c.data.startswith("pay:"))
async def confirm_payment(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # Извлекаем данные из callback_data
    _, user_id, amount = callback.data.split(":")
    user_id = int(user_id)
    amount = float(amount)

    # Изменяем баланс пользователя
    await DataBase.update_user_balance_add(user_id, amount)

    # Уведомляем администратора и пользователя
    await callback.answer("Balance updated successfully!", show_alert=True)
    await callback.message.delete()
    await bot.send_message(
        chat_id=user_id,
        text=f"💰 Your balance has been updated by {amount:.2f} USDT.",
        parse_mode="html"
    )


""" choose accounts """


@router.message(Command(commands='accounts'), (lambda message: message.chat.type == 'private'))
async def process_choose_accounts(message: Message, bot: Bot, state: FSMContext):
    if await check_throttle(message.from_user.id, message.text):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    chat_member = await bot.get_chat_member(chat_id=CHAT_ID, user_id=message.from_user.id)

    # Достаем статус пользователя
    user_status = chat_member.status.split('.')[-1]
    if user_status not in ['member', 'administrator', 'creator']:
        await message.answer('you must be subscribed to discountravel chat to access bot, contact admin @Yacobovitz')
        return
    await state.clear()
    await message.delete()

    user_id = message.from_user.id
    await send_accounts(bot, user_id)


@router.callback_query((F.data == 'accounts'), (lambda callback: callback.message.chat.type == 'private'))
async def process_accounts(callback: CallbackQuery, bot: Bot, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    await state.clear()
    await callback.message.delete()
    user_id = callback.from_user.id
    await send_accounts(bot, user_id)


@router.callback_query(lambda c: c.data.startswith('acc_'))
async def process_account_buttons(callback: CallbackQuery, state: FSMContext):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    await callback.message.delete()
    # Определяем данные для каждой категории
    accounts_data = {
        "Latam air": [
            "200k with cash | 150$",
            "30k with email | 20$",
            "10k with email | 10$"
        ],
        "Azul air": [
            "20k with email | 20$"
        ],
        "Delta": [
            "14k | 20$",
            "10k with email | 15$"
        ],
        "IHG": [
            "15k | 20$",
            "13k with email | 15$"
        ],
        "Virgin Atlantic": [
            "38k with email | 40$"
        ],
        "Southwest": [
            "8k with credits 300$ without email | 150$"
        ],
        "Emirates": [
            "10k | 15$",
            "8k family with email | 10$"
        ],
        "BA": [
            "with email 17k | 15$",
            "26k plus voucher flight for 1 person with email | 40$"
        ],
        "AA": [
            "15k with email | 15$"
        ],
        "Choice priviledge hotels": [
            "14k with email | 15$",
            "10k with email | 10$"
        ],
        "Singapore air": [
            "13k with email | 15$",
            "19k with email | 25$"
        ],
        "Virgin Velocity": [
            "6k with email | 10$",
            "7k with email | 10$"
        ],
        "Hawaiian airlines": [
            "64k with email | 40$",
            "10k with email | 10$"
        ]
    }

    # Получаем название выбранной категории
    selected_account = callback.data.split('_')[1]

    # Проверяем, есть ли данные для выбранной категории
    if selected_account in accounts_data:
        response_text = selected_account
        # Генерация кнопок
        buttons = [
            [InlineKeyboardButton(text=name, callback_data=f'prod_{name}')]
            for name in accounts_data[selected_account]
        ]
        # Добавляем кнопку "Back"
        buttons.append([InlineKeyboardButton(text='Back', callback_data='accounts')])
    else:
        await callback.message.answer("Invalid account selected.")
        return

    # Создаем разметку клавиатуры
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    # Отправляем текст и клавиатуру
    await callback.message.answer(text=response_text, reply_markup=kb, parse_mode='html')

    # Подтверждаем callback
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith('prod_'))
async def process_product_selection(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # Регулярное выражение для поиска цены в формате "число$"
    match = re.search(r'\| (\d+)\$', callback.data)

    price = int(match.group(1))  # Получаем совпадение

    await callback.message.delete()
    product_text = callback.message.text
    selected_product = callback.data.split('_')[1]
    user_id = callback.from_user.id

    # Уведомляем пользователя
    await callback.message.answer(
        "Thanks for choosing! The administrator will contact you shortly. ✅"
    )
    await asyncio.sleep(1)
    messages = (f'<code>TMPZ28h4GWpAnxJiE3Vq5G8dbRPncxJ9mU</code>\nTRC20 network\n\n'
                f'{selected_product}\n\n'
                f'After replenishment, click on the "Completed" button\n'
                f'To return to the "Back" accounts')

    completed = InlineKeyboardButton(
        text='Completed',
        callback_data=f'bayacc_completed_{price}'
    )
    back_profile = InlineKeyboardButton(
        text='Back',
        callback_data='accounts'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[back_profile, completed]])

    await callback.message.answer(text=messages, reply_markup=kb, parse_mode='html')

    write = InlineKeyboardButton(text='Profile', url=f"tg://user?id={user_id}")
    markup = InlineKeyboardMarkup(inline_keyboard=[[write]])
    # Уведомляем админа
    admin_id = config.tg_bot.admin
    user_info = f"👁️ ID: {callback.from_user.id},\n✅ Username: @{callback.from_user.username or 'No username'}"
    await bot.send_message(
        chat_id=admin_id,
        text=f"👤 User\n{user_info}\n\nSelected:\n{product_text}\n{selected_product}",
        reply_markup=markup
    )

    await bot.send_message(
        chat_id=717150843,
        text=f"👤 User\n{user_info}\n\nSelected:\n{product_text}\n{selected_product}",
        reply_markup=markup
    )

    # Подтверждаем callback
    await callback.answer("✅ Your choice is registered!")

@router.callback_query(lambda c: c.data.startswith('bayacc_'))
async def process_bay_acc(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку
    await callback.message.delete()
    username = callback.from_user.username
    fullname = callback.from_user.full_name
    user_id = callback.from_user.id
    text = 'Pay account'
    amount = callback.data.split('_')[2]

    await sender_admin_account(bot, text, amount, username, fullname, user_id)

    text = '“The deposit has been successfully completed ✅ \nthis may take up to 24 hours ✅”'
    message_del = await callback.message.answer(text=text)
    await asyncio.sleep(10)
    await message_del.delete()

@router.callback_query(lambda c: c.data.startswith("payacc:"))
async def confirm_payment_account(callback: CallbackQuery, bot: Bot):
    if await check_throttle(callback.from_user.id, callback.data):
        return  # Если пользователь в режиме троттлинга, завершить обработку

    # Извлекаем данные из callback_data
    _, user_id, amount = callback.data.split(":")
    user_id = int(user_id)
    amount = float(amount)

    # Изменяем баланс пользователя
    # await DataBase.update_user_balance_add(user_id, amount)

    # Уведомляем администратора и пользователя
    await callback.answer("Balance updated successfully!", show_alert=True)
    await callback.message.delete()
    await bot.send_message(
        chat_id=user_id,
        text=f"💰 Your balance has been updated by {amount:.2f} USDT.",
        parse_mode="html"
    )