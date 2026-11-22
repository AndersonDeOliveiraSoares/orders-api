
import hashlib
import json
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions.exceptions_order import (
    CustomerNotFoundException,
    IdempotencyKeyPayloadMismatchException,
    InsufficientStockException,
    InvalidOrderStatusException,
    OrderNotFoundException,
    ProductNotFoundException,
)
from app.models.models_customer import Customer
from app.models.models_order import Order, OrderItem
from app.models.models_outbox import OutboxEvent
from app.models.models_product import Product
from app.repositories.repository_customer import CustomerRepository
from app.repositories.repository_idempotency import IdempotencyRepository
from app.repositories.repository_order import OrderRepository
from app.repositories.repository_outbox import OutboxRepository
from app.repositories.repository_product import ProductRepository
from app.schemas.schemas_order import OrderCreate, OrderItemCreate


class OrderService:
    """Serviço responsável pelas regras de negócio dos pedidos."""

    ALLOWED_TRANSITIONS = {
        "PENDING": {"CONFIRMED", "CANCELLED"},
        "CONFIRMED": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }

    def __init__(self, db: Session):
        self.db = db
        self.customer_repository = CustomerRepository(db)
        self.product_repository = ProductRepository(db)
        self.order_repository = OrderRepository(db)
        self.idempotency_repository = IdempotencyRepository(db)
        self.outbox_repository = OutboxRepository(db)

    def _validate_customer(self, customer_id: int) -> Customer:
        customer = self.customer_repository.get_by_id(customer_id)

        if customer is None:
            raise CustomerNotFoundException(
                f"Cliente não encontrado: {customer_id}"
            )

        return customer

    def _get_products_for_order(
        self,
        product_ids: list[int],
    ) -> dict[int, Product]:
        products = self.product_repository.get_by_ids_for_update(product_ids)

        products_by_id = {
            product.id: product for product in products
        }

        missing_product_ids = set(product_ids) - set(products_by_id)

        if missing_product_ids:
            raise ProductNotFoundException(
                f"Produtos não encontrados: {sorted(missing_product_ids)}"
            )

        return products_by_id

    def _validate_stock(
        self,
        products_by_id: dict[int, Product],
        items: list[OrderItemCreate],
    ) -> None:
        for item in items:
            product = products_by_id[item.product_id]

            if product.stock < item.quantity:
                raise InsufficientStockException(
                    f"Estoque insuficiente para o produto {product.name}. "
                    f"Disponível: {product.stock}, "
                    f"solicitado: {item.quantity}."
                )

    def _calculate_order_items(
        self,
        products_by_id: dict[int, Product],
        items: list[OrderItemCreate],
    ) -> tuple[list[OrderItem], Decimal]:
        order_items = []
        total_amount = Decimal("0.00")

        for item in items:
            product = products_by_id[item.product_id]
            unit_price = product.price

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_price=unit_price,
                )
            )

            total_amount += unit_price * item.quantity

        return order_items, total_amount

    def _decrease_stock(
        self,
        products_by_id: dict[int, Product],
        items: list[OrderItemCreate],
    ) -> None:
        for item in items:
            products_by_id[item.product_id].stock -= item.quantity

    def create_order(
        self,
        order_data: OrderCreate,
        idempotency_key: str | None = None,
    ) -> Order:
        try:
            if idempotency_key:
                payload = json.dumps(
                    order_data.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                )

                request_hash = hashlib.sha256(
                    payload.encode("utf-8")
                ).hexdigest()

                key_created = self.idempotency_repository.try_create(
                    idempotency_key,
                    request_hash,
                )

                if not key_created:
                    existing_key = (
                        self.idempotency_repository.get_by_key(
                            idempotency_key
                        )
                    )

                    if existing_key.request_hash != request_hash:
                        raise IdempotencyKeyPayloadMismatchException(
                            "A chave idempotente já foi utilizada "
                            "com conteúdo diferente."
                        )

                    if existing_key.order_id is None:
                        raise RuntimeError(
                            "Chave idempotente sem pedido associado."
                        )

                    order = self.order_repository.get_by_id(
                        existing_key.order_id
                    )

                    if order is None:
                        raise RuntimeError(
                            "Pedido associado à chave idempotente "
                            "não encontrado."
                        )

                    return order

            customer = self._validate_customer(order_data.customer_id)

            product_ids = [
                item.product_id for item in order_data.items
            ]

            products_by_id = self._get_products_for_order(product_ids)

            self._validate_stock(products_by_id, order_data.items)

            order_items, total_amount = self._calculate_order_items(
                products_by_id,
                order_data.items,
            )

            self._decrease_stock(products_by_id, order_data.items)

            order = Order(
                customer_id=customer.id,
                total_amount=total_amount,
                items=order_items,
            )

            self.order_repository.create(order)

            # Garante que o pedido tenha ID antes de criar o evento.
            self.db.flush()

            # Registra o evento na mesma transação do pedido.
            self.outbox_repository.create(
                OutboxEvent(
                    event_type="ORDER_CREATED",
                    aggregate_type="ORDER",
                    aggregate_id=order.id,
                    payload={
                        "order_id": order.id,
                        "customer_id": order.customer_id,
                        "total_amount": str(order.total_amount),
                        "status": order.status,
                    },
                )
            )

            # Associa a chave idempotente ao pedido, quando fornecida.
            if idempotency_key:
                self.idempotency_repository.update_order_id(
                    self.idempotency_repository.get_by_key(
                        idempotency_key
                    ),
                    order.id,
                )

            self.db.commit()
            self.db.refresh(order)

            return order

        except Exception:
            self.db.rollback()
            raise

    def get_order_by_id(self, order_id: int) -> Order:
        order = self.order_repository.get_by_id(order_id)

        if order is None:
            raise OrderNotFoundException(
                f"Pedido não encontrado: {order_id}"
            )

        return order

    def get_all_orders(self) -> list[Order]:
        return self.order_repository.get_all()

    def update_order_status(
        self,
        order_id: int,
        new_status: str,
    ) -> Order:
        """
        Atualiza o status respeitando as transições permitidas.
        Ao cancelar, devolve o estoque na mesma transação.
        """
        try:
            order = self.order_repository.get_by_id_for_update(order_id)

            if order is None:
                raise OrderNotFoundException(
                    f"Pedido não encontrado: {order_id}"
                )

            allowed_statuses = self.ALLOWED_TRANSITIONS.get(
                order.status,
                set(),
            )

            if new_status not in allowed_statuses:
                raise InvalidOrderStatusException(
                    f"Não é permitido alterar o pedido de "
                    f"{order.status} para {new_status}."
                )

            if new_status == "CANCELLED":
                product_ids = [
                    item.product_id for item in order.items
                ]

                products_by_id = self._get_products_for_order(product_ids)

                for item in order.items:
                    products_by_id[item.product_id].stock += item.quantity

            self.order_repository.update_status(order, new_status)

            self.db.commit()
            self.db.refresh(order)

            return order

        except Exception:
            self.db.rollback()
            raise
