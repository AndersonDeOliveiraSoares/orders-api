from sqlalchemy.orm import Session

from app.models.models_product import Product
from app.repositories.repository_product import ProductRepository
from app.schemas.schemas_product import ProductCreate, ProductUpdate
from app.exceptions.exceptions_product import (
    ProductNotFoundException,
    ProductHasOrdersException,
)


class ProductService:
    """Serviço responsável pelas regras de negócio dos produtos."""

    def __init__(self, db: Session):
        self.db = db
        self.product_repository = ProductRepository(db)

    def create_product(self, product_data: ProductCreate) -> Product:
        try:
            product = Product(**product_data.model_dump())
            self.product_repository.create(product)
            self.db.commit()
            self.db.refresh(product)
            return product
        except Exception:
            self.db.rollback()
            raise

    def get_product_by_id(self, product_id: int) -> Product:
        product = self.product_repository.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundException(
                f"Produto não encontrado: {product_id}"
            )
        return product

    def get_all_products(self) -> list[Product]:
        return self.product_repository.get_all()

    def update_product(
        self,
        product_id: int,
        product_data: ProductUpdate
    ) -> Product:
        try:
            product = self.get_product_by_id(product_id)
            for field, value in product_data.model_dump().items():
                setattr(product, field, value)
            self.db.commit()
            self.db.refresh(product)
            return product
        except Exception:
            self.db.rollback()
            raise

    def delete_product(self, product_id: int) -> None:
        try:
            product = self.get_product_by_id(product_id)

            if self.product_repository.has_orders(product_id):
                raise ProductHasOrdersException(
                    f"Não é possível excluir o produto {product_id}: "
                    "ele está associado a pedidos."
                )

            self.product_repository.delete(product)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
