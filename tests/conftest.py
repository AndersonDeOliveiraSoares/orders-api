
import pytest

from sqlalchemy.orm import Session

from app.database.database_connection import engine


@pytest.fixture
def db_session():
    """
    Fornece uma sessão isolada para cada teste.

    Todas as alterações realizadas durante o teste
    são revertidas ao final.
    """

    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint"
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
