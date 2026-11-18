
from app.models.models_product import Product
from app.repositories.repository_product import ProductRepository


def test_get_by_id_returns_product(db_session):
    product = Product(
        name="Notebook",
        price=3500.00,
        stock=10
    )

    db_session.add(product)
    db_session.flush()

    repository = ProductRepository(db_session)

    result = repository.get_by_id(product.id)

    assert result is not None
    assert result.id == product.id
    assert result.name == "Notebook"
    assert result.stock == 10


def test_get_by_id_returns_none_when_product_does_not_exist(db_session):
    repository = ProductRepository(db_session)

    result = repository.get_by_id(999999)

    assert result is None


def test_get_by_ids_returns_multiple_products(db_session):
    products = [
        Product(name="Notebook", price=3500.00, stock=10),
        Product(name="Mouse", price=80.00, stock=20),
        Product(name="Teclado", price=150.00, stock=15),
    ]

    db_session.add_all(products)
    db_session.flush()

    product_ids = [product.id for product in products]

    repository = ProductRepository(db_session)

    result = repository.get_by_ids(product_ids)

    assert len(result) == 3

    result_ids = {product.id for product in result}

    assert result_ids == set(product_ids)


def test_get_by_ids_returns_empty_list_when_products_do_not_exist(db_session):
    repository = ProductRepository(db_session)

    result = repository.get_by_ids([999998, 999999])

    assert result == []


def test_get_by_ids_for_update_returns_products_ordered_by_id(db_session):
    products = [
        Product(name="Notebook", price=3500.00, stock=10),
        Product(name="Mouse", price=80.00, stock=20),
        Product(name="Teclado", price=150.00, stock=15),
    ]

    db_session.add_all(products)
    db_session.flush()

    product_ids = [product.id for product in products]

    repository = ProductRepository(db_session)

    result = repository.get_by_ids_for_update(
        list(reversed(product_ids))
    )

    result_ids = [product.id for product in result]

    assert result_ids == sorted(product_ids)
    assert len(result) == 3
