from decimal import Decimal
from math import ceil

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from database.models import UsersORM, DealStatus, DealORM, DealRatingORM
from database.database import session_factory



class DataBase:
    @staticmethod
    async def insert_user(user_id: int, user_name: str, name: str = 'нет'):
        """Добавляет нового пользователя в БД или обновляет данные существующего"""
        async with session_factory() as session:
            # Проверка, существует ли пользователь
            query = select(UsersORM).filter(UsersORM.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                # Если пользователь найден, обновляем его данные
                user.user_name = user_name
                user.name = name
            else:
                # Если пользователь не найден, создаем нового
                user = UsersORM(
                    id=user_id,
                    user_name=user_name,
                    name=name,
                )
                session.add(user)

            # Сохраняем изменения
            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                raise ValueError("Ошибка обновления или вставки данных: возможен конфликт") from e

            return True

    @staticmethod
    async def get_deals_count_by_status(user_id: int) -> dict:
        """Возвращает количество сделок пользователя по статусам."""
        try:
            async with session_factory() as session:
                # Запрос для подсчета сделок по статусам
                query = (
                    select(DealORM.status, func.count())
                    .where((DealORM.user_id == user_id) | (DealORM.deal_with == user_id))
                    .group_by(DealORM.status)
                )

                result = await session.execute(query)

                # Инициализируем словарь для подсчета
                status_count = {
                    "in_progress": 0,
                    "completed": 0,
                    "in_arbitration": 0,
                }

                # Обрабатываем результат
                for status, count in result.all():
                    if status == DealStatus.IN_PROGRESS:
                        status_count["in_progress"] = count
                    elif status == DealStatus.COMPLETED:
                        status_count["completed"] = count
                    elif status == DealStatus.IN_ARBITRATION:
                        status_count["in_arbitration"] = count

                return status_count
        except Exception as e:
            raise Exception(f"Ошибка при подсчете сделок: {e}")

    @staticmethod
    async def get_deals(user_id: int, status: DealStatus):
        """Получает список сделок пользователя по статусу и страницу с пагинацией."""
        async with session_factory() as session:  # Создаем асинхронную сессию
            query = (
                select(DealORM)
                .where(
                    (DealORM.user_id == user_id) | (DealORM.deal_with == user_id),  # Условие для пользователя
                    DealORM.status == status  # Условие для статуса
                )
                .order_by(DealORM.created_at.desc())  # Упорядочиваем по дате создания
            )
            result = await session.execute(query)  # Выполняем запрос
            return result.scalars().all()

    @staticmethod
    async def get_deals_all(status: DealStatus):
        """Получает список сделок по статусу и страницу с пагинацией."""
        async with session_factory() as session:  # Создаем асинхронную сессию
            query = (
                select(DealORM)
                .where(
                    DealORM.status == status  # Условие для статуса
                )
                .order_by(DealORM.created_at.desc())  # Упорядочиваем по дате создания
            )
            result = await session.execute(query)  # Выполняем запрос
            return result.scalars().all()

    @staticmethod
    async def create_deal(user_id: int, deal_with: int, deal_name: str, deal_terms: str,
                          deal_amount: Decimal):
        """Создание новой сделки"""
        async with session_factory() as session:
            async with session.begin():
                new_deal = DealORM(
                    user_id=user_id,
                    deal_with=deal_with,
                    deal_name=deal_name,
                    deal_terms=deal_terms,
                    deal_amount=deal_amount
                )
                session.add(new_deal)
                await session.flush()
                return new_deal.id

    @staticmethod
    async def update_deal_status(deal_id: int, new_status: DealStatus):
        """Меняет статус по ид"""
        async with session_factory() as session:
            deal = await session.get(DealORM, deal_id)
            if deal:
                deal.status = new_status
                await session.commit()
            return deal


    @staticmethod
    async def get_deal_by_id(deal_id: int):
        """
          Получает детали сделки с корректным использованием алиасов для таблицы users.
          """
        async with session_factory() as session:
            # Создаем алиасы для таблицы UsersORM
            initiator = aliased(UsersORM)
            partner = aliased(UsersORM)

            query = (
                select(
                    DealORM.deal_name,
                    DealORM.deal_terms,
                    DealORM.deal_amount,
                    DealORM.created_at,
                    DealORM.status,
                    DealORM.user_id,
                    DealORM.deal_with,
                    initiator.user_name.label("initiator_name"),
                    initiator.name.label("initiator_fullname"),
                    partner.user_name.label("partner_name"),
                    partner.name.label("partner_fullname"),
                )
                .join(initiator, DealORM.user_id == initiator.id)  # Алиас для инициатора
                .join(partner, DealORM.deal_with == partner.id)  # Алиас для собеседника
                .where(DealORM.id == deal_id)
            )
            result = await session.execute(query)
            return result.mappings().first()

    @staticmethod
    async def get_user_by_id(user_id: int) -> UsersORM:
        """Ищет пользователя по ID и возвращает объект UsersORM."""
        try:
            async with session_factory() as session:
                query = select(UsersORM).where(UsersORM.id == user_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()  # Возвращает один объект или None
                return user
        except Exception as e:
            raise Exception(f"Ошибка при получении пользователя с ID {user_id}: {e}")

    @staticmethod
    async def get_user_by_username(user_name: str) -> UsersORM:
        """Ищет пользователя по username и возвращает объект UsersORM."""
        try:
            async with session_factory() as session:
                query = select(UsersORM).where(UsersORM.user_name == user_name)
                result = await session.execute(query)
                user = result.scalar_one_or_none()  # Возвращает объект пользователя или None
                return user
        except Exception as e:
            raise Exception(f"Ошибка при поиске пользователя с username '{user_name}': {e}")

    @staticmethod
    async def update_user_balance_add(user_id: int, amount: float):
        """
        Изменяет баланс пользователя в базе данных.

        :param user_id: ID пользователя.
        :param amount: Сумма, которую нужно добавить к балансу.
        """
        async with session_factory() as session:
            query = (
                update(UsersORM)
                .where(UsersORM.id == user_id)
                .values(balance=UsersORM.balance + amount)
            )
            await session.execute(query)
            await session.commit()

    @staticmethod
    async def update_user_balance_reduce(user_id: int, amount: float):
        """
        Изменяет баланс пользователя в базе данных.

        :param session: Активная сессия SQLAlchemy.
        :param user_id: ID пользователя.
        :param amount: Сумма, которую нужно убавить
        """
        async with session_factory() as session:
            query = (
                update(UsersORM)
                .where(UsersORM.id == user_id)
                .values(balance=UsersORM.balance - amount)
            )
            await session.execute(query)
            await session.commit()

    @staticmethod
    async def update_purchase(user_id: int, purchase_increment: int, purchase_amount_increment: Decimal):
        """
        Обновление количества покупок и общей суммы покупок пользователя.

        :param user_id: ID пользователя.
        :param purchase_increment: Количество покупок для добавления.
        :param purchase_amount_increment: Сумма покупок для добавления.
        """
        async with session_factory() as session:  # session_factory — ваша фабрика для сессий
            async with session.begin():
                # Обновляем данные пользователя
                query = (
                    update(UsersORM)
                    .where(UsersORM.id == user_id)
                    .values(
                        purchase=UsersORM.purchase + purchase_increment,
                        purchase_amount=UsersORM.purchase_amount + purchase_amount_increment
                    )
                )
                await session.execute(query)

    @staticmethod
    async def add_rating(user_id: int, deal_id: int, rating: int, comment: str = None):
        # Добавляем новую оценку
        async with session_factory() as session:
            new_rating = DealRatingORM(
                user_id=user_id,
                deal_id=deal_id,
                rating=rating,
                comment=comment)

            session.add(new_rating)
            await session.commit()

            # Пересчитываем средний рейтинг
            avg_rating = await session.execute(
                select(func.avg(DealRatingORM.rating)).where(DealRatingORM.user_id == user_id)
            )
            new_avg = avg_rating.scalar()

            # Обновляем рейтинг пользователя
            user = await session.get(UsersORM, user_id)
            user.rating = new_avg
            await session.commit()