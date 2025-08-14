from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import os
import sys
from sqlalchemy import create_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.base import Base, DATABASE_URL
import db

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Alembic должен использовать sync движок, даже если DATABASE_URL asyncpg
    sync_url = DATABASE_URL.replace('asyncpg', 'psycopg2')
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
