from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models_customer import Customer
from app.models.models_order import Order


class CustomerRepository:
    """Repositório responsável pelo acesso aos dados de Customer."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        return self.db.get(Customer, customer_id)

    def get_all(self) -> list[Customer]:
        statement = select(Customer).order_by(Customer.id)
        return list(self.db.scalars(statement).all())

    def get_by_email(
        self,
        email: str,
        exclude_customer_id: Optional[int] = None
    ) -> Optional[Customer]:
        statement = select(Customer).where(
            func.lower(Customer.email) == email.lower()
        )
        if exclude_customer_id is not None:
            statement = statement.where(
                Customer.id != exclude_customer_id
            )
        return self.db.scalar(statement)

    def has_orders(self, customer_id: int) -> bool:
        statement = (
            select(Order.id)
            .where(Order.customer_id == customer_id)
            .limit(1)
        )
        return self.db.scalar(statement) is not None

    def delete(self, customer: Customer) -> None:
        self.db.delete(customer)
