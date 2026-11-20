from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database_connection import get_db
from app.schemas.schemas_product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from app.services.service_product import ProductService

router = APIRouter(tags=["Products"])


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    return ProductService(db).create_product(product_data)


@router.get(
    "/products",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK
)
def get_all_products(db: Session = Depends(get_db)):
    return ProductService(db).get_all_products()


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    return ProductService(db).get_product_by_id(product_id)


@router.put(
    "/products/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db)
):
    return ProductService(db).update_product(product_id, product_data)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    ProductService(db).delete_product(product_id)
    return None
