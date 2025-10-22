from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

from alembic import op
import sqlalchemy as sa

def upgrade():
    with op.batch_alter_table('products') as batch_op:
        batch_op.add_column(sa.Column('new_column', sa.String(), nullable=True))

# Make sure Alembic can find your app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your SQLAlchemy Base
from app.database import Base  # adjust if your Base is elsewhere

# Alembic Config object
config = context.config

# Set DB URL with escaped % signs
config.set_main_option(
    "sqlalchemy.url",
    "postgresql+psycopg2://postgres:ZopNow%%40123%%21@localhost:5432/ecommerce_db"
)

# Set up Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic to your models’ metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # optional: include here if you use compare_type for ENUM changes
            # compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


# Run migrations based on mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
