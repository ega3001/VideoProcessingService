import uuid
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy import update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import null

from db.models import Subscription, UserSubscription
from core.status import StatusEnum


class SubscriptionDAL:
    """Data Access Layer for operating subscriptions info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user_sub(
        self,
        user_id: uuid.UUID,
        sub_id: uuid.UUID,
        stripe_sub_id: uuid.UUID
    ) -> UserSubscription:
        sub = await self.get_sub(sub_id)
        new_sub = UserSubscription(
            user_id=user_id,
            subscription_id=sub_id,
            stripe_sub_id=stripe_sub_id,
            valid_until=datetime.utcnow() + sub.duration,
            renewal_active=True
        )

        self.db_session.add(new_sub)
        await self.db_session.flush()
        return new_sub
    
    async def reactivate_user_sub(self, user_id: uuid.UUID) -> bool:
        user_sub = await self.get_user_sub(user_id)
        if not user_sub:
            return False
        sub = await self.get_sub(user_sub.subscription_id)
        query = update(UserSubscription).where(UserSubscription.id == user_sub.id).values(
            valid_until=user_sub.valid_until + sub.duration,
            renewal_active=True,
            updated=datetime.utcnow()
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True
    
    async def disable_user_sub(self, user_id: uuid.UUID) -> bool:
        user_sub = await self.get_user_sub(user_id)
        if not user_sub:
            return False
        query = update(UserSubscription).where(UserSubscription.id == user_sub.id).values(
            renewal_active=False,
            updated=datetime.utcnow()
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def get_user_sub(self, user_id: uuid.UUID) -> UserSubscription:
        query = select(UserSubscription).where((UserSubscription.user_id==user_id) & (UserSubscription.valid_until > datetime.utcnow()))
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        if not res.first():
            return None
        return res.fetchone()[0]
    
    async def get_sub(self, sub_id: uuid.UUID) -> Subscription:
        query = select(Subscription).where(Subscription.id == sub_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return res.fetchone()[0]
    
    async def get_list_subs(self) -> List[Subscription]:
        query = select(Subscription)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return [r[0] for r in res.fetchall()]
    
    async def update_stripe_sub_id(self, sub_id: uuid.UUID, stripe_sub_id: str) -> bool:
        query = update(Subscription).where(Subscription.id == sub_id).values(
            stripe_sub_id=stripe_sub_id,
            updated=datetime.utcnow()
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def delete_user_sub(self, user_sub_id: uuid.UUID) -> bool:
        query = delete(UserSubscription).where(UserSubscription.id == user_sub_id)
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True
