
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database_connection import get_db
from app.models.models_customer import Customer
from app.models.models_product import Product
from app.models.models_order import Order


@pytest.fixture
def client(db_session):
    """
    Cliente HTTP de teste usando a sessão isolada do conftest.
    """

    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_customer(db_session):
    customer = Customer(
        name="Cliente Integração",
        email=f"cliente-{uuid4()}@example.com"
    )

    db_session.add(customer)
    db_session.flush()

    return customer


def create_product(db_session, name, price, stock):
    product = Product(
        name=name,
        price=price,
        stock=stock
    )

    db_session.add(product)
    db_session.flush()

    return product


def test_create_order_returns_201(client, db_session):
    customer = create_customer(db_session)
    product = create_product(
        db_session,
        "Notebook Integração",
        3500.00,
        10
    )

    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2
                }
            ]
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["customer_id"] == customer.id
    assert data["total_amount"] == "7000.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["unit_price"] == "3500.00"


def test_get_order_returns_200(client, db_session):
    customer = create_customer(db_session)
    product = create_product(
        db_session,
        "Mouse Integração",
        100.00,
        10
    )

    db_session.commit()

    create_response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1
                }
            ]
        }
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    response = client.get(f"/orders/{order_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order_id
    assert data["customer_id"] == customer.id
    assert len(data["items"]) == 1


def test_get_order_not_found_returns_404(client):
    response = client.get("/orders/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Pedido não encontrado: 999999"


def test_create_order_customer_not_found_returns_404(
    client,
    db_session
):
    product = create_product(
        db_session,
        "Teclado Integração",
        150.00,
        10
    )

    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": 999999,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1
                }
            ]
        }
    )

    assert response.status_code == 404
    assert "Cliente não encontrado" in response.json()["detail"]


def test_create_order_product_not_found_returns_404(
    client,
    db_session
):
    customer = create_customer(db_session)

    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": 999999,
                    "quantity": 1
                }
            ]
        }
    )

    assert response.status_code == 404
    assert "Produtos não encontrados" in response.json()["detail"]


def test_create_order_insufficient_stock_returns_409(
    client,
    db_session
):
    customer = create_customer(db_session)
    product = create_product(
        db_session,
        "Monitor Integração",
        1200.00,
        2
    )

    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 5
                }
            ]
        }
    )

    assert response.status_code == 409
    assert "Estoque insuficiente" in response.json()["detail"]

    product_after = db_session.get(Product, product.id)

    assert product_after.stock == 2


def test_create_order_invalid_payload_returns_422(client):
    response = client.post(
        "/orders",
        json={
            "customer_id": 1,
            "items": [
                {
                    "product_id": 1,
                    "quantity": 0
                }
            ]
        }
    )

    assert response.status_code == 422
