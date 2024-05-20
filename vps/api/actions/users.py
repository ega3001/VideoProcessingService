from uuid import UUID
from fastapi import Depends
from fastapi_sso.sso.google import GoogleSSO
from sqlalchemy.ext.asyncio import AsyncSession

from api import pydantic_models as models
from api.exceptions import credentials_exception, userExists_exception, incorrectCredentials_exception, incorrectAuth_exception
from api.actions.email import send_verify_email_code

from core.security import (
    create_access_token,
    create_share_token,
    create_cent_token,
    decode_access_token,
    decode_share_token,
    oauth2_scheme
)

from core.config import Config
from db.dals.users import UserDAL
from db.dals.subscriptions import SubscriptionDAL
from db.session import get_db

sso_google = GoogleSSO(
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    redirect_uri=Config.DOMAIN_URL + "users/google_callback",
)


async def create_new_user(
    body: models.UserRegister, session: AsyncSession, from_sso: bool = False
) -> str:
    async with session.begin():
        user_dal = UserDAL(session)

        exists = await user_dal.get_by_email(body.email)
        if exists is not None:
            raise userExists_exception

        user = await user_dal.create(
            name=body.name,
            email=body.email,
            password=body.password,
            verified=from_sso,
            used_sso=from_sso,
        )

    if not from_sso:
        email_token = create_access_token(
            data={"email": user.email, "aim": "verify_email"}, email=True
        )

        await send_verify_email_code(user, email_token)


async def get_current_user(
    token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_db)
) -> models.UserInfo:
    email, aim = decode_access_token(token)

    if aim != "login":
        raise credentials_exception

    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.get_by_email(email)

        if user is None:
            raise credentials_exception

        user_dict = user.__dict__
        user_sub = await SubscriptionDAL(session).get_user_sub(user.id)
        if not user_sub:
            user_dict["sub_is_active"] = False
            user_dict["sub_until"] = None
        else:
            user_dict["sub_is_active"] = user_sub.renewal_active
            user_dict["sub_until"] = user_sub.valid_until

        user_info = models.UserInfo.parse_obj(user_dict)

    return user_info


async def authenticate_by_login_password(
    session: AsyncSession, username: str, password: str
) -> bool:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.authenticate(email=username, password=password)
        if not user:
            raise incorrectCredentials_exception

        if user.used_sso:
            raise incorrectAuth_exception

    return True


def get_share_project(token: str) -> str:
    prj_id, aim = decode_share_token(token)

    if aim != "share":
        raise credentials_exception

    return prj_id


def share(prj_id: str) -> str:
    return create_share_token(data={"prj_id": prj_id, "aim": "share"})


def get_cent_token(user_id: UUID) -> str:
    return create_cent_token(data={"sub": str(user_id), "aim": "centrifugo"})
