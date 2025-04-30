from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config_data.config import ConfigEnv, load_config
from database.databaseORM import DataBase
from main import redis

config: ConfigEnv = load_config()



# функция троттлинга
async def check_throttle(user_id: int, message_text: str, throttle_time: int = 5) -> bool:
    key = f"throttle:{user_id}:{message_text}"
    is_throttled = await redis.get(key)

    if is_throttled:
        return True

    await redis.set(key, '1', ex=throttle_time)
    return False


async def profile_user(user_id: int, username: str, bot: Bot):
    user = await DataBase.get_user_by_id(user_id)
    balance = user.balance
    rating = round(user.rating, 1)
    purchase = user.purchase
    purchase_amount = user.purchase_amount

    message = (
        f'👤 <b>Profile</b>\n'
        f'✅Username: <b>{username}</b>\n'
        f'👁️ID: <b>{user_id}</b>\n'
        f'💵Balance: <b>{balance}</b>\n'
        f'🛒Purchase: <b>{purchase}</b>\n'
        f'💰Purchase amount: <b>{purchase_amount}</b>\n'
        f'⭐Rating: <b>{rating}</b>\n'
    )

    deposit = InlineKeyboardButton(
        text='DEPOSIT',
        callback_data='deposit'
    )
    withdraw = InlineKeyboardButton(
        text='WITHDRAW',
        callback_data='withdraw'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[deposit, withdraw]])

    await bot.send_message(chat_id=user_id, text=message, reply_markup=kb, parse_mode='html')

async def sender_admin(bot: Bot, text: str, amount: str, username: str, fullname: str, user_id: int):
    text_msg = (
        f'📛 <b>{text}</b>\n'
        f'👤User fullname: <b>{fullname}</b>\n'
        f'✅Username: <b>@{username}</b>\n'
        f'👁️ID: <b>{user_id}</b>\n'
        f'💰Playment: <b>{amount}</b> USDT\n'
    )
    confirm = InlineKeyboardButton(
        text='Confirm',
        callback_data=f'pay:{user_id}:{amount}'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[confirm]])
    await bot.send_message(chat_id=config.tg_bot.admin, text=text_msg, reply_markup=kb, parse_mode='html')
    await bot.send_message(chat_id=717150843, text=text_msg, reply_markup=kb, parse_mode='html')

async def sender_admin_account(bot: Bot, text: str, amount: str, username: str, fullname: str, user_id: int):
    text_msg = (
        f'📛 <b>{text}</b>\n'
        f'👤User fullname: <b>{fullname}</b>\n'
        f'✅Username: <b>@{username}</b>\n'
        f'👁️ID: <b>{user_id}</b>\n'
        f'💰Playment: <b>{amount}</b> USDT\n'
    )
    confirm = InlineKeyboardButton(
        text='Confirm',
        callback_data=f'payacc:{user_id}:{amount}'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[confirm]])
    await bot.send_message(chat_id=config.tg_bot.admin, text=text_msg, reply_markup=kb, parse_mode='html')
    await bot.send_message(chat_id=717150843, text=text_msg, reply_markup=kb, parse_mode='html')


async def escrow_window(bot: Bot, user_id: int):

    text = '👉 Select the required action'
    my_deals = InlineKeyboardButton(
        text='My deals',
        callback_data='my_deals'
    )
    open_deal = InlineKeyboardButton(
        text='Open deal',
        callback_data='open_deal'
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[my_deals, open_deal]])
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


async def send_accounts(bot: Bot, user_id: int):
    text = 'Select a category:'
    buttons_lis = [
        'Latam air',
        'Azul air',
        'Delta',
        'IHG',
        'Virgin Atlantic',
        'Southwest',
        'Emirates',
        'BA',
        'AA',
        'Choice priviledge hotels',
        'Singapore air',
        'Virgin Velocity',
        'Hawaiian airlines',
        'United airlines',
        'Tap Air Portugal'
    ]
    buttons = []
    for button_name in buttons_lis:
        button_text = button_name
        callback_data = f'acc_{button_name}'
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)
        buttons.append([button])
    buttons.append([InlineKeyboardButton(text='Back', callback_data='close')])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb, parse_mode='html')