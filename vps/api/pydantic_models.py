from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, model_validator

from core.storages import ProjectFiles


# User
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    access_token: str
    token_type: str


class UserInfo(BaseModel):
    id: UUID
    email: EmailStr
    used_sso: bool
    name: str
    is_verified: bool
    status: int
    balance: int
    created: datetime
    updated: datetime
    last_email_request: Optional[datetime] = None
    total_created_prj: int
    total_created_loc: int
    total_secs_processed: int
    total_paid: int
    sub_is_active: bool
    sub_until: Optional[datetime] = None
    has_been_invited_to_castdev: bool


# Project
class ProjectID(BaseModel):
    prj_id: UUID


class ProjectInfo(BaseModel):
    id: UUID
    name: str
    source_path: str
    preview_path: str
    duration_in_sec: float
    created: datetime
    updated: datetime
    source_language_id: UUID
    status: int

    @model_validator(mode="before")
    def _transform(cls, values):
        if values is not dict:
            if not hasattr(values, "__dict__"):
                raise ValueError('Input is not a dict or don`t have __dict__ attribute')
            values = values.__dict__
        pf = ProjectFiles(values["id"])
        values["source_path"] = pf.get_file_link(values["source_name"], checks=False)
        values["preview_path"] = pf.get_file_link(values["preview_name"], checks=False)
        return values


class ProjectsList(BaseModel):
    projects: List[ProjectInfo]


class ProjectCreate(BaseModel):
    name: str
    file_url: Optional[str] = None
    source_language_id: UUID
    target_language_id: UUID
    duration_in_sec: int


# Localization
class LocalizationID(BaseModel):
    prj_id: UUID
    loc_id: UUID


class LocalizationInfo(BaseModel):
    id: UUID
    project_id: UUID
    target_language_id: UUID
    target_voice_name: str
    result_path: Optional[str] = None
    duration_in_sec: Optional[float] = None
    estimated_completion_date: datetime = None
    created: datetime
    updated: datetime
    status: int
    like: int


class LocalizationsList(BaseModel):
    localizations: List[LocalizationInfo]


class LocalizationCreate(BaseModel):
    prj_id: str
    target_language_id: UUID


# Languages
class LanguageInfo(BaseModel):
    id: UUID
    name: str
    source: bool
    target: bool


class LanguagesList(BaseModel):
    languages: List[LanguageInfo]


# Voices
class VoiceInfo(BaseModel):
    name: str


class VoicesList(BaseModel):
    voices: List[VoiceInfo]


# Subscriptions
class SubscriptionInfo(BaseModel):
    id: UUID
    duration: int
    type: int
    price_in_cents: float
    currency: str


class SubscriptionsList(BaseModel):
    subscriptions: List[SubscriptionInfo]


# Feedbacks
class FeedbackID(BaseModel):
    id: UUID


class FeedbackInfo(BaseModel):
    description: str
    status: int


# Airtable
class UserInvitationInfo(BaseModel):
    email: EmailStr
    name: str


# Share
class ShareInfo(BaseModel):
    project: ProjectInfo
    localizations: List[LocalizationInfo]


class EventInfo(BaseModel):
    created: datetime
    object: str
    object_id: UUID
    event: str
    data: BaseModel