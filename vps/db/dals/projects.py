import uuid
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy import update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import null

from db.models import Project
from core.status import StatusEnum


class ProjectDAL:
    """Data Access Layer for operating project info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        video_name: str,
        preview_name: str,
        lang_id: uuid.UUID,
        duration: float = None,
        with_id: uuid.UUID = None,
    ) -> Project:
        new_prj = Project(
            user_id=user_id,
            name=name,
            source_name=video_name,
            source_language_id=lang_id,
            preview_name=preview_name,
        )
        if duration:
            new_prj.duration_in_sec = duration
        if with_id:
            new_prj.id = with_id

        self.db_session.add(new_prj)
        await self.db_session.flush()
        return new_prj

    async def delete(self, prj_id: uuid.UUID) -> bool:
        query = delete(Project).where(Project.id == prj_id)
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def check_existance(self, prj_id: uuid.UUID) -> bool:
        query = select(Project).where(Project.id == prj_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return bool(res.one_or_none())

    async def get_by_id(self, prj_id: uuid.UUID) -> Project:
        query = select(Project).where(Project.id == prj_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return res.fetchone()[0]
    
    async def get_list_created_before(self, before_date: datetime) -> List[Project]:
        query = select(Project).where((Project.status == StatusEnum.created) & (Project.created < before_date))
        res = await self.db_session.execute(query)
        await self.db_session.flush()

        return [r[0] for r in res.fetchall()]

    async def belongs_to_user(self, prj_id: uuid.UUID, usr_id: uuid.UUID) -> bool:
        query = select(Project).where(
            (Project.id == prj_id) & (Project.user_id == usr_id)
        )
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        if res.one_or_none() is None:
            return False
        return True

    async def get_list_by_user_id(
        self, usr_id: uuid.UUID, processed: bool = False
    ) -> List[Project]:
        if processed:
            query = select(Project).where(
                (Project.user_id == usr_id)
                & (Project.status.in_((StatusEnum.failed, StatusEnum.processed)))
            )
        else:
            query = select(Project).where(Project.user_id == usr_id)

        res = await self.db_session.execute(query)
        await self.db_session.flush()

        return [r[0] for r in res.fetchall()]

    async def update_task_id(self, prj_id: uuid.UUID, task_id: uuid.UUID) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(task_id=task_id, updated=datetime.utcnow())
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def clear_task_id(self, prj_id: uuid.UUID) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(task_id=null, updated=datetime.utcnow())
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def update_name(self, prj_id: uuid.UUID, name: str) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(name=name, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_duration(self, prj_id: uuid.UUID, duration: int) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(duration_in_sec=duration, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_speech_data(self, prj_id: uuid.UUID, speech_data) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(parsed_speech_data=speech_data, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_status(self, prj_id: uuid.UUID, status) -> bool:
        query = (
            update(Project)
            .where(Project.id == prj_id)
            .values(status=status, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True
