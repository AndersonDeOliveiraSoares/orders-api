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
    # def get_by_id(self, order_id: int) -> Optional[Order]:
    #     """
    #     Busca um pedido pelo ID.
    #
    #     Retorna Order se encontrado ou None caso contrário.
    #     """
    #     return self.db.get(Order, order_id)

    def get_all(self) -> list[Order]:
        """
        Lista todos os pedidos cadastrados.

        Retorna uma lista de objetos Order.
        """
        statement = select(Order).order_by(Order.id)

        return list(self.db.scalars(statement).all())

    def create(self, order: Order) -> Order:
        """
        Adiciona um novo pedido à sessão do banco.

        Retorna o objeto Order.
        """
        self.db.add(order)

        return order