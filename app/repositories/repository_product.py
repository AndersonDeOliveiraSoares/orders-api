from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models_product import Product


class ProductRepository:
    """
    Repositório responsável pelo acesso aos dados de Product.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """
        Busca um produto pelo ID.

        Retorna Product se encontrado ou None caso contrário.
        """
        return self.db.get(Product, product_id)

    def get_by_ids(self, product_ids: list[int]) -> list[Product]:
        """
        Busca vários produtos pelos seus IDs.

        Retorna uma lista de produtos encontrados.
        """
        statement = select(Product).where(Product.id.in_(product_ids))

        return list(self.db.scalars(statement).all())

    def get_by_ids_for_update(self, product_ids: list[int]) -> list[Product]:
        """
        Busca produtos pelos IDs e bloqueia suas linhas
        durante a transação atual.

        Retorna uma lista de produtos encontrados.
        """
        statement = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        )

        return list(self.db.scalars(statement).all())