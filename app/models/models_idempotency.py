
from sqlalchemy import (
    ForeignKey,
    String,
    DateTime,
    UniqueConstraint,
    func,
)
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models_base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_idempotency_keys_key",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    request_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
