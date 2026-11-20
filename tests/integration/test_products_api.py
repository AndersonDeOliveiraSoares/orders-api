from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.database_connection import get_db
from app.models.models_customer import Customer
from app.models.models_product import Product


@pytest.fixture
def client(db_session):
    """Cliente HTTP de teste usando a sessão isolada do conftest."""
    def override_get_db():
        return db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def unique_email():
    return f"customer-{uuid4()}@example.com"


def create_customer(db_session):
    customer = Customer(
        name="Cliente Integração",
        email=unique_email()
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def create_product(db_session, name="Produto Integração", price=100.00, stock=10):
    product = Product(
        name=name,
        price=price,
        stock=stock
    )
    db_session.add(product)
    db_session.flush()
    return product


def test_create_product_returns_201(client):
    payload = {
        "name": "Notebook",
        "price": "3500.00",
        "stock": 10
    }

    response = client.post("/products", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["name"] == payload["name"]
    assert data["price"] == "3500.00"
    assert data["stock"] == payload["stock"]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": "100.00", "stock": 1},
        {"name": "Produto", "price": "-1.00", "stock": 1},
        {"name": "Produto", "price": "10.999", "stock": 1},
        {"name": "Produto", "price": "100.00", "stock": -1},
        {"name": "Produto", "price": "100.00", "stock": 1.5},
    ]
)
def test_create_product_invalid_payload_returns_422(client, payload):
    response = client.post("/products", json=payload)
    assert response.status_code == 422


def test_get_products_returns_200(client, db_session):
    product = create_product(db_session)
    db_session.commit()

    response = client.get("/products")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == product.id for item in data)


def test_get_product_returns_200(client, db_session):
    product = create_product(db_session)
    db_session.commit()

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product.id
    assert data["name"] == product.name
    assert data["price"] == "100.00"
    assert data["stock"] == product.stock


def test_get_product_not_found_returns_404(client):
    response = client.get("/products/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Produto não encontrado: 999999"


def test_update_product_returns_200(client, db_session):
    product = create_product(db_session)
    db_session.commit()

    payload = {
        "name": "Produto Atualizado",
        "price": "250.50",
        "stock": 25
    }

    response = client.put(f"/products/{product.id}", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product.id
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]
    assert data["stock"] == payload["stock"]


def test_update_product_invalid_price_returns_422(client, db_session):
    product = create_product(db_session)
    db_session.commit()

    response = client.put(
        f"/products/{product.id}",
        json={
            "name": "Produto Atualizado",
            "price": "-10.00",
            "stock": 10
        }
    )

    assert response.status_code == 422


def test_update_product_not_found_returns_404(client):
    response = client.put(
        "/products/999999",
        json={
            "name": "Produto Inexistente",
            "price": "10.00",
            "stock": 1
        }
    )

    assert response.status_code == 404


def test_delete_product_returns_204(client, db_session):
    product = create_product(db_session)
    db_session.commit()

    response = client.delete(f"/products/{product.id}")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/products/{product.id}")
    assert get_response.status_code == 404


def test_delete_product_with_orders_returns_409(client, db_session):
    customer = create_customer(db_session)
    product = create_product(db_session)
    db_session.commit()

    order_response = client.post(
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

    assert order_response.status_code == 201

    response = client.delete(f"/products/{product.id}")

    assert response.status_code == 409
    assert "associado a pedidos" in response.json()["detail"]
