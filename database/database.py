from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from config_data.config import DATABASE_URL_asyncpg

engine = create_async_engine(
    url=DATABASE_URL_asyncpg(),
    echo=False
)

session_factory = async_sessionmaker(engine)




class Base(DeclarativeBase):
    pass