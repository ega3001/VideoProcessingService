import uuid
from datetime import datetime
from typing import Union, List

from sqlalchemy import select
from sqlalchemy import update, delete, null
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Localization, Project
from core.status import StatusEnum


class LocalizationDAL:
    """Data Access Layer for operating project info"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(
        self,
        prj_id: uuid.UUID,
        target_lang_id: uuid.UUID,
        target_voice_name: str,
        duration: int,
        estimated: datetime
    ) -> Localization:
        new_loc = Localization(
            project_id=prj_id,
            target_language_id=target_lang_id,
            target_voice_name=target_voice_name,
            duration_in_sec=duration,
            estimated_completion_date=estimated
        )

        self.db_session.add(new_loc)
        await self.db_session.flush()
        return new_loc

    async def delete_by_id(self, loc_id: uuid.UUID) -> bool:
        query = delete(Localization).where(Localization.id == loc_id)
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def delete_by_project_id(self, prj_id: uuid.UUID) -> bool:
        query = delete(Localization).where(Localization.project_id == prj_id)
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def check_existance(self, loc_id: uuid.UUID) -> bool:
        query = select(Localization).where(Localization.id == loc_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return bool(res.one_or_none())
    
    async def get_list_created_before(self, before_date: datetime) -> List[Localization]:
        query = select(Project).where((Project.status == StatusEnum.created) & (Project.created < before_date))
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return [r[0] for r in res.fetchall()]

    async def get_list_by_project_id(self, prj_id: uuid.UUID) -> List[Localization]:
        query = select(Localization).where(Localization.project_id == prj_id)

        res = await self.db_session.execute(query)
        await self.db_session.flush()

        return [r[0] for r in res.fetchall()]

    async def get_list_by_user_id(
        self, usr_id: uuid.UUID, processed: bool
    ) -> List[Localization]:
        if processed:
            query = (
                select(Localization)
                .join(Project, Project.id == Localization.project_id)
                .where(
                    (Project.user_id == usr_id)
                    & (
                        Localization.status.in_(
                            (StatusEnum.failed, StatusEnum.processed)
                        )
                    )
                    & (Localization.task_id != null)
                )
            )
        else:
            query = (
                select(Localization)
                .join(Project, Project.id == Localization.project_id)
                .where(Project.user_id == usr_id)
            )

        res = await self.db_session.execute(query)
        await self.db_session.flush()

        return [r[0] for r in res.fetchall()]

    async def get_by_id(self, loc_id: uuid.UUID) -> Localization:
        query = select(Localization).where(Localization.id == loc_id)
        res = await self.db_session.execute(query)
        await self.db_session.flush()
        return res.fetchone()[0]

    async def update_task_id(self, loc_id: uuid.UUID, task_id: uuid.UUID) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(task_id=task_id, updated=datetime.utcnow())
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True

    async def clear_task_id(self, loc_id: uuid.UUID) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(task_id=null, updated=datetime.utcnow())
        )
        await self.db_session.execute(query)
        await self.db_session.flush()
        return True
    
    async def update_estimated(self, loc_id: uuid.UUID, estimated_date: datetime) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(estimated_completion_date=estimated_date, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_result_path(self, loc_id: uuid.UUID, result_name: str) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(result_name=result_name, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_duration(self, loc_id: uuid.UUID, duration) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(duration_in_sec=duration, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_speech_data(self, loc_id: uuid.UUID, speech_data) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(parsed_speech_data=speech_data, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True

    async def update_status(self, loc_id: uuid.UUID, status) -> bool:
        query = (
            update(Localization)
            .where(Localization.id == loc_id)
            .values(status=status, updated=datetime.utcnow())
        )

        await self.db_session.execute(query)
        await self.db_session.flush()

        return True
