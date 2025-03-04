# database.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()

# Получаем параметры подключения к базе данных
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "videos")

# Формируем URL для подключения к базе данных
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Connecting to database at: {DB_HOST}:{DB_PORT}/{DB_NAME}")

# Создаем движок
engine = create_engine(
    DATABASE_URL,
    echo=True  # Включаем SQL-логирование
)

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

# Dependency для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для сброса и пересоздания всех таблиц
# ВНИМАНИЕ: Эта функция удаляет все данные!
def reset_database():
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema has been reset and recreated.")

# Функция для проверки существования таблицы
def table_exists(table_name):
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

# Функция для безопасного обновления схемы
def update_schema():
    """
    Обновляет схему базы данных без потери данных.
    Создает только отсутствующие таблицы.
    """
    logger.info("Updating database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema update completed.")
