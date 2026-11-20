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


def create_customer(db_session, name="Cliente Integração", email=None):
    customer = Customer(
        name=name,
        email=email or unique_email()
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


def test_create_customer_returns_201(client):
    payload = {
        "name": "Novo Cliente",
        "email": unique_email()
    }

    response = client.post("/customers", json=payload)

    assert response.status_code == 201

    data = response.json()
    assert data["id"] is not None
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]


def test_create_customer_invalid_email_returns_422(client):
    response = client.post(
        "/customers",
        json={
            "name": "Cliente Inválido",
            "email": "email-invalido"
        }
    )

    assert response.status_code == 422


def test_create_customer_duplicate_email_returns_409(client, db_session):
    email = unique_email()
    create_customer(db_session, email=email)
    db_session.commit()

    response = client.post(
        "/customers",
        json={
            "name": "Outro Cliente",
            "email": email
        }
    )

    assert response.status_code == 409


def test_get_customers_returns_200(client, db_session):
    customer = create_customer(db_session)
    db_session.commit()

    response = client.get("/customers")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["id"] == customer.id for item in data)


def test_get_customer_returns_200(client, db_session):
    customer = create_customer(db_session)
    db_session.commit()

    response = client.get(f"/customers/{customer.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer.id
    assert data["name"] == customer.name
    assert data["email"] == customer.email


def test_get_customer_not_found_returns_404(client):
    response = client.get("/customers/999999")

    assert response.status_code == 404


def test_update_customer_returns_200(client, db_session):
    customer = create_customer(db_session)
    db_session.commit()

    new_name = "Cliente Atualizado"
    new_email = unique_email()

    response = client.put(
        f"/customers/{customer.id}",
        json={
            "name": new_name,
            "email": new_email
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer.id
    assert data["name"] == new_name
    assert data["email"] == new_email


def test_update_customer_duplicate_email_returns_409(client, db_session):
    customer = create_customer(db_session)
    other_customer = create_customer(db_session)
    db_session.commit()

    response = client.put(
        f"/customers/{customer.id}",
        json={
            "name": "Cliente Alterado",
            "email": other_customer.email
        }
    )

    assert response.status_code == 409


def test_update_customer_not_found_returns_404(client):
    response = client.put(
        "/customers/999999",
        json={
            "name": "Cliente Inexistente",
            "email": unique_email()
        }
    )

    assert response.status_code == 404


def test_delete_customer_returns_204(client, db_session):
    customer = create_customer(db_session)
    db_session.commit()

    response = client.delete(f"/customers/{customer.id}")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/customers/{customer.id}")
    assert get_response.status_code == 404


def test_delete_customer_with_orders_returns_409(client, db_session):
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

    response = client.delete(f"/customers/{customer.id}")

    assert response.status_code == 409
