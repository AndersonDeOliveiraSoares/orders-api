from uuid import uuid4

from app.models.models_idempotency import IdempotencyKey
from app.repositories.repository_idempotency import IdempotencyRepository
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
from time import monotonic, sleep

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from conftest import test_engine
from app.exceptions.exceptions_order import InsufficientStockException
from app.models.models_customer import Customer
from app.models.models_order import Order, OrderItem
from app.models.models_product import Product
from app.repositories.repository_product import ProductRepository
from app.schemas.schemas_order import OrderCreate, OrderItemCreate
from app.services.service_order import OrderService


def test_concurrent_orders_cannot_oversell_stock(monkeypatch):
    first_lock_acquired = Event()
    second_attempting_lock = Event()
    release_first_transaction = Event()

    setup_session = Session(test_engine)

    try:
        customer = Customer(
            name="Cliente Concorrência",
            email="concurrency-test@example.com",
        )

        product = Product(
            name="Produto Concorrência",
            price=100.00,
            stock=5,
        )

        setup_session.add_all([customer, product])
        setup_session.commit()

        customer_id = customer.id
        product_id = product.id

    finally:
        setup_session.close()

    original_get_by_ids_for_update = (
        ProductRepository.get_by_ids_for_update
    )

    second_backend_pid = None

    def controlled_get_by_ids_for_update(repository, product_ids):
        nonlocal second_backend_pid

        if current_thread().name.endswith("_0"):
            products = original_get_by_ids_for_update(
                repository,
                product_ids,
            )

            first_lock_acquired.set()

            if not release_first_transaction.wait(timeout=10):
                raise TimeoutError(
                    "A primeira transação não foi liberada."
                )

            return products

        second_backend_pid = repository.db.execute(
            text("SELECT pg_backend_pid()")
        ).scalar_one()

        second_attempting_lock.set()

        return original_get_by_ids_for_update(
            repository,
            product_ids,
        )

    monkeypatch.setattr(
        ProductRepository,
        "get_by_ids_for_update",
        controlled_get_by_ids_for_update,
    )

    def create_order():
        session = Session(test_engine)

        try:
            order_data = OrderCreate(
                customer_id=customer_id,
                items=[
                    OrderItemCreate(
                        product_id=product_id,
                        quantity=4,
                    )
                ],
            )

            return OrderService(session).create_order(order_data)

        except InsufficientStockException:
            return "INSUFFICIENT_STOCK"

        finally:
            session.close()

    try:
        with ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="order-concurrency",
        ) as executor:

            first_future = executor.submit(create_order)

            assert first_lock_acquired.wait(timeout=10), (
                "A primeira transação não adquiriu o lock."
            )

            second_future = executor.submit(create_order)

            assert second_attempting_lock.wait(timeout=10), (
                "A segunda transação não tentou adquirir o lock."
            )

            verification_session = Session(test_engine)

            try:
                deadline = monotonic() + 10
                second_is_waiting = False

                while monotonic() < deadline:
                    wait_event = verification_session.execute(
                        text(
                            """
                            SELECT wait_event_type
                            FROM pg_stat_activity
                            WHERE pid = :pid
                            """
                        ),
                        {"pid": second_backend_pid},
                    ).scalar_one_or_none()

                    if wait_event == "Lock":
                        second_is_waiting = True
                        break

                    sleep(0.05)

                assert second_is_waiting, (
                    "A segunda transação não foi observada "
                    "aguardando um lock no PostgreSQL."
                )

            finally:
                verification_session.close()

            release_first_transaction.set()

            results = [
                first_future.result(timeout=20),
                second_future.result(timeout=20),
            ]

        successful_orders = [
            result for result in results
            if isinstance(result, Order)
        ]

        rejected_orders = [
            result for result in results
            if result == "INSUFFICIENT_STOCK"
        ]

        assert len(successful_orders) == 1
        assert len(rejected_orders) == 1

        verification_session = Session(test_engine)

        try:
            product_after = verification_session.get(
                Product,
                product_id,
            )

            assert product_after.stock == 1

            orders = verification_session.scalars(
                select(Order).where(
                    Order.customer_id == customer_id
                )
            ).all()

            assert len(orders) == 1

        finally:
            verification_session.close()

    finally:
        release_first_transaction.set()

        cleanup_session = Session(test_engine)

        try:
            orders = cleanup_session.scalars(
                select(Order).where(
                    Order.customer_id == customer_id
                )
            ).all()

            order_ids = [order.id for order in orders]

            if order_ids:
                cleanup_session.query(OrderItem).filter(
                    OrderItem.order_id.in_(order_ids)
                ).delete(synchronize_session=False)

                cleanup_session.query(Order).filter(
                    Order.id.in_(order_ids)
                ).delete(synchronize_session=False)

            cleanup_session.query(Customer).filter(
                Customer.id == customer_id
            ).delete(synchronize_session=False)

            cleanup_session.query(Product).filter(
                Product.id == product_id
            ).delete(synchronize_session=False)

            cleanup_session.commit()

        except Exception:
            cleanup_session.rollback()
            raise

        finally:
            cleanup_session.close()


