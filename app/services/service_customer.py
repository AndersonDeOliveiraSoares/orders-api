from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.exceptions_customer import (
    CustomerEmailAlreadyExistsException,
    CustomerHasOrdersException,
    CustomerNotFoundException,
)
from app.models.models_customer import Customer
from app.repositories.repository_customer import CustomerRepository
from app.schemas.schemas_customer import CustomerCreate, CustomerUpdate


class CustomerService:
    """Serviço responsável pelas regras de negócio dos clientes."""

    def __init__(self, db: Session):
        self.db = db
        self.customer_repository = CustomerRepository(db)

    def _get_customer_or_raise(self, customer_id: int) -> Customer:
        customer = self.customer_repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundException(
                f"Cliente não encontrado: {customer_id}"
            )
        return customer

    def _validate_email(
        self,
        email: str,
        exclude_customer_id: int | None = None
    ) -> None:
        existing = self.customer_repository.get_by_email(
            email,
            exclude_customer_id=exclude_customer_id
        )
        if existing is not None:
            raise CustomerEmailAlreadyExistsException(
                f"E-mail já cadastrado: {email}"
            )

    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        self._validate_email(customer_data.email)
        customer = Customer(
            name=customer_data.name,
            email=customer_data.email
        )

        try:
            self.customer_repository.create(customer)
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except IntegrityError as exc:
            self.db.rollback()
            raise CustomerEmailAlreadyExistsException(
                f"E-mail já cadastrado: {customer_data.email}"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def get_customer_by_id(self, customer_id: int) -> Customer:
        return self._get_customer_or_raise(customer_id)

    def get_all_customers(self) -> list[Customer]:
        return self.customer_repository.get_all()

    def update_customer(
        self,
        customer_id: int,
        customer_data: CustomerUpdate
    ) -> Customer:
        customer = self._get_customer_or_raise(customer_id)
        self._validate_email(
            customer_data.email,
            exclude_customer_id=customer_id
        )

        customer.name = customer_data.name
        customer.email = customer_data.email

        try:
            self.db.commit()
            self.db.refresh(customer)
            return customer
        except IntegrityError as exc:
            self.db.rollback()
            raise CustomerEmailAlreadyExistsException(
                f"E-mail já cadastrado: {customer_data.email}"
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def delete_customer(self, customer_id: int) -> None:
        customer = self._get_customer_or_raise(customer_id)

        if self.customer_repository.has_orders(customer_id):
            raise CustomerHasOrdersException(
                f"Não é possível excluir o cliente {customer_id}: "
                "existem pedidos associados."
            )

        try:
            self.customer_repository.delete(customer)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
