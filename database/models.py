import enum
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import BigInteger, Numeric, Integer, ForeignKey, DateTime, String, Enum, Float
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.database import Base


intpk = Annotated[int, mapped_column(BigInteger, primary_key=True)]

class UsersORM(Base):
    __tablename__ = 'users'

    id: Mapped[intpk]
    user_name: Mapped[str]
    name: Mapped[str]
    balance: Mapped[Decimal] = mapped_column(Numeric(scale=2), default=0)  # Баланс с дробными значениями
    purchase: Mapped[int] = mapped_column(Integer, default=0)  # Количество покупок
    purchase_amount: Mapped[Decimal] = mapped_column(Numeric(scale=2), default=0)  # Общая сумма покупок
    rating: Mapped[float] = mapped_column(Float, default=0)  # Рейтинг пользователя

    # Отношения к сделкам
    initiated_deals: Mapped[list['DealORM']] = relationship(
        'DealORM', foreign_keys='DealORM.user_id', back_populates='user', cascade='all, delete-orphan'
    )
    received_deals: Mapped[list['DealORM']] = relationship(
        'DealORM', foreign_keys='DealORM.deal_with', back_populates='deal_with_user', cascade='all, delete-orphan'
    )
    # Отношение к истории баланса
    balance_history: Mapped[list['BalanceHistoryORM']] = relationship(
        'BalanceHistoryORM', back_populates='user', cascade='all, delete-orphan'
    )
    # Отношение к оценкам
    ratings: Mapped[list['DealRatingORM']] = relationship(
        'DealRatingORM', back_populates='user', cascade='all, delete-orphan'
    )



class DealStatus(enum.Enum):
    IN_PROGRESS = "In progress"  # Ожидание
    COMPLETED = "Completed"  # Завершена
    IN_ARBITRATION = "In arbitration"  # Отменена

class DealORM(Base):
    __tablename__ = 'deals'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)  # Ссылка на пользователя
    deal_with: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)  # Другой пользователь
    deal_name: Mapped[str] = mapped_column(String(255), nullable=False)  # Название сделки
    deal_terms: Mapped[str] = mapped_column(String(1000), nullable=False)  # Условия сделки
    deal_amount: Mapped[Decimal] = mapped_column(Numeric(scale=2), nullable=False)  # Сумма сделки
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)  # Дата создания сделки
    status: Mapped[DealStatus] = mapped_column(Enum(DealStatus), default=DealStatus.IN_PROGRESS)  # Статус сделки

    # Отношения к пользователям
    user: Mapped['UsersORM'] = relationship('UsersORM', foreign_keys=[user_id], back_populates='initiated_deals')
    deal_with_user: Mapped['UsersORM'] = relationship('UsersORM', foreign_keys=[deal_with], back_populates='received_deals')


class BalanceHistoryORM(Base):
    __tablename__ = 'balance_history'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)  # Ссылка на пользователя
    change_amount: Mapped[Decimal] = mapped_column(Numeric(scale=2), nullable=False)  # Изменение баланса
    reason: Mapped[str] = mapped_column(String(255), nullable=False)  # Причина изменения
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow())  # Дата изменения

    # Отношение к пользователю
    user: Mapped['UsersORM'] = relationship('UsersORM', back_populates='balance_history')

class DealRatingORM(Base):
    __tablename__ = 'deal_ratings'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey('deals.id'), nullable=False)  # Ссылка на сделку
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)  # Ссылка на оцениваемого пользователя
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # Оценка (например, от 1 до 5)
    comment: Mapped[str] = mapped_column(String(1000), nullable=True)  # Комментарий к оценке

    # Отношения
    user: Mapped['UsersORM'] = relationship('UsersORM', back_populates='ratings')
