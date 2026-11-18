from typing import Optional

from sqlalchemy.orm import Session

from app.models.models_customer import Customer


class CustomerRepository:
    """
    Repositório responsável pelo acesso aos dados de Customer.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: int) -> Optional[Customer]:
        """
        Busca um cliente pelo ID.

        Retorna Customer se encontrado ou None caso contrário.
        """
        return self.db.get(Customer, customer_id)