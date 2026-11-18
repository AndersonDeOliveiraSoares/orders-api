from fastapi import APIRouter, status

from app.schemas.schemas_order import OrderCreate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate):
    # Provisório: ainda não existe Service. Só devolve o que foi validado.
    return order.model_dump()