"""Testes adicionais para transições de status e devolução de estoque.

Para integrar: copie os testes abaixo para tests/integration/test_orders_api.py
ou renomeie este arquivo para test_orders_status_api.py.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database_connection import get_db
from app.models.models_customer import Customer
from app.models.models_product import Product


@pytest.fixture
def status_client(db_session):
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def create_order_for_status_test(client, db_session, stock=10, quantity=3):
    customer = Customer(
        name="Cliente Status",
        email=f"status-{uuid4()}@example.com"
    )
    product = Product(
        name="Produto Status",
        price=100.00,
        stock=stock
    )
    db_session.add_all([customer, product])
    db_session.flush()
    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [{"product_id": product.id, "quantity": quantity}]
        }
    )
    assert response.status_code == 201
    db_session.refresh(product)
    return response.json()["id"], product


def change_status(client, order_id, new_status):
    return client.patch(
        f"/orders/{order_id}/status",
        json={"status": new_status}
    )


def test_pending_order_can_be_confirmed(status_client, db_session):
    order_id, _ = create_order_for_status_test(status_client, db_session)
    response = change_status(status_client, order_id, "CONFIRMED")
    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"


def test_confirmed_order_can_be_completed(status_client, db_session):
    order_id, _ = create_order_for_status_test(status_client, db_session)
    assert change_status(status_client, order_id, "CONFIRMED").status_code == 200
    response = change_status(status_client, order_id, "COMPLETED")
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


@pytest.mark.parametrize("initial_status", ["PENDING", "CONFIRMED"])
def test_pending_or_confirmed_order_can_be_cancelled_and_stock_restored(
    status_client, db_session, initial_status
):
    order_id, product = create_order_for_status_test(status_client, db_session)
    if initial_status == "CONFIRMED":
        assert change_status(status_client, order_id, "CONFIRMED").status_code == 200

    response = change_status(status_client, order_id, "CANCELLED")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    db_session.refresh(product)
    assert product.stock == 10


def test_completed_order_cannot_be_cancelled(status_client, db_session):
    order_id, product = create_order_for_status_test(status_client, db_session)
    assert change_status(status_client, order_id, "CONFIRMED").status_code == 200
    assert change_status(status_client, order_id, "COMPLETED").status_code == 200

    response = change_status(status_client, order_id, "CANCELLED")
    assert response.status_code == 409
    db_session.refresh(product)
    assert product.stock == 7


def test_cancelled_order_cannot_be_cancelled_twice(status_client, db_session):
    order_id, product = create_order_for_status_test(status_client, db_session)
    assert change_status(status_client, order_id, "CANCELLED").status_code == 200

    response = change_status(status_client, order_id, "CANCELLED")
    assert response.status_code == 409
    db_session.refresh(product)
    assert product.stock == 10


def test_pending_order_cannot_skip_to_completed(status_client, db_session):
    order_id, product = create_order_for_status_test(status_client, db_session)
    response = change_status(status_client, order_id, "COMPLETED")
    assert response.status_code == 409
    db_session.refresh(product)
    assert product.stock == 7


def test_update_status_order_not_found_returns_404(status_client):
    response = change_status(status_client, 999999, "CANCELLED")
    assert response.status_code == 404


def test_update_status_invalid_value_returns_422(status_client):
    response = change_status(status_client, 1, "INVALID")
    assert response.status_code == 422
