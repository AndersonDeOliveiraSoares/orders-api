
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models_outbox import OutboxEvent


class OutboxRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, event: OutboxEvent) -> OutboxEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def get_pending_events(
            self,
            limit: int = 100,
            event_ids: list[int] | None = None,
    ) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at, OutboxEvent.id)
            .limit(limit)
        )

        if event_ids is not None:
            statement = statement.where(
                OutboxEvent.id.in_(event_ids)
            )

        return list(self.db.scalars(statement).all())

    def mark_as_published(self, event: OutboxEvent) -> OutboxEvent:
        event.status = "PUBLISHED"
        event.published_at = datetime.now(timezone.utc)

        self.db.flush()

        return event
