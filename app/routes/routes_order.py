from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.database_connection import get_db
from app.schemas.schemas_order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.service_order import OrderService

router = APIRouter(tags=["Orders"])


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.create_order(order_data)


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.get_order_by_id(order_id)


@router.get(
    "/orders",
    response_model=list[OrderResponse],
    status_code=status.HTTP_200_OK
)
def get_all_orders(
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.get_all_orders()


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK
)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.update_order_status(order_id, status_data.status)
