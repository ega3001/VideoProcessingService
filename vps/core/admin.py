from typing import Optional

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from db.session import engine
from db.models import User, Promocode, Project, UserPromocode, Localization, Language, Subscription, UserSubscription
from core.security import create_access_token, decode_access_token
from core.config import Config


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]

        if username != Config.SQLADMIN_USER or password != Config.SQLADMIN_PASSWORD:
            return False

        access_token = create_access_token(data={"email": username, "aim": "login"})
        request.session.update({"token": access_token})

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")

        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        username, aim = decode_access_token(token)

        if username != Config.SQLADMIN_USER or aim != "login":
            return RedirectResponse(request.url_for("admin:login"), status_code=302)


authentication_backend = AdminAuth(secret_key="...")


class UserAdmin(ModelView, model=User):
    column_list = [
        User.email,
        User.is_verified,
        User.balance,
        User.created,
        User.updated,
        User.id,
        User.name,
        User.status,
        User.total_created_loc,
        User.total_secs_processed,
        User.total_paid,
        User.total_secs_processed,
    ]
    column_default_sort = (User.created, True)
    page_size = 25


class ProjectAdmin(ModelView, model=Project):
    column_list = [
        Project.id,
        Project.user_id,
        Project.task_id,
        Project.name,
        Project.source_name,
        Project.preview_name,
        Project.duration_in_sec,
        Project.created,
        Project.updated,
        Project.parsed_speech_data,
        Project.source_language_id,
        Project.status,
    ]
    column_default_sort = (Project.created, True)
    page_size = 25


class LocalizationAdmin(ModelView, model=Localization):
    column_list = [
        Localization.id,
        Localization.task_id,
        Localization.created,
        Localization.duration_in_sec,
        Localization.estimated_completion_date,
        Localization.parsed_speech_data,
        Localization.project_id,
        Localization.result_name,
        Localization.status,
        Localization.target_language_id,
        Localization.updated,
    ]
    column_default_sort = (Localization.created, True)
    page_size = 25


class LanguageAdmin(ModelView, model=Language):
    column_list = [Language.id, Language.lang_name, Language.api_name]
    column_default_sort = (Language.id, True)
    page_size = 25


class PromocodeAdmin(ModelView, model=Promocode):
    column_list = [
        Promocode.code,
        Promocode.value,
        Promocode.expiration,
        Promocode.description,
    ]
    column_default_sort = [(Promocode.expiration, True)]
    page_size = 25


class UserPromocodeAdmin(ModelView, model=UserPromocode):
    column_list = [
        UserPromocode.user_id,
        UserPromocode.promocode_id,
        UserPromocode.usage_date,
    ]
    column_default_sort = [(UserPromocode.usage_date, True)]
    page_size = 25


class SubscriptionAdmin(ModelView, model=Subscription):
    column_list = [
        Subscription.id,
        Subscription.duration,
        Subscription.type,
        Subscription.status,
        Subscription.meta,
    ]
    column_default_sort = [(Subscription.id, True)]
    page_size = 25


class UserSubscriptionAdmin(ModelView, model=UserSubscription):
    column_list = [
        UserSubscription.id,
        UserSubscription.user_id,
        UserSubscription.subscription_id,
        UserSubscription.stripe_sub_id,
        UserSubscription.renewal_active,
        UserSubscription.created,
        UserSubscription.updated,
        UserSubscription.valid_until,
    ]
    column_default_sort = [(UserSubscription.created, True)]
    page_size = 25


def init_admin(app):
    admin = Admin(app=app, engine=engine, authentication_backend=authentication_backend)
    admin.add_view(UserAdmin)
    admin.add_view(ProjectAdmin)
    admin.add_view(LocalizationAdmin)
    admin.add_view(LanguageAdmin)
    admin.add_view(PromocodeAdmin)
    admin.add_view(UserPromocodeAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(UserSubscriptionAdmin)
