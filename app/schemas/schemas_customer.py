import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome é obrigatório.")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_PATTERN.fullmatch(value):
            raise ValueError("E-mail inválido.")
        return value


class CustomerUpdate(CustomerCreate):
    """PUT: substitui os dados cadastrais do cliente."""


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