def test_concurrent_orders_with_same_idempotency_key(monkeypatch):
    first_key_reserved = Event()
    second_attempting_key = Event()
    release_first_transaction = Event()

    setup_session = Session(test_engine)

    try:
        customer = Customer(
            name="Cliente Idempotencia Concorrencia",
            email=f"idempotency-{uuid4()}@example.com",
        )

        product = Product(
            name="Produto Idempotencia Concorrencia",
            price=100.00,
            stock=5,
        )

        setup_session.add_all([customer, product])
        setup_session.commit()

        customer_id = customer.id
        product_id = product.id

    finally:
        setup_session.close()

    idempotency_key = str(uuid4())

    original_try_create = IdempotencyRepository.try_create
    second_backend_pid = None

    def controlled_try_create(
        repository,
        key,
        request_hash,
    ):
        nonlocal second_backend_pid

        if current_thread().name.endswith("_0"):
            result = original_try_create(
                repository,
                key,
                request_hash,
            )

            first_key_reserved.set()

            if not release_first_transaction.wait(timeout=10):
                raise TimeoutError(
                    "A primeira transacao nao foi liberada."
                )

            return result

        second_backend_pid = repository.db.execute(
            text("SELECT pg_backend_pid()")
        ).scalar_one()

        second_attempting_key.set()

        return original_try_create(
            repository,
            key,
            request_hash,
        )

    monkeypatch.setattr(
        IdempotencyRepository,
        "try_create",
        controlled_try_create,
    )

    def create_order():
        session = Session(test_engine)

        try:
            order_data = OrderCreate(
                customer_id=customer_id,
                items=[
                    OrderItemCreate(
                        product_id=product_id,
                        quantity=4,
                    )
                ],
            )

            return OrderService(session).create_order(
                order_data,
                idempotency_key=idempotency_key,
            )

        finally:
            session.close()

    try:
        with ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="idempotency-concurrency",
        ) as executor:

            first_future = executor.submit(create_order)

            assert first_key_reserved.wait(timeout=10), (
                "A primeira requisicao nao reservou a chave."
            )

            second_future = executor.submit(create_order)

            assert second_attempting_key.wait(timeout=10), (
                "A segunda requisicao nao tentou reservar a chave."
            )

            verification_session = Session(test_engine)

            try:
                deadline = monotonic() + 10
                second_is_waiting = False

                while monotonic() < deadline:
                    wait_event = verification_session.execute(
                        text(
                            """
                            SELECT wait_event_type
                            FROM pg_stat_activity
                            WHERE pid = :pid
                            """
                        ),
                        {"pid": second_backend_pid},
                    ).scalar_one_or_none()

                    if wait_event == "Lock":
                        second_is_waiting = True
                        break

                    sleep(0.05)

                assert second_is_waiting, (
                    "A segunda transacao nao foi observada "
                    "aguardando a chave no PostgreSQL."
                )

            finally:
                verification_session.close()

            release_first_transaction.set()

            first_order = first_future.result(timeout=20)
            second_order = second_future.result(timeout=20)

        assert first_order.id == second_order.id

        verification_session = Session(test_engine)

        try:
            product_after = verification_session.get(
                Product,
                product_id,
            )

            assert product_after.stock == 1

            orders = verification_session.scalars(
                select(Order).where(
                    Order.customer_id == customer_id
                )
            ).all()

            assert len(orders) == 1

            idempotency_records = verification_session.scalars(
                select(IdempotencyKey).where(
                    IdempotencyKey.idempotency_key == idempotency_key
                )
            ).all()

            assert len(idempotency_records) == 1
            assert idempotency_records[0].order_id == first_order.id

        finally:
            verification_session.close()

    finally:
        release_first_transaction.set()

        cleanup_session = Session(test_engine)

        try:
            cleanup_session.query(IdempotencyKey).filter(
                IdempotencyKey.idempotency_key == idempotency_key
            ).delete(synchronize_session=False)

            orders = cleanup_session.scalars(
                select(Order).where(
                    Order.customer_id == customer_id
                )
            ).all()

            order_ids = [order.id for order in orders]

            if order_ids:
                cleanup_session.query(OrderItem).filter(
                    OrderItem.order_id.in_(order_ids)
                ).delete(synchronize_session=False)

                cleanup_session.query(Order).filter(
                    Order.id.in_(order_ids)
                ).delete(synchronize_session=False)

            cleanup_session.query(Customer).filter(
                Customer.id == customer_id
            ).delete(synchronize_session=False)

            cleanup_session.query(Product).filter(
                Product.id == product_id
            ).delete(synchronize_session=False)

            cleanup_session.commit()

        except Exception:
            cleanup_session.rollback()
            raise

        finally:
            cleanup_session.close()