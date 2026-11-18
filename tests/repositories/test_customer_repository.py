
from app.models.models_customer import Customer
from app.repositories.repository_customer import CustomerRepository


def test_get_by_id_returns_customer(db_session):
    customer = Customer(
        name="Cliente Teste",
        email="cliente.teste@example.com"
    )

    db_session.add(customer)
    db_session.flush()

    repository = CustomerRepository(db_session)

    result = repository.get_by_id(customer.id)

    assert result is not None
    assert result.id == customer.id
    assert result.name == "Cliente Teste"
    assert result.email == "cliente.teste@example.com"


def test_get_by_id_returns_none_when_customer_does_not_exist(db_session):
    repository = CustomerRepository(db_session)

    result = repository.get_by_id(999999)

    assert result is None
