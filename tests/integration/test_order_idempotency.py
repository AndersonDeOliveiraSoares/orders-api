
from uuid import uuid4

from sqlalchemy import func, select

from app.models.models_customer import Customer
from app.models.models_product import Product
from app.models.models_order import Order
from app.models.models_outbox import OutboxEvent


def create_customer(db_session):
    customer = Customer(
        name="Cliente Idempotencia",
        email=f"cliente-{uuid4()}@example.com",
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def create_product(db_session, stock=10):
    product = Product(
        name="Produto Idempotencia",
        price=100.00,
        stock=stock,
    )
    db_session.add(product)
    db_session.flush()
    return product


def count_orders(db_session):
    statement = select(func.count()).select_from(Order)
    return db_session.scalar(statement)


def count_outbox_events(db_session, order_id):
    statement = (
        select(func.count())
        .select_from(OutboxEvent)
        .where(
            OutboxEvent.aggregate_type == "ORDER",
            OutboxEvent.aggregate_id == order_id,
            OutboxEvent.event_type == "ORDER_CREATED",
        )
    )
    return db_session.scalar(statement)


def test_same_key_and_payload_returns_same_order(
    client,
    db_session,
):
    customer = create_customer(db_session)
    product = create_product(db_session)

    db_session.commit()

    payload = {
        "customer_id": customer.id,
        "items": [
            {
                "product_id": product.id,
                "quantity": 2,
            }
        ],
    }

    headers = {"Idempotency-Key": str(uuid4())}

    first_response = client.post(
        "/orders",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201

    first_order_id = first_response.json()["id"]

    second_response = client.post(
        "/orders",
        json=payload,
        headers=headers,
    )

    assert second_response.status_code == 201
    assert second_response.json()["id"] == first_order_id

    db_session.expire(product)

    product_after = db_session.get(Product, product.id)

    assert product_after.stock == 8
    assert count_orders(db_session) == 1
    assert count_outbox_events(db_session, first_order_id) == 1


def test_same_key_with_different_payload_returns_409(
    client,
    db_session,
):
    customer = create_customer(db_session)
    product = create_product(db_session)

    db_session.commit()

    headers = {"Idempotency-Key": str(uuid4())}

    first_response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                }
            ],
        },
        headers=headers,
    )

    assert first_response.status_code == 201

    first_order_id = first_response.json()["id"]

    second_response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 3,
                }
            ],
        },
        headers=headers,
    )

    assert second_response.status_code == 409

    db_session.expire(product)

    product_after = db_session.get(Product, product.id)

    assert product_after.stock == 8
    assert count_orders(db_session) == 1
    assert count_outbox_events(db_session, first_order_id) == 1


def test_order_without_idempotency_key_creates_outbox_event(
    client,
    db_session,
):
    customer = create_customer(db_session)
    product = create_product(db_session)

    db_session.commit()

    response = client.post(
        "/orders",
        json={
            "customer_id": customer.id,
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                }
            ],
        },
    )

    assert response.status_code == 201

    order_id = response.json()["id"]

    statement = select(OutboxEvent).where(
        OutboxEvent.aggregate_id == order_id,
        OutboxEvent.aggregate_type == "ORDER",
        OutboxEvent.event_type == "ORDER_CREATED",
    )

    event = db_session.scalars(statement).first()

    assert event is not None
    assert event.status == "PENDING"
    assert event.payload["order_id"] == order_id
    assert event.payload["customer_id"] == customer.id
    assert count_outbox_events(db_session, order_id) == 1
