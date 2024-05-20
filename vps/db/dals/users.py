from uuid import UUID

import logging

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Union

from sqlalchemy import select
from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.hashing import Hasher
from db.models import User, UserPromocode


logger = logging.getLogger(__name__)

class UserDAL:
    """Data Access Layer for operating user info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
        self,
        email: str,
        password: str,
        name: str,
        verified=False,
        used_sso=False,
    ) -> User:
        new_user = User(
            email=email,
            hashed_password=Hasher.get_password_hash(password),
            name=name,
            is_verified=verified,
            used_sso=used_sso,
            balance=3,
        )

        self.db_session.add(new_user)
        await self.db_session.flush()

        return new_user

    async def verify_email(self, email: str) -> bool:
        query = update(User).where(User.email == email).values(is_verified=True)

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_name(self, user_id: UUID, new_name: str) -> bool:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(name=new_name, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_email(self, user_id: UUID, new_email: str) -> bool:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(email=new_email, is_verified=False, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_password(self, user_id: UUID, new_password: str) -> bool:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=Hasher.get_password_hash(new_password),
                updated=datetime.utcnow(),
            )
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_balance(self, user_id: UUID, delta: int) -> bool:
        current_balance = (await self.get_by_id(user_id)).balance

        if (current_balance + delta) < 0:
            return False

        query = (
            update(User)
            .where(User.id == user_id)
            .values(balance=(current_balance + delta), updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def get_by_id(self, user_id: UUID) -> Union[User, None]:
        query = select(User).where(User.id == user_id)
        res = await self.db_session.execute(query)
        user_row = res.fetchone()

        if user_row is not None:
            return user_row[0]

    async def get_by_email(self, email: str) -> Union[User, None]:
        query = select(User).where(User.email == email)
        res = await self.db_session.execute(query)
        user_row = res.fetchone()

        if user_row is not None:
            return user_row[0]

        return None

    async def authenticate(self, email: str, password: str) -> Union[User, None]:
        user = await self.get_by_email(email)

        if not user:
            return None
        if not Hasher.verify_password(password, user.hashed_password):
            return None

        return user

    async def update_last_email_request(self, user_id: UUID) -> bool:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(last_email_request=datetime.utcnow(), updated=datetime.utcnow())
        )
        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_project_stats(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        current_created_prj = user.total_created_prj
        current_created_loc = user.total_created_loc

        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                total_created_prj=current_created_prj + 1,
                total_created_loc=current_created_loc + 1,
                updated=datetime.utcnow(),
            )
        )
        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_localization_stats(self, user_id: UUID) -> bool:
        current_created_loc = (await self.get_by_id(user_id)).total_created_loc

        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                total_created_loc=current_created_loc + 1, updated=datetime.utcnow()
            )
        )
        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def delete(self, user_id: UUID):
        # todo: add subscriptions, payments deletion
        query = delete(UserPromocode).where(UserPromocode.user_id == user_id)

        await self.db_session.execute(query)
        await self.db_session.flush()

        query = delete(User).where(User.user_id == user_id)

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_status_invitation_to_castdev(self, user_id: UUID) -> bool:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(has_been_invited_to_castdev=True)
        )
        await self.db_session.execute(query)
        await self.db_session.flush()

        return True
