
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.main import app
from app.database.database_connection import get_db
from app.models import Base


load_dotenv()

TEST_DATABASE_NAME = "orders_test_db"

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5434"))

if not all([DB_USER, DB_PASSWORD]):
    raise RuntimeError(
        "Configurações do PostgreSQL ausentes para os testes."
    )

TEST_DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    database=TEST_DATABASE_NAME,
)

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)


@pytest.fixture(scope="session", autouse=True)
def create_test_schema():
    if test_engine.url.database != TEST_DATABASE_NAME:
        raise RuntimeError(
            "Os testes só podem executar no banco orders_test_db."
        )

    Base.metadata.create_all(bind=test_engine)

    yield

    test_engine.dispose()


@pytest.fixture
def db_session(create_test_schema):
    connection = test_engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    previous_override = app.dependency_overrides.get(get_db)
    had_previous_override = get_db in app.dependency_overrides

    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if had_previous_override:
            app.dependency_overrides[get_db] = previous_override
        else:
            app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def status_client(client):
    return client
