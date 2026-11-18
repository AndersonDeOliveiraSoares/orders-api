
from logging.config import fileConfig

from alembic import context

from app.database.database_connection import engine
from app.models import Base


# Configuração do Alembic
config = context.config

# Configuração de logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata das entidades SQLAlchemy
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrations sem conexão ativa com o banco."""

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
    """Executa migrations utilizando conexão com o banco."""

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# Define o modo de execução
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
