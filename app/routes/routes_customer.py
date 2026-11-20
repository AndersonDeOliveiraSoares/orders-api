from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database.database_connection import get_db
from app.schemas.schemas_customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.service_customer import CustomerService

router = APIRouter(tags=["Customers"])


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED
)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    service = CustomerService(db)
    return service.create_customer(customer_data)


@router.get(
    "/customers",
    response_model=list[CustomerResponse],
    status_code=status.HTTP_200_OK
)
def get_all_customers(db: Session = Depends(get_db)):
    service = CustomerService(db)
    return service.get_all_customers()


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK
)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    service = CustomerService(db)
    return service.get_customer_by_id(customer_id)


@router.put(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK
)
def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db)
):
    service = CustomerService(db)
    return service.update_customer(customer_id, customer_data)


@router.delete(
    "/customers/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    service = CustomerService(db)
    service.delete_customer(customer_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
