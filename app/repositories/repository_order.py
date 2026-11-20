from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models_order import Order


class OrderRepository:

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        statement = select(Order).where(Order.id == order_id)
        return self.db.scalars(statement).first()

    def get_by_id_for_update(self, order_id: int) -> Optional[Order]:
        """Busca e bloqueia o pedido até o fim da transação."""
        statement = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
        )
        return self.db.scalars(statement).first()

    def get_all(self) -> list[Order]:
        statement = select(Order).order_by(Order.id)
        return list(self.db.scalars(statement).all())

    def create(self, order: Order) -> Order:
        self.db.add(order)
        return order

    def update_status(self, order: Order, status: str) -> Order:
        order.status = status
        return order
