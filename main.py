import asyncio
import logging
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.redis import Redis, RedisStorage

import handlers
from config_data.config import ConfigEnv, load_config
from keybords.main_menu import set_main_menu

# Инициализируем логгер
logger = logging.getLogger(__name__)

# Загружаем конфиг в переменную config
config: ConfigEnv = load_config()
bot = Bot(token=config.tg_bot.token)


redis = Redis(host=config.redis.host, port=config.redis.port, password=config.redis.password)
storage = RedisStorage(redis=redis)

async def main():
    # await start_http_server()
    # Конфигурируем логирование
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    # Выводим в консоль информацию о начале запуска бота
    logger.info('Starting bot')
    #
    # # Проверяем соединение с PostgreSQL
    # async with async_engine.connect() as conn:
    #     res = await conn.execute(text('SELECT VERSION()'))
    #     logger.info(f'Starting {res.first()[0]}')
    #
    # # Создание таблиц
    # async with async_engine.begin() as conn:
    #     # await conn.run_sync(Base.metadata.drop_all)
    #     await conn.run_sync(Base.metadata.create_all)

    dp = Dispatcher(bot=bot, storage=storage)

    dp.include_router(handlers.router)

    # Настраиваем главное меню бота
    await set_main_menu(bot)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



if __name__ == '__main__':
    asyncio.run(main())