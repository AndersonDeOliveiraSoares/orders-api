
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.models_idempotency import IdempotencyKey


class IdempotencyRepository:

    def __init__(self, db: Session):
        self.db = db

    def try_create(
        self,
        idempotency_key: str,
        request_hash: str,
    ) -> bool:
        """
        Tenta reservar uma chave idempotente.

        Retorna True se a chave foi criada.
        Retorna False se ela já existe.
        """
        statement = (
            insert(IdempotencyKey)
            .values(
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(
                index_elements=["idempotency_key"]
            )
            .returning(IdempotencyKey.id)
        )

        result = self.db.execute(statement)

        return result.scalar_one_or_none() is not None

    def get_by_key(
        self,
        idempotency_key: str,
    ) -> IdempotencyKey | None:
        statement = select(IdempotencyKey).where(
            IdempotencyKey.idempotency_key == idempotency_key
        )

        return self.db.scalars(statement).first()

    def update_order_id(
        self,
        idempotency: IdempotencyKey,
        order_id: int,
    ) -> IdempotencyKey:
        idempotency.order_id = order_id
        return idempotency
