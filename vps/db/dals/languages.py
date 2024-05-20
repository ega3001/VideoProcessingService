from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Language


class LanguagesDAL:
    """Data Access Layer for operating localization info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_list(self) -> List[Language]:
        query = select(Language)

        res = await self.db_session.execute(query)
        await self.db_session.flush()

        return [r[0] for r in res.fetchall()]

    async def get_by_id(self, lang_id) -> Language:
        query = select(Language).where(Language.id == lang_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return res.fetchone()[0]
