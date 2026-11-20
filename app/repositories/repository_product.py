from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models_product import Product
from app.models.models_order import OrderItem


class ProductRepository:
    """Repositório responsável pelo acesso aos dados de Product."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product: Product) -> Product:
        self.db.add(product)
        self.db.flush()
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        return self.db.get(Product, product_id)

    def get_by_ids(self, product_ids: list[int]) -> list[Product]:
        statement = select(Product).where(Product.id.in_(product_ids))
        return list(self.db.scalars(statement).all())

    def get_by_ids_for_update(self, product_ids: list[int]) -> list[Product]:
        statement = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        )
        return list(self.db.scalars(statement).all())

    def get_all(self) -> list[Product]:
        statement = select(Product).order_by(Product.id)
        return list(self.db.scalars(statement).all())

    def has_orders(self, product_id: int) -> bool:
        statement = select(OrderItem.id).where(
            OrderItem.product_id == product_id
        ).limit(1)
        return self.db.scalar(statement) is not None

    def delete(self, product: Product) -> None:
        self.db.delete(product)
