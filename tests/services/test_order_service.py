
from decimal import Decimal

import pytest

from app.models.models_customer import Customer
from app.models.models_order import Order
from app.models.models_product import Product
from app.schemas.schemas_order import OrderCreate
from app.services.service_order import OrderService
from app.exceptions.exceptions_order import (
    CustomerNotFoundException,
    ProductNotFoundException,
    InsufficientStockException,
)


def create_customer(db_session):
    customer = Customer(
        name="Cliente Teste",
        email="cliente.teste@example.com"
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def create_product(db_session, name, price, stock):
    product = Product(
        name=name,
        price=Decimal(price),
        stock=stock
    )
    db_session.add(product)
    db_session.flush()
    return product


def test_create_order_success(db_session):
    customer = create_customer(db_session)
    product = create_product(db_session, "Notebook", "3500.00", 10)

    order_data = OrderCreate(
        customer_id=customer.id,
        items=[
            {"product_id": product.id, "quantity": 2}
        ]
    )

    service = OrderService(db_session)
    order = service.create_order(order_data)

    assert order.id is not None
    assert order.customer_id == customer.id
    assert order.total_amount == Decimal("7000.00")
    assert len(order.items) == 1
    assert order.items[0].product_id == product.id
    assert order.items[0].quantity == 2
    assert order.items[0].unit_price == Decimal("3500.00")

    db_session.refresh(product)
    assert product.stock == 8


def test_create_order_with_multiple_products(db_session):
    customer = create_customer(db_session)
    product_1 = create_product(db_session, "Notebook", "3500.00", 10)
    product_2 = create_product(db_session, "Mouse", "100.00", 20)

    order_data = OrderCreate(
        customer_id=customer.id,
        items=[
            {"product_id": product_1.id, "quantity": 2},
            {"product_id": product_2.id, "quantity": 3}
        ]
    )

    service = OrderService(db_session)
    order = service.create_order(order_data)

    assert order.total_amount == Decimal("7300.00")
    assert len(order.items) == 2

    db_session.refresh(product_1)
    db_session.refresh(product_2)

    assert product_1.stock == 8
    assert product_2.stock == 17


def test_create_order_customer_not_found(db_session):
    product = create_product(
        db_session, "Notebook", "3500.00", 10
    )

    product_id = product.id

    order_data = OrderCreate(
        customer_id=9999,
        items=[
            {"product_id": product_id, "quantity": 1}
        ]
    )

    db_session.commit()
    orders_before = db_session.query(Order).count()

    service = OrderService(db_session)

    with pytest.raises(
        CustomerNotFoundException,
        match="Cliente não encontrado"
    ):
        service.create_order(order_data)

    product_after = db_session.get(Product, product_id)

    assert product_after is not None
    assert product_after.stock == 10

    assert db_session.query(Order).count() == orders_before


def test_create_order_product_not_found(db_session):
    customer = create_customer(db_session)

    order_data = OrderCreate(
        customer_id=customer.id,
        items=[
            {"product_id": 9999, "quantity": 1}
        ]
    )

    db_session.commit()
    orders_before = db_session.query(Order).count()

    service = OrderService(db_session)

    with pytest.raises(
        ProductNotFoundException,
        match="Produtos não encontrados"
    ):
        service.create_order(order_data)

    assert db_session.query(Order).count() == orders_before


def test_create_order_insufficient_stock(db_session):
    customer = create_customer(db_session)
    product = create_product(db_session, "Notebook", "3500.00", 2)

    order_data = OrderCreate(
        customer_id=customer.id,
        items=[
            {"product_id": product.id, "quantity": 3}
        ]
    )

    db_session.commit()
    orders_before = db_session.query(Order).count()

    service = OrderService(db_session)

    with pytest.raises(
        InsufficientStockException,
        match="Estoque insuficiente"
    ):
        service.create_order(order_data)

    product_after = db_session.get(Product, product.id)

    assert product_after is not None
    assert product_after.stock == 2

    assert db_session.query(Order).count() == orders_before


def test_create_order_does_not_change_stock_when_one_product_has_insufficient_stock(
    db_session
):
    customer = create_customer(db_session)

    product_1 = create_product(
        db_session, "Notebook", "3500.00", 10
    )
    product_2 = create_product(
        db_session, "Mouse", "100.00", 1
    )

    order_data = OrderCreate(
        customer_id=customer.id,
        items=[
            {"product_id": product_1.id, "quantity": 2},
            {"product_id": product_2.id, "quantity": 3}
        ]
    )

    db_session.commit()
    orders_before = db_session.query(Order).count()

    service = OrderService(db_session)

    with pytest.raises(
        InsufficientStockException,
        match="Estoque insuficiente"
    ):
        service.create_order(order_data)

    product_1_after = db_session.get(Product, product_1.id)
    product_2_after = db_session.get(Product, product_2.id)

    assert product_1_after is not None
    assert product_2_after is not None

    assert product_1_after.stock == 10
    assert product_2_after.stock == 1

    assert db_session.query(Order).count() == orders_before
