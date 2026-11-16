from pydantic import BaseModel, Field, model_validator


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    items: list[OrderItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_duplicate_products(self):
        seen = set()

        for item in self.items:
            if item.product_id in seen:
                raise ValueError(f"Produto duplicado: {item.product_id}")
            seen.add(item.product_id)

        return self