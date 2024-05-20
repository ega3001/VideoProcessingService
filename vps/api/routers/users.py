import logging
import datetime

from fastapi import APIRouter, Depends, Request, Body, BackgroundTasks, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from api import pydantic_models as models
from api.services import CastdevService
from api.actions.projects import delete_user_projects
from api.actions.email import send_verify_email_code, send_reset_password_code
from api.actions.users import (
    create_new_user,
    sso_google,
    get_current_user,
    authenticate_by_login_password,
)
from core.security import create_access_token, decode_access_token
from core.config import Config
from core.status import StatEventTypeEnum
from db.dals.promocodes import PromocodesDAL
from db.dals.users import UserDAL
from db.dals.statistics import StatsDAL
from db.session import get_db

router = APIRouter()

logger = logging.getLogger("routers")


@router.post(
    path="/signup",
    tags=["Authorisation / Registration"],
    description="User registration via email and password.",
)
async def create_user(
    request: Request,
    body: models.UserRegister,
    session: AsyncSession = Depends(get_db),
) -> models.UserLogin:
    await create_new_user(body, session)

    logger.info(f"User with email {body.email} registered")
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=f"Successful registration"
    )


@router.get(
    path="/login_google",
    tags=["Authorisation / Registration"],
    description="Signup / login via Google SSO.",
)
async def login_google():
    return await sso_google.get_login_redirect(
        params={"prompt": "consent", "access_type": "offline"}
    )


@router.get(
    path="/google_callback",
    tags=["Authorisation / Registration"],
    description="Callback for Google SSO.",
)
async def google_auth_callback(
    request: Request, session: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    google_data = await sso_google.verify_and_process(request)

    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(google_data.email)

    if user is None:
        await create_new_user(
            models.UserRegister(
                name=google_data.display_name,
                email=google_data.email,
                password=google_data.id,
            ),
            session,
            from_sso=True,
        )
        logger.info(f"User with email {google_data.email} registered")

    async with session.begin():
        await StatsDAL(session).create(
            user.id,
            StatEventTypeEnum.login,
            {"from": "google SSO"}
        )

    access_token = create_access_token(
        data={"email": google_data.email, "aim": "login"}
    )

    # todo: check profile url
    redirect_r = RedirectResponse(
        url=Config.FRONTEND_URL + "workspace",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )

    redirect_r.set_cookie(
        samesite=None,
        key="access_token", 
        value=access_token, 
        domain=Config.FRONTEND_DOMAIN, 
        expires=(datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)).strftime("%a, %d %b %Y %H:%M:%S GMT"),
    )

    return redirect_r


@router.post(
    path="/login",
    tags=["Authorisation / Registration"],
    description="OAuth 2.0 auth via login (e-mail) and password.",
    response_model=models.UserLogin,
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> models.UserLogin:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.authenticate(email=form_data.username, password=form_data.password)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=f"Incorrect credentials"
            )
        if not user.is_verified and not Config.DEBUG:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Verify your email"
            )
        await StatsDAL(session).create(
            user.id,
            StatEventTypeEnum.login,
            {"from": "email & password"}
        )
    access_token = create_access_token(
        data={"email": form_data.username, "aim": "login"}
    )
    return models.UserLogin(access_token=access_token, token_type="bearer")


@router.post(
    path="/logout",
    tags=["Authorisation / Registration"],
    description="Logout endpoint for cleanup server side cookies.",
)
async def logout(response: Response) -> RedirectResponse:
    # redirect_r = RedirectResponse(
    #     url=Config.FRONTEND_URL + "login",
    #     status_code=status.HTTP_303_SEE_OTHER,
    # )

    response.delete_cookie("access_token")

    return response


@router.post(
    path="/logout2",
    tags=["Authorisation / Registration"],
    description="Logout endpoint for cleanup server side cookies.",
)
async def logout() -> RedirectResponse:
    # response = JSONResponse(content={"success": True}, status_code=status.HTTP_200_OK)
    response = RedirectResponse(
        url=Config.FRONTEND_URL + "sign_in",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    expires = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
    # datetime.datetime.min
    # response.delete_cookie("access_token", domain=Config.FRONTEND_DOMAIN)
    response.set_cookie(
        key="access_token2",
        value="deleted",
        path="/",
        # expires="Thu, 01 Jan 1970 00:00:00 GMT",
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        domain=Config.FRONTEND_DOMAIN,
        samesite=None
    )

    return response


@router.get(
    path="/me/",
    tags=["Authorisation / Registration"],
    description="Returns current user by JWT token.",
    response_model=models.UserInfo,
)
async def read_users_me(
    current_user: models.UserInfo = Depends(get_current_user),
) -> models.UserInfo:
    return current_user


@router.get(
    path="/me/refresh_token",
    tags=["Authorisation / Registration"],
    description="Returns new JWT token.",
    response_model=models.UserLogin,
)
async def refresh_token(
    current_user: models.UserInfo = Depends(get_current_user),
) -> models.UserLogin:
    access_token = create_access_token(
        data={"email": current_user.email, "aim": "login"}
    )
    return models.UserLogin(access_token=access_token, token_type="bearer")


@router.patch(
    path="/me/name", tags=["Change user info"], description="Change user's name."
)
async def change_name(
    new_name: str,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        user_dal = UserDAL(session)
        await user_dal.update_name(current_user.id, new_name)

    logger.info(f"User({current_user.id}) changed name")
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=f"Changed name for user {new_name}"
    )


@router.patch(
    path="/me/email", tags=["Change user info"], description="Change user's email."
)
async def change_email(
    new_email: EmailStr,
    password: str,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        user_dal = UserDAL(session)
        exists = await user_dal.get_by_email(new_email)
        if exists is not None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"User with this email exists",
            )
        res = await user_dal.authenticate(current_user.email, password)
        if not res:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content=f"Incorrect password"
            )
        await user_dal.update_email(current_user.id, new_email)

    logger.info(f"User({current_user.id}) changed email")
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=f"Changed email for user to {new_email}"
    )


