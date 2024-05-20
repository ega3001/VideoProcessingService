import uuid
import logging

from celery.result import AsyncResult
from fastapi import Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.actions.users import get_current_user
from api.exceptions import ownership_exception
from db.session import get_db
from api import pydantic_models as models
from db.dals.projects import ProjectDAL
from db.dals.localizations import LocalizationDAL
from core.storages import ProjectFiles


async def delete_user_projects(session: AsyncResult, user_id: uuid.UUID) -> bool:
    async with session.begin():
        project_dal = ProjectDAL(session)
        projects = await project_dal.get_list_by_user_id(user_id)

    for project in projects:
        await delete_project(session, project.id)

    return True


async def delete_project(session: AsyncSession, prj_id: uuid.UUID) -> bool:
    async with session.begin():
        localization_dal = LocalizationDAL(session)
        localizations = await localization_dal.get_list_by_project_id(prj_id)

    for loc in localizations:
        await delete_localization(session, loc.id)

    async with session.begin():
        project_dal = ProjectDAL(session)
        project = await project_dal.get_by_id(prj_id)
        if project.task_id:
            AsyncResult(project.task_id).revoke(terminate=True)
        ProjectFiles(prj_id).delete_files()
        await project_dal.delete(prj_id)

    return True


async def delete_localization(session: AsyncSession, loc_id: uuid.UUID) -> bool:
    async with session.begin():
        localization_dal = LocalizationDAL(session)
        localization = await localization_dal.get_by_id(loc_id)

        if localization.task_id:
            AsyncResult(localization.task_id).revoke(terminate=True)
        if localization.result_name:
            ProjectFiles(localization.project_id).delete_file(localization.result_name)
        await localization_dal.delete_by_id(localization.id)

    return True


async def check_project_ownership(
    body: models.ProjectID = Depends(),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        project_dal = ProjectDAL(db)
        if not await project_dal.belongs_to_user(body.prj_id, current_user.id):
            # todo: raise error instead
            raise ownership_exception

    return body


async def check_localization_ownership(
    body: models.LocalizationID = Depends(),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    async with db.begin():
        localization = await LocalizationDAL(db).get_by_id(body.loc_id)
        if localization.project_id != body.prj_id:
            # todo: raise error instead
            raise ownership_exception
        project = await ProjectDAL(db).get_by_id(localization.project_id)
        if project.user_id != current_user.id:
            # todo: raise error instead
            raise ownership_exception

    return body
