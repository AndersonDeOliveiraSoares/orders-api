import pytest
from pydantic import ValidationError

from app.schemas.schemas_order import OrderCreate

VALID_ITEM = {"product_id": 10, "quantity": 1}


def test_valid_order_is_accepted():
    order = OrderCreate(
        customer_id=1,
        items=[
            {"product_id": 10, "quantity": 2},
            {"product_id": 25, "quantity": 1},
        ],
    )

    assert order.customer_id == 1
    assert len(order.items) == 2


def test_duplicate_product_is_rejected():
    with pytest.raises(ValidationError) as exc_info:
        OrderCreate(
            customer_id=1,
            items=[
                {"product_id": 10, "quantity": 2},
                {"product_id": 10, "quantity": 3},
            ],
        )

    assert "Produto duplicado: 10" in str(exc_info.value)


@pytest.mark.parametrize(
    "payload",
    [
        {"customer_id": 1, "items": [{"product_id": 10, "quantity": 0}]},
        {"customer_id": 1, "items": [{"product_id": 10, "quantity": -5}]},
        {"customer_id": 1, "items": []},
        {"customer_id": 0, "items": [VALID_ITEM]},
        {"customer_id": -1, "items": [VALID_ITEM]},
        {"customer_id": 1, "items": [{"product_id": 0, "quantity": 1}]},
        {"customer_id": 1, "items": [{"product_id": -10, "quantity": 2}]},
    ],
)
def test_invalid_payload_is_rejected(payload):
    with pytest.raises(ValidationError):
        OrderCreate(**payload)