from sqlalchemy import select
from sqlalchemy import update
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from api.exceptions import promocodeOutdated_exception, promocodeNotValid_exception, promocodeUsed_exception
from db.models import UserPromocode, User, Promocode


class PromocodesDAL:
    """Data Access Layer for operating promocodes"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def apply_promocode(self, promocode: str, user_id) -> int:
        table_promocode = await self.promocode_is_valid(promocode)

        query = select(UserPromocode).where(
            UserPromocode.user_id == user_id,
            UserPromocode.promocode_id == table_promocode.id,
        )
        res = await self.db_session.execute(query)
        applied_promocode = res.fetchone()

        if applied_promocode is not None:
            raise promocodeUsed_exception

        used_promocode = UserPromocode(user_id=user_id, promocode_id=table_promocode.id)

        self.db_session.add(used_promocode)
        await self.db_session.flush()

        query = select(User).where(User.id == user_id)

        res = await self.db_session.execute(query)
        current_balance = res.fetchone()[0].balance

        query = (
            update(User)
            .where(User.id == user_id)
            .values(balance=(current_balance + table_promocode.value))
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return table_promocode.value

    async def promocode_is_valid(self, promocode: str) -> Promocode:
        query = select(Promocode).where(Promocode.code == promocode)
        res = await self.db_session.execute(query)
        table_promocode = res.fetchone()

        if table_promocode is None:
            raise promocodeNotValid_exception

        if table_promocode[0].expiration < datetime.utcnow():
            raise promocodeOutdated_exception

        return table_promocode[0]
