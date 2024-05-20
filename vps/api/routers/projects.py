import os
import asyncio
import uuid
import logging
from typing import Optional
from datetime import timedelta, datetime, timezone

from celery import signature
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Form,
    HTTPException,
    status,
    UploadFile,
    File,
    BackgroundTasks
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from api import pydantic_models as models
from api.exceptions import *
from api.services import voices, WebsocketService
from api.actions.users import get_current_user, get_cent_token
from api.actions.projects import (
    check_project_ownership,
    check_localization_ownership,
    delete_localization,
    delete_project,
)
from db.dals.projects import ProjectDAL
from db.dals.localizations import LocalizationDAL
from db.dals.feedbacks import FeedbackDAL
from db.dals.users import UserDAL
from db.dals.languages import LanguagesDAL

from core.status import StatusEnum, FeedbackEnum
from core.file_processor import preview_from_video, source_duration
from core.storages import ProjectFiles
from core.config import Config
from db.session import get_db

router = APIRouter()
logger = logging.getLogger("routers")


@router.get(
    path="/",
    tags=["Projects"],
    description="Get list of current user's projects.",
    response_model=models.ProjectsList,
    responses={401: {"description": "Not authenticated"}},
)
async def get_projects_list(
    request: Request,
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> models.ProjectsList:
    async with db.begin():
        project_dal = ProjectDAL(db)
        projects = await project_dal.get_list_by_user_id(current_user.id)

    projects_list = []

    for item in projects:
        files = ProjectFiles(item.id)
        prj_dict = item.__dict__
        prj_dict["source_path"] = files.get_file_link(item.source_name)
        prj_dict["preview_path"] = files.get_file_link(item.preview_name)
        projects_list.append(models.ProjectInfo.parse_obj(prj_dict))

    return models.ProjectsList(projects=projects_list)

from functools import wraps
def cent_update(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        bg_task = kwargs.get("bg_task")
        current_user = kwargs.get("current_user")
        bg_task.add_task(WebsocketService.publish,
                         current_user.id,
                         result)
        
        return result.data
    return wrapper

@router.post(
    path="/",
    tags=["Projects"],
    description="Create new user's project.",
    response_model=models.ProjectInfo,
    responses={401: {"description": "Not authenticated"}},
)
@cent_update
async def post_create_project(
    bg_task: BackgroundTasks,
    request: Request,
    name: str = Form(...),
    file_url: Optional[str] = Form(None),
    source_language_id: uuid.UUID = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> models.ProjectInfo:
    def sec_to_min(secs):
        return secs//60 + (secs % 60 > 0)

    project_uuid = uuid.uuid4()
    project_files = ProjectFiles(project_uuid)

    try:
        async with db.begin():
            source_lang = await LanguagesDAL(db).get_by_id(source_language_id)
        if not source_lang.source:
            raise incorrectLang_exception

        if file:
            file_name = await project_files.store_by_obj(file)
        elif file_url:
            file_name = project_files.store_by_youtube_url(file_url)
        else:
            raise noVideo_exception

        video_duration = source_duration(
            project_files.get_file_path(file_name)
        )
        if video_duration > Config.VIDEO_MAX_DURATION:
            raise bigVideo_exception

        if current_user.balance < sec_to_min(video_duration):
            raise notEnoughFunds_exception

        preview_path = project_files.get_file_path(
            str(uuid.uuid4()) + ".jpg", checks=False)
        preview_from_video(
            project_files.get_file_path(file_name), preview_path)

        async with db.begin():
            project_dal = ProjectDAL(db)
            preview_name = os.path.basename(preview_path)
            project = await project_dal.create(
                current_user.id,
                name,
                file_name,
                preview_name,
                source_language_id,
                with_id=project_uuid,
                duration=video_duration,
            )

        task = signature(
            "process_video",
            args=(project.id,),
        ).delay()
        async with db.begin():
            await ProjectDAL(db).update_task_id(project.id, task.id)

        logger.info(
            f"User({current_user.id}) created new Project({project.id})"
        )

        return models.EventInfo(
            created = datetime.now(timezone.utc),
            object = "Project",
            object_id = project.id,
            event = "created project",
            data = models.ProjectInfo.model_validate(project)
        )
    except HTTPException:
        project_files.delete_files()
        raise


@router.patch(
    path="/{prj_id}",
    tags=["Projects"],
    description="Modify specified user's project.",
    responses={401: {"description": "Not authenticated"}},
)
async def patch_project(
    bg_task: BackgroundTasks,
    request: Request,
    body: models.ProjectID = Depends(check_project_ownership),
    name: str = Form(...),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with db.begin():
        prj_dal = ProjectDAL(db)
        await prj_dal.update_name(body.prj_id, name)
        prj = await prj_dal.get_by_id(body.prj_id)

    event = {"created": datetime.utcnow(),
             "object": "Project",
             "object_id": body.prj_id,
             "event": "update name",
             "data": models.ProjectInfo(**prj.__dict__)
             }

    bg_task.add_task(WebsocketService.publish,
                     current_user.id,
                     models.EventInfo(**event))

    logger.info(
        f"User({current_user.id}) changed Project({body.prj_id}) name to {name}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Project name successfully changed",
    )


@router.delete(
    path="/{prj_id}",
    tags=["Projects"],
    description="Delete specified user's project.",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_delete_project(
    request: Request,
    body: models.ProjectID = Depends(check_project_ownership),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await delete_project(db, body.prj_id)

    logger.info(f"User({current_user.id}) deleted Project({body.prj_id})")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Project successfully deleted",
    )


@router.get(
    path="/{prj_id}/localizations/",
    tags=["Projects/Localizations"],
    description="Get list of current project's localizations.",
    response_model=models.LocalizationsList,
    responses={401: {"description": "Not authenticated"}},
)
async def get_localizations_list(
    request: Request,
    body: models.ProjectID = Depends(check_project_ownership),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> models.LocalizationsList:
    async with db.begin():
        localization_dal = LocalizationDAL(db)
        feedback_dal = FeedbackDAL(db)
        localizations = await localization_dal.get_list_by_project_id(body.prj_id)

    localizations_list = []
    project_files = ProjectFiles(body.prj_id)

    for item in localizations:
        loc_dict = item.__dict__

        feedback = await feedback_dal.get(email=current_user.email, loc_id=item.id)
        loc_dict["like"] = FeedbackEnum.empty if feedback is None else feedback.status

        loc_dict["result_path"] = project_files.get_file_link(
            loc_dict["result_name"], checks=False
        )
        localizations_list.append(models.LocalizationInfo.parse_obj(loc_dict))

    return models.LocalizationsList(localizations=localizations_list)


@router.get(
    path="/voices",
    tags=["Projects/Localizations"],
    description="Get list of available localization voices.",
    response_model=models.VoicesList,
    responses={401: {"description": "Not authenticated"}},
)
async def get_localization_voices_list(
    request: Request,
    current_user: models.UserInfo = Depends(get_current_user),
) -> models.LocalizationsList:
    return models.VoicesList(
        voices=[
            models.VoiceInfo(name=v.name)
            for v in voices() if v.category == 'premade'
        ]
    )


@router.post(
    path="/{prj_id}/localizations/",
    tags=["Projects/Localizations"],
    description="Create new project's localization.",
    response_model=models.LocalizationInfo,
    responses={401: {"description": "Not authenticated"}},
)
async def post_create_localization(
    bg_task: BackgroundTasks,
    request: Request,
    body: models.ProjectID = Depends(check_project_ownership),
    target_language_id: uuid.UUID = Form(),
    target_voice_name: str = Form(),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> models.LocalizationInfo:
    def sec_to_min(secs):
        return secs//60 + (secs % 60 > 0)

    event = {"created": datetime.utcnow(),
             "object": "Localization",
             "object_id": "",
             "event": "create localization",
             "data": ""
             }

    async with db.begin():
        target_lang = await LanguagesDAL(db).get_by_id(target_language_id)
        if not target_lang.target:
            raise incorrectLang_exception

        project_dal = ProjectDAL(db)
        localization_dal = LocalizationDAL(db)
        project = await project_dal.get_by_id(body.prj_id)

        if current_user.balance < sec_to_min(project.duration_in_sec):
            raise notEnoughFunds_exception

        seconds = sec_to_min(project.duration_in_sec) * \
            Config.MIN_PROC_TIME_IN_SEC
        if project.status == StatusEnum.created:
            previous_prjs = await project_dal.get_list_created_before(project.created)
            for prj in previous_prjs:
                seconds += sec_to_min(prj.duration_in_sec) * \
                    Config.MIN_PROC_TIME_IN_SEC

        previous_locs = await localization_dal.get_list_created_before(datetime.utcnow())
        for loc in previous_locs:
            seconds += sec_to_min(loc.duration_in_sec) * \
                Config.MIN_PROC_TIME_IN_SEC

        localization = await localization_dal.create(
            body.prj_id,
            target_language_id,
            target_voice_name,
            project.duration_in_sec,
            estimated=datetime.utcnow() + timedelta(seconds=seconds)
        )
        await UserDAL(db).update_balance(current_user.id, -sec_to_min(project.duration_in_sec))
        event["object_id"] = localization.id
        event["data"] = models.LocalizationInfo(**localization.__dict__)
        bg_task.add_task(WebsocketService.publish,
                         current_user.id, models.EventInfo(**event))

    async with db.begin():
        localization_dal = LocalizationDAL(db)
        if project.status == StatusEnum.processed:
            task = signature(
                "process_subs",
                args=(localization.id,),
            ).delay()
            await localization_dal.update_task_id(localization.id, task.id)

            event["object_id"] = localization.id
            event["data"] = models.LocalizationInfo(**localization.__dict__)
            bg_task.add_task(WebsocketService.publish,
                             current_user.id, models.EventInfo(**event))

    logger.info(
        f"User({current_user.id}) created new Localization({localization.id}) for Project({project.id})"
    )

    loc_dict = localization.__dict__
    loc_dict["like"] = FeedbackEnum.empty

    return models.LocalizationInfo.parse_obj(loc_dict)


@router.post(
    path="/{prj_id}/localizations/{loc_id}/restart",
    tags=["Projects/Localizations"],
    description="Restart processing project's localization.",
    responses={401: {"description": "Not authenticated"}},
)
async def post_restart_localization(
    bg_task: BackgroundTasks,
    request: Request,
    body: models.LocalizationID = Depends(check_localization_ownership),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:

    event = {"created": datetime.utcnow(),
             "object": "Localization",
             "object_id": "",
             "event": "restart localization",
             "data": ""
             }

    async with db.begin():
        project_dal = ProjectDAL(db)
        localization_dal = LocalizationDAL(db)

        localization = await localization_dal.get_by_id(body.loc_id)
        project = await project_dal.get_by_id(localization.project_id)

        if localization.task_id or project.task_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Localization still in process!",
            )

        if project.status == StatusEnum.failed:
            task_id = signature(
                "process_video",
                args=(project.id, ),
            ).delay()
            project_dal.update_task_id(project.id, task_id)

            event["object_id"] = localization.id
            event["data"] = models.LocalizationInfo(**localization.__dict__)
            bg_task.add_task(WebsocketService.publish,
                             current_user.id, models.EventInfo(**event))

        elif project.status == StatusEnum.processed:
            task_id = signature(
                "process_subs",
                args=(localization.id, ),
            ).delay()
            localization_dal.update_task_id(localization.id, task_id)

            event["object_id"] = localization.id
            event["data"] = models.LocalizationInfo(**localization.__dict__)
            bg_task.add_task(WebsocketService.publish,
                             current_user.id, models.EventInfo(**event))

    logger.info(
        f"User({current_user.id}) restarted Localization({localization.id})")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Localization processing restarted successfully",
    )


@router.delete(
    path="/{prj_id}/localizations/{loc_id}",
    tags=["Projects/Localizations"],
    description="Delete project's localization.",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_delete_localization(
    request: Request,
    body: models.LocalizationID = Depends(check_localization_ownership),
    current_user: models.UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await delete_localization(db, body.loc_id)

    logger.info(f"User({current_user.id}) deleted Localization({body.loc_id})")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Localization successfully deleted",
    )


@router.post(
    path="/{prj_id}/localizations/{loc_id}/feedback",
    tags=["Projects/Localizations/Feedbacks"],
    description="Create/update feedback.",
    responses={401: {"description": "Not authenticated"}},
)
async def create_feedback(
    request: Request,
    body: models.FeedbackInfo,
    current_user: models.UserInfo = Depends(get_current_user),
    current_loc: models.LocalizationID = Depends(check_localization_ownership),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        feedback_dal = FeedbackDAL(session)
        feedback = await feedback_dal.get(email=current_user.email, loc_id=current_loc.loc_id)

        if feedback is None:
            await feedback_dal.create(
                email=current_user.email,
                loc_id=current_loc.loc_id,
                description=body.description,
                new_status=body.status
            )
        else:
            await feedback_dal.update(
                email=current_user.email,
                loc_id=current_loc.loc_id,
                new_description=body.description,
                new_status=body.status
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content="Feedback has been created/updated."
        )


@router.delete(
    path="/{prj_id}/localizations/{loc_id}/feedback",
    tags=["Projects/Localizations/Feedbacks"],
    description="Delete feedback.",
    responses={401: {"description": "Not authenticated"}},
)
async def delete_feedback(
        request: Request,
        current_user: models.UserInfo = Depends(get_current_user),
        body: models.LocalizationID = Depends(check_localization_ownership),
        session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        feedback_dal = FeedbackDAL(session)
        feedback = await feedback_dal.get(email=current_user.email, loc_id=body.loc_id)

        if feedback is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"There is no such record in the database.",
            )
        else:
            await feedback_dal.delete(email=current_user.email, loc_id=body.loc_id)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content="Feedback has been deleted."
            )


@router.get(
    path="/event_stream",
    tags=["Projects/Events"],
    description="Event stream which signals about processing.",
    responses={401: {"description": "Not authenticated"}},
)
async def event_stream(
    request: Request, current_user: models.UserInfo = Depends(get_current_user)
) -> EventSourceResponse:
    async def get_messages():
        events = []
        db = get_db()
        project_dal = ProjectDAL(db)
        localization_dal = LocalizationDAL(db)

        projects = await project_dal.get_list_by_user_id(
            current_user.id, processed=True
        )
        for project in projects:
            if project.status == StatusEnum.failed:
                events.append(
                    {
                        "object": "project",
                        "id": project.id,
                        "event": "Failed",
                        "data": "",
                    }
                )
        localizations = await localization_dal.get_list_by_user_id(
            current_user.id, processed=True
        )
        for loc in localizations:
            if loc.status == StatusEnum.failed:
                events.append(
                    {
                        "object": "localization",
                        "id": loc.id,
                        "event": "Failed",
                        "data": "",
                    }
                )
            elif loc.status == StatusEnum.processed:
                events.append(
                    {
                        "object": "localization",
                        "id": loc.id,
                        "event": "Finished",
                        "data": ProjectFiles(project.id).get_file_link(loc.result_name),
                    }
                )
        return events

    async def event_generator():
        while True:
            if await request.is_disconnected():
                logger.debug("Request disconnected")
                break

            # Checks for new messages and return them to client if any
            events = await get_messages()
            for event in events:
                yield event

            await asyncio.sleep(Config.MESSAGE_STREAM_DELAY)

    return EventSourceResponse(event_generator())


@router.post(
    path="/centrifugo",
    tags=["Centrifugo"],
    description="Get a websockets access token.",
)
async def get_token_websockets(current_user: models.UserInfo = Depends(get_current_user)) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_200_OK, content=get_cent_token(current_user.id))
