import os
from typing import get_type_hints, Union


class AppConfigError(Exception):
    pass


def _parse_bool(val: Union[str, bool]) -> bool:
    return val if type(val) == bool else val.lower() in ["true", "yes", "1"]


class AppConfig:
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    SECRET_KEY: str
    ALGORITHM: str

    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_MINUTE_PRICE_ID: str

    DUB_API_URL: str
    TRANS_API_URL: str
    SYNT_API_KEY: str
    REQUEST_STATUS_DELAY: int

    POSTGRES_URL: str
    POSTGRES_URL_ALEMBIC: str

    SQLADMIN_USER: str
    SQLADMIN_PASSWORD: str

    FILE_ROOT: str

    ACCESS_TOKEN_EXPIRE_MINUTES: float
    EMAIL_CODE_EXPIRE_MINUTES: float
    SHARE_TOKEN_EXPIRE_WEEK: int

    BROKER_URL: str
    BACKEND_URL: str

    DOMAIN_URL: str
    FILES_URL: str
    FRONTEND_URL: str
    FRONTEND_DOMAIN: str
    ORIGINS: str

    MAILCHIMP_KEY: str

    CHUNK_SIZE: int
    MESSAGE_STREAM_DELAY: int
    MIN_PROC_TIME_IN_SEC: int
    VIDEO_MAX_DURATION: int

    AIRTABLE_API_KEY: str
    AIRTABLE_TABLE_NAME: str
    AIRTABLE_BASE_ID: str

    CENTRIFUGO_TOKEN_HMAC_SECRET_KEY: str
    CENTRIFUGO_ADMIN_PASSWORD: str
    CENTRIFUGO_ADMIN_SECRET: str
    CENTRIFUGO_API_KEY: str
    CENTRIFUGO_ALLOWED_ORIGINS: str
    CENTRIFUGO_ALLOW_SUBSCRIBE_FOR_CLIENT: bool
    CENTRIFUGO_PORT: int

    DEBUG: bool

    """
    Map environment variables to class fields according to these rules:
      - Field won't be parsed unless it has a type annotation
      - Field will be skipped if not in all caps
      - Class field and environment variable name are the same
    """

    def __init__(self):
        for field in self.__annotations__:
            if not field.isupper():
                continue

            default_value = getattr(self, field, None)
            if default_value is None and os.getenv(field) is None:
                raise AppConfigError("The {} field is required".format(field))

            try:
                var_type = get_type_hints(AppConfig)[field]
                if var_type == bool:
                    value = _parse_bool(os.getenv(field, default_value))
                else:
                    value = var_type(os.getenv(field, default_value))

                self.__setattr__(field, value)
            except ValueError:
                raise AppConfigError(
                    'Unable to cast value of "{}" to type "{}" for "{}" field'.format(
                        os.getenv(field, None), var_type, field
                    )
                )

    def __repr__(self):
        return str(self.__dict__)


Config = AppConfig()