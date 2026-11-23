
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database.database_connection import engine
from app.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    if not url or url == "driver://user:pass@localhost/dbname":
        url = engine.url.render_as_string(hide_password=False)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}

    # configured_url = config.get_main_option("sqlalchemy.url")
    x_args = context.get_x_argument(as_dictionary=True)

    configured_url = (
            x_args.get("db_url")
            or config.get_main_option("sqlalchemy.url")
    )

    if configured_url and configured_url != "driver://user:pass@localhost/dbname":
        configuration["sqlalchemy.url"] = configured_url
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    if connectable is not engine:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
