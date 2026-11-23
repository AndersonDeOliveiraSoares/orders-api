
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.database.database_connection import get_db
from app.schemas.schemas_order import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
)
from app.services.service_order import OrderService


router = APIRouter(tags=["Orders"])


ERROR_RESPONSES = {
    404: {
        "description": "Recurso não encontrado",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Cliente não encontrado: 999999"
                }
            }
        },
    },
    409: {
        "description": "Conflito com as regras de negócio",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Estoque insuficiente para o produto Produto Teste Swagger. Disponível: 10, solicitado: 15."
                }
            }
        },
    },
    422: {
        "description": "Dados enviados inválidos",
    },
}


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=255,
    ),
):
    correlation_id = str(uuid4())

    service = OrderService(db)

    return service.create_order(
        order_data,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: ERROR_RESPONSES[404],
    },
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
    status_code=status.HTTP_200_OK,
)
def get_all_orders(
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.get_all_orders()


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: ERROR_RESPONSES[404],
        409: ERROR_RESPONSES[409],
        422: ERROR_RESPONSES[422],
    },
)
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    return service.update_order_status(order_id, status_data.status)
