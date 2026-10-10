import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from reachai.db import Base
from reachai.models.database import Company, Contact, ContactEmail, ContactPhone, ContactSource, Opportunity, OutreachEvent, Referral  # noqa: F401
from reachai.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the sqlalchemy.url
if settings.DATABASE_URL:
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
try:
    fileConfig(config.config_file_name)
except Exception:
    pass

target_metadata = Base.metadata

# other values from the config, defined by the standard Python logging config file format
# can be acquired here

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even have to think about the
    DBAPI being used.
    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # this callback is used to prevent SQLALCHEMY from emitting log messages
    # that are unnecessary
    def process_revision_directives(context, revision, directives):
        if getattr(directives, 'branch_label', None) is not None:
            del directives.branch_label

    connectable = config.attributes.get('connection', None)

    if connectable is None:
        # only create Engine if we don't have one
        from sqlalchemy import create_engine
        connectable = create_engine(
            config.get_main_option("sqlalchemy.url"),
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()
