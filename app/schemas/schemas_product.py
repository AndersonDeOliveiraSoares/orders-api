from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    price: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=2)
    stock: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome do produto é obrigatório.")
        return value


class ProductUpdate(ProductCreate):
    pass


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    stock: int
