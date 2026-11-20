
import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.exceptions_customer import (
    CustomerEmailAlreadyExistsException,
    CustomerHasOrdersException,
    CustomerNotFoundException,
)
from app.models.models_customer import Customer
from app.models.models_order import Order
from app.models.models_product import Product
from app.schemas.schemas_customer import CustomerCreate, CustomerUpdate
from app.services.service_customer import CustomerService


def create_customer(db_session, name="Cliente Teste", email="cliente@example.com"):
    customer = Customer(name=name, email=email)
    db_session.add(customer)
    db_session.flush()
    return customer


def create_product(db_session):
    product = Product(
        name="Notebook",
        price=1000,
        stock=10,
    )
    db_session.add(product)
    db_session.flush()
    return product


def create_order(db_session, customer):
    product = create_product(db_session)

    order = Order(
        customer_id=customer.id,
        total_amount=1000,
    )
    db_session.add(order)
    db_session.flush()

    return order


def test_create_customer_success(db_session):
    service = CustomerService(db_session)

    customer = service.create_customer(
        CustomerCreate(
            name="Novo Cliente",
            email="novo@example.com",
        )
    )

    assert customer.id is not None
    assert customer.name == "Novo Cliente"
    assert customer.email == "novo@example.com"


def test_create_customer_duplicate_email(db_session):
    create_customer(db_session)
    service = CustomerService(db_session)

    with pytest.raises(CustomerEmailAlreadyExistsException):
        service.create_customer(
            CustomerCreate(
                name="Outro Cliente",
                email="cliente@example.com",
            )
        )


def test_create_customer_integrity_error_rolls_back(
    db_session, monkeypatch
):
    service = CustomerService(db_session)

    def fail_commit():
        raise IntegrityError("INSERT", {}, Exception())

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(CustomerEmailAlreadyExistsException):
        service.create_customer(
            CustomerCreate(
                name="Novo Cliente",
                email="novo@example.com",
            )
        )

    assert db_session.query(Customer).count() == 0


def test_create_customer_unexpected_error_rolls_back(
    db_session, monkeypatch
):
    service = CustomerService(db_session)

    def fail_commit():
        raise RuntimeError("Erro inesperado")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="Erro inesperado"):
        service.create_customer(
            CustomerCreate(
                name="Novo Cliente",
                email="novo@example.com",
            )
        )

    assert db_session.query(Customer).count() == 0


def test_get_customer_by_id_success(db_session):
    customer = create_customer(db_session)
    service = CustomerService(db_session)

    result = service.get_customer_by_id(customer.id)

    assert result.id == customer.id
    assert result.email == customer.email


def test_get_customer_by_id_not_found(db_session):
    service = CustomerService(db_session)

    with pytest.raises(CustomerNotFoundException):
        service.get_customer_by_id(9999)


def test_get_all_customers(db_session):
    create_customer(db_session)
    create_customer(
        db_session,
        name="Segundo Cliente",
        email="segundo@example.com",
    )

    service = CustomerService(db_session)
    customers = service.get_all_customers()

    assert len(customers) == 2


def test_update_customer_success(db_session):
    customer = create_customer(db_session)
    service = CustomerService(db_session)

    updated = service.update_customer(
        customer.id,
        CustomerUpdate(
            name="Cliente Atualizado",
            email="atualizado@example.com",
        ),
    )

    assert updated.name == "Cliente Atualizado"
    assert updated.email == "atualizado@example.com"


def test_update_customer_duplicate_email(db_session):
    customer = create_customer(db_session)
    create_customer(
        db_session,
        name="Outro Cliente",
        email="outro@example.com",
    )

    service = CustomerService(db_session)

    with pytest.raises(CustomerEmailAlreadyExistsException):
        service.update_customer(
            customer.id,
            CustomerUpdate(
                name="Cliente Atualizado",
                email="outro@example.com",
            ),
        )


def test_update_customer_not_found(db_session):
    service = CustomerService(db_session)

    with pytest.raises(CustomerNotFoundException):
        service.update_customer(
            9999,
            CustomerUpdate(
                name="Cliente Atualizado",
                email="atualizado@example.com",
            ),
        )


def test_update_customer_integrity_error_rolls_back(
    db_session, monkeypatch
):
    customer = create_customer(db_session)
    customer_id = customer.id
    db_session.commit()
    service = CustomerService(db_session)

    def fail_commit():
        raise IntegrityError("UPDATE", {}, Exception())

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(CustomerEmailAlreadyExistsException):
        service.update_customer(
            customer_id,
            CustomerUpdate(
                name="Nome Alterado",
                email="alterado@example.com",
            ),
        )

    updated_customer = db_session.get(Customer, customer_id)

    assert updated_customer.name == "Cliente Teste"
    assert updated_customer.email == "cliente@example.com"


def test_update_customer_unexpected_error_rolls_back(
    db_session, monkeypatch
):
    customer = create_customer(db_session)
    customer_id = customer.id

    db_session.commit()

    service = CustomerService(db_session)

    def fail_commit():
        raise RuntimeError("Erro inesperado")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="Erro inesperado"):
        service.update_customer(
            customer_id,
            CustomerUpdate(
                name="Nome Alterado",
                email="alterado@example.com",
            ),
        )

    updated_customer = db_session.get(Customer, customer_id)

    assert updated_customer.name == "Cliente Teste"
    assert updated_customer.email == "cliente@example.com"


def test_delete_customer_success(db_session):
    customer = create_customer(db_session)
    customer_id = customer.id

    service = CustomerService(db_session)
    service.delete_customer(customer_id)

    assert db_session.get(Customer, customer_id) is None


def test_delete_customer_with_orders(db_session):
    customer = create_customer(db_session)
    create_order(db_session, customer)

    service = CustomerService(db_session)

    with pytest.raises(CustomerHasOrdersException):
        service.delete_customer(customer.id)


def test_delete_customer_not_found(db_session):
    service = CustomerService(db_session)

    with pytest.raises(CustomerNotFoundException):
        service.delete_customer(9999)


def test_delete_customer_unexpected_error_rolls_back(
    db_session, monkeypatch
):
    customer = create_customer(db_session)
    customer_id = customer.id

    db_session.commit()

    service = CustomerService(db_session)

    def fail_commit():
        raise RuntimeError("Erro inesperado")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    with pytest.raises(RuntimeError, match="Erro inesperado"):
        service.delete_customer(customer_id)

    assert db_session.get(Customer, customer_id) is not None
