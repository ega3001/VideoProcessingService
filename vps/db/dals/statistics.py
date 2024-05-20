import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import StatisticEvent
from core.status import StatEventTypeEnum


class StatsDAL:
    """Data Access Layer for operating statistics info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
            self,
            user_id: uuid.UUID,
            event_type: StatEventTypeEnum,
            meta: dict,
    ) -> StatisticEvent:
        new_stat = StatisticEvent(
            user_id=user_id,
            event_type=event_type,
            meta=meta,
        )
        self.db_session.add(new_stat)
        await self.db_session.flush()
        return new_stat