@router.patch(
    path="/me/password",
    tags=["Change user info"],
    description="Change user's password.",
)
async def change_password(
    old_password: str = Body(),
    new_password: str = Body(),
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        user_dal = UserDAL(session)
        res = await user_dal.authenticate(current_user.email, old_password)
        if not res:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST, content=f"Incorrect password"
            )
        await user_dal.update_password(current_user.id, new_password)

    logger.info(f"User({current_user.id}) changed password")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Changed password for user {current_user.email}",
    )


@router.post(path="/me/promocode", tags=["Promocodes"], description="Apply promocode")
async def apply_promocode(
    promocode: str,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        promo_dal = PromocodesDAL(session)
        num_wands = await promo_dal.apply_promocode(promocode, current_user.id)

    logger.info(f"User({current_user.id}) applied promocode")
    return JSONResponse(status_code=status.HTTP_200_OK, content=f"{num_wands} wands")


@router.delete(path="/me", tags=["Change user info"], description="Delete account")
async def delete_account(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await authenticate_by_login_password(
        session, form_data.username, form_data.password
    )
    async with session.begin():
        user_dal = UserDAL(session)
        this_user = await user_dal.get_by_email(form_data.username)

    await delete_user_projects(session, this_user.id)
    async with session.begin():
        await UserDAL(session).delete(this_user.id)

    logger.info(f"User with email({form_data.username}) deleted")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Successfully deleted account {form_data.username}",
    )


@router.get(
    path="/reset/password/send",
    tags=["Email codes"],
    description="Reset password: send code to e-mail.",
)
async def send_reset_code(
    email: EmailStr, 
    session: AsyncSession = Depends(get_db)
) -> JSONResponse:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(email)
        if user is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=f"No user with email {email}",
            )
        if user.last_email_request is not None:
            last_email_delta = (
                datetime.datetime.utcnow() - user.last_email_request
            ).seconds
            if last_email_delta < 60:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=f"Wait for {60 - last_email_delta} seconds before sending email again",
                )
        await user_dal.update_last_email_request(user.id)

    token = create_access_token(
        data={"email": email, "aim": "reset_password"}, email=True
    )
    await send_reset_password_code(
        user=user, token=token
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Code for password reset has been sent to {email}",
    )


@router.post(
    path="/reset/password/confirm",
    tags=["Email codes"],
    description="Reset password: confirm sent code, change password.",
)
async def verify_reset_password(
    token: str = Body(), 
    new_password: str = Body(), 
    session: AsyncSession = Depends(get_db)
) -> JSONResponse:
    email, aim = decode_access_token(token)
    if aim != "reset_password":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"Wrong reset password code",
        )
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(email)
        if user is None:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=f"No user with email {email}",
            )
        await user_dal.update_password(user.id, new_password)

    logger.info(f"User({email}) successfully reseted password")
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=f"Password for {email} was changed"
    )


@router.get(
    path="/verify/email/send",
    tags=["Email codes"],
    description="Verify email: send code to e-mail.",
)
async def send_verify_code(
    email: EmailStr,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(email)

    if user is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=f"No user with email {email}",
        )
    if user.is_verified:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=f"User's email is already verified",
        )
    if user.last_email_request is not None:
        last_email_delta = (
            datetime.datetime.utcnow() - user.last_email_request
        ).seconds
        if last_email_delta < 60:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"Wait for {60 - last_email_delta} seconds before sending email again",
            )
    
    async with session.begin():
        user_dal = UserDAL(session)
        await user_dal.update_last_email_request(user.id)

    token = create_access_token(
        data={"email": user.email, "aim": "verify_email"}, email=True
    )
    await send_verify_email_code(
        user=user, token=token
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Token for verification has been sent to {user.email}",
    )


@router.post(
    path="/verify/email/confirm",
    tags=["Email codes"],
    description="Verify email: confirm sent code.",
)
async def confirm_verification(
    token: str = Body(), 
    session: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    email, aim = decode_access_token(token)
    if aim != "verify_email":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST, content=f"Wrong verification code"
        )
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(email)
        if not user:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"User's email is not exists",
            )
        if user.is_verified:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=f"User's email is already verified",
            )
        await user_dal.verify_email(email)
    
    logger.info(f"User({email}) successfully confirmed email")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"Successful confirmation",
    )

@router.post(
    path="/me/castdev", tags=["Change user info"], description="Invitation to castdev."
)
async def invitation_to_casdev(
    bg_task: BackgroundTasks,
    request: Request,
    body: models.UserInvitationInfo,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    if not current_user.has_been_invited_to_castdev:
        bg_task.add_task(
            CastdevService.create,
            body.name,
            body.email,
            current_user.id
        )

        async with session.begin():
            user_dal = UserDAL(session)
            await user_dal.update_status_invitation_to_castdev(current_user.id)

        logger.info(f"User({current_user.id}) used the invitation to castdev")

    return JSONResponse(
        status_code=status.HTTP_200_OK, content="The invitation has been used"
    )