import uuid

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Feedback
from sqlalchemy import and_


class FeedbackDAL:
    """Data Access Layer for operating feedback info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
            self,
            email: uuid.UUID,
            description: str,
            loc_id: uuid.UUID,
            new_status,
    ) -> Feedback:
        new_feedback = Feedback(
            user_email=email,
            localization_id=loc_id,
            description=description,
            status=new_status,
        )
        self.db_session.add(new_feedback)
        await self.db_session.flush()
        return new_feedback

    async def update(
            self,
            email: uuid.UUID,
            loc_id: uuid.UUID,
            new_description: str,
            new_status,
    ) -> Feedback:
        query = (
            update(Feedback)
            .where(and_(Feedback.user_email == email, Feedback.localization_id == loc_id))
            .values(description=new_description, status=new_status)
        )

        res = await self.db_session.execute(query)
        await self.db_session.flush()

        try:
            return bool(res.one_or_none())
        except Exception:
            return False

    async def delete(
            self,
            email: uuid.UUID,
            loc_id: uuid.UUID
    ) -> bool:
        query = (
            delete(Feedback)
            .where(and_(Feedback.user_email == email, Feedback.localization_id == loc_id))
        )

        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def get(self, email: str, loc_id: uuid.UUID) -> Feedback:
        query = (
            select(Feedback)
            .where(and_(Feedback.user_email == email, Feedback.localization_id == loc_id))
        )

        res = await self.db_session.execute(query)
        obj = res.first()

        return None if obj is None else obj[0]
