
from decimal import Decimal

from app.models.models_customer import Customer
from app.models.models_order import Order
from app.repositories.repository_order import OrderRepository


def test_get_by_id_returns_order(db_session):
    customer = Customer(
        name="Cliente Teste",
        email="cliente.order@example.com"
    )

    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("3500.00")
    )

    db_session.add(order)
    db_session.flush()

    repository = OrderRepository(db_session)

    result = repository.get_by_id(order.id)

    assert result is not None
    assert result.id == order.id
    assert result.customer_id == customer.id
    assert result.total_amount == Decimal("3500.00")


def test_get_by_id_returns_none_when_order_does_not_exist(db_session):
    repository = OrderRepository(db_session)

    result = repository.get_by_id(999999)

    assert result is None


def test_get_all_returns_orders_ordered_by_id(db_session):
    customer = Customer(
        name="Cliente Teste",
        email="cliente.list@example.com"
    )

    db_session.add(customer)
    db_session.flush()

    orders = [
        Order(customer_id=customer.id, total_amount=Decimal("100.00")),
        Order(customer_id=customer.id, total_amount=Decimal("200.00")),
        Order(customer_id=customer.id, total_amount=Decimal("300.00")),
    ]

    db_session.add_all(orders)
    db_session.flush()

    repository = OrderRepository(db_session)

    result = repository.get_all()

    result_ids = [order.id for order in result]

    assert len(result) == 3
    assert result_ids == sorted(result_ids)


def test_create_adds_order_to_session(db_session):
    customer = Customer(
        name="Cliente Teste",
        email="cliente.create@example.com"
    )

    db_session.add(customer)
    db_session.flush()

    order = Order(
        customer_id=customer.id,
        total_amount=Decimal("450.00")
    )

    repository = OrderRepository(db_session)

    result = repository.create(order)

    assert result is order
    assert order in db_session
    assert order.id is None
