
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models_customer import Customer
from app.models.models_order import Order, OrderItem
from app.models.models_product import Product
from app.repositories.repository_customer import CustomerRepository
from app.repositories.repository_order import OrderRepository
from app.repositories.repository_product import ProductRepository
from app.schemas.schemas_order import OrderCreate, OrderItemCreate
from app.exceptions.exceptions_order import (
    CustomerNotFoundException,
    ProductNotFoundException,
    OrderNotFoundException,
    InsufficientStockException,
)


class OrderService:
    """
    Serviço responsável pelas regras de negócio dos pedidos.
    """

    def __init__(self, db: Session):
        self.db = db

        self.customer_repository = CustomerRepository(db)
        self.product_repository = ProductRepository(db)
        self.order_repository = OrderRepository(db)

    def _validate_customer(self, customer_id: int) -> Customer:
        """
        Verifica se o cliente existe.
        Retorna o cliente encontrado ou gera erro.
        """
        customer = self.customer_repository.get_by_id(customer_id)

        if customer is None:
            raise CustomerNotFoundException(
                f"Cliente não encontrado: {customer_id}"
            )

        return customer

    def _get_products_for_order(
        self,
        product_ids: list[int]
    ) -> dict[int, Product]:
        """
        Busca os produtos solicitados e bloqueia suas linhas
        durante a transação.
        Retorna um dicionário indexado pelo ID do produto.
        """
        products = self.product_repository.get_by_ids_for_update(
            product_ids
        )

        products_by_id = {
            product.id: product
            for product in products
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
        items: list[OrderItemCreate]
    ) -> None:
        """
        Verifica se existe estoque suficiente para todos os itens.
        """
        for item in items:
            product = products_by_id[item.product_id]

            if product.stock < item.quantity:
                raise InsufficientStockException(
                    f"Estoque insuficiente para o produto "
                    f"{product.name}. "
                    f"Disponível: {product.stock}, "
                    f"solicitado: {item.quantity}."
                )

    def _calculate_order_items(
        self,
        products_by_id: dict[int, Product],
        items: list[OrderItemCreate]
    ) -> tuple[list[OrderItem], Decimal]:
        """
        Calcula os valores dos itens do pedido e o total geral.
        """
        order_items = []
        total_amount = Decimal("0.00")

        for item in items:
            product = products_by_id[item.product_id]

            unit_price = product.price
            subtotal = unit_price * item.quantity

            order_item = OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price=unit_price
            )

            order_items.append(order_item)
            total_amount += subtotal

        return order_items, total_amount

    def _decrease_stock(
        self,
        products_by_id: dict[int, Product],
        items: list[OrderItemCreate]
    ) -> None:
        """
        Atualiza o estoque dos produtos após a validação.
        """
        for item in items:
            product = products_by_id[item.product_id]
            product.stock -= item.quantity

    def create_order(self, order_data: OrderCreate) -> Order:
        """
        Cria um pedido, valida os dados e atualiza o estoque.

        A operação é atômica: pedido, itens e estoque são
        confirmados ou revertidos em conjunto.
        """
        try:
            customer = self._validate_customer(order_data.customer_id)

            product_ids = [
                item.product_id
                for item in order_data.items
            ]

            products_by_id = self._get_products_for_order(product_ids)

            self._validate_stock(products_by_id, order_data.items)

            order_items, total_amount = self._calculate_order_items(
                products_by_id,
                order_data.items
            )

            self._decrease_stock(products_by_id, order_data.items)

            order = Order(
                customer_id=customer.id,
                total_amount=total_amount,
                items=order_items
            )

            self.order_repository.create(order)

            self.db.commit()
            self.db.refresh(order)

            return order

        except Exception:
            self.db.rollback()
            raise

    def get_order_by_id(self, order_id: int) -> Order:
        """
        Busca um pedido pelo ID.
        """
        order = self.order_repository.get_by_id(order_id)

        if order is None:
            raise OrderNotFoundException(f"Pedido não encontrado: {order_id}")

        return order

    def get_all_orders(self) -> list[Order]:
        """
        Retorna todos os pedidos cadastrados.
        """
        return self.order_repository.get_all()
