import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api import pydantic_models as models
from api.actions.users import share, get_share_project, get_current_user

from core.status import FeedbackEnum
from core.storages import ProjectFiles
from core.security import Config

from db.session import get_db
from db.dals.projects import ProjectDAL
from db.dals.localizations import LocalizationDAL

router = APIRouter()
logger = logging.getLogger("routers")


@router.get(
    path="/share/{token}",
    tags=["Share"],
    description="Open a shared project.",
)
async def get_shared_project(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> models.ShareInfo:

    prj_id = get_share_project(token)
    async with db.begin():
        localization_dal = LocalizationDAL(db)
        project_dal = ProjectDAL(db)
        project = await project_dal.get_by_id(prj_id)
        localizations = await localization_dal.get_list_by_project_id(prj_id)

    localizations_list = []

    files = ProjectFiles(prj_id)

    prj_dict = project.__dict__
    prj_dict["source_path"] = files.get_file_link(project.source_name)
    prj_dict["preview_path"] = files.get_file_link(project.preview_name)
    project = models.ProjectInfo.parse_obj(prj_dict)

    for item in localizations:
        loc_dict = item.__dict__

        loc_dict["like"] = FeedbackEnum.empty

        loc_dict["result_path"] = files.get_file_link(
            loc_dict["result_name"], checks=False
        )
        localizations_list.append(models.LocalizationInfo.parse_obj(loc_dict))

    return models.ShareInfo(project=project, localizations=localizations_list)


@router.post(
    path="/shared/{prj_id}",
    tags=["Share"],
    description="Share a project.",
)
async def share_project(prj_id: str, current_user: models.UserInfo = Depends(get_current_user)) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=f'{Config.FRONTEND_URL}/share?token={share(prj_id)}'
    )
