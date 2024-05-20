import uuid
from datetime import datetime

from sqlalchemy import Column, Boolean, String, Integer, DateTime, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB, INTERVAL
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy_utils.types.choice import ChoiceType

from core.status import StatusEnum, SubscriptionTypeEnum, FeedbackEnum, StatEventTypeEnum

Base = declarative_base()


# todo: use relationships
class User(Base):
    __tablename__ = "users"
    # main info
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    used_sso = Column(Boolean(), default=False)
    name = Column(String, nullable=False)
    is_verified = Column(Boolean(), default=False)
    status = Column(
        ChoiceType(StatusEnum, impl=Integer()),
        nullable=False,
        default=StatusEnum.created,
    )
    # balance
    balance = Column(Integer, nullable=False, default=0)
    # stats
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)
    last_email_request = Column(DateTime, nullable=True, default=None)
    total_created_prj = Column(Integer, nullable=False, default=0)
    total_created_loc = Column(Integer, nullable=False, default=0)
    total_secs_processed = Column(Integer, nullable=False, default=0)
    total_paid = Column(Integer, nullable=False, default=0)
    has_been_invited_to_castdev = Column(Boolean, default=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duration = Column(INTERVAL, nullable=False)
    type = Column(
        ChoiceType(SubscriptionTypeEnum, impl=Integer()),
        nullable=False
    )
    status = Column(
        ChoiceType(StatusEnum, impl=Integer()),
        nullable=False,
        default=StatusEnum.created,
    )
    meta = Column(JSONB, nullable=True)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    subscription_id = Column(ForeignKey("subscriptions.id"), nullable=False)
    stripe_sub_id = Column(String, nullable=False)
    renewal_active = Column(Boolean, nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=False)


class UserPromocode(Base):
    __tablename__ = "user_promocodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    promocode_id = Column(ForeignKey("promocodes.id"), nullable=False)
    usage_date = Column(DateTime, default=datetime.utcnow)


class Promocode(Base):
    __tablename__ = "promocodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(String, nullable=False)
    code = Column(Integer, nullable=False)
    expiration = Column(DateTime, nullable=False)
    value = Column(Integer, nullable=False)


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    task_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    source_name = Column(String, nullable=False)
    preview_name = Column(String, nullable=False)
    duration_in_sec = Column(Float, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)
    parsed_speech_data = Column(JSONB, nullable=True)
    source_language_id = Column(ForeignKey("languages.id"), nullable=True)
    status = Column(
        ChoiceType(StatusEnum, impl=Integer()),
        nullable=False,
        default=StatusEnum.created,
    )


class Language(Base):
    __tablename__ = "languages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lang_name = Column(String, nullable=False)
    api_name = Column(String, nullable=False)
    source = Column(Boolean, nullable=False)
    target = Column(Boolean, nullable=False)


class Localization(Base):
    __tablename__ = "localizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(ForeignKey("projects.id"), nullable=False)
    target_language_id = Column(ForeignKey("languages.id"), nullable=False)
    target_voice_name = Column(String, nullable=False)
    task_id = Column(String, nullable=True)
    result_name = Column(String, nullable=True)
    duration_in_sec = Column(Float, nullable=True)
    estimated_completion_date = Column(DateTime, nullable=True)
    parsed_speech_data = Column(JSONB, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)
    status = Column(
        ChoiceType(StatusEnum, impl=Integer()),
        nullable=False,
        default=StatusEnum.created,
    )


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    user_email = Column(ForeignKey('users.email'), primary_key=True)
    localization_id = Column(ForeignKey('localizations.id'), primary_key=True)
    description = Column(String, nullable=True)
    status = Column(
        ChoiceType(FeedbackEnum, impl=Integer()),
        nullable=False,
        default=FeedbackEnum.empty,
    )


class StatisticEvent(Base):
    __tablename__ = "statistic_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(ForeignKey('users.id'), primary_key=True)
    event_type = Column(
        ChoiceType(StatEventTypeEnum, impl=String()),
        nullable=False
    )
    meta = Column(JSONB, nullable=True)
    created = Column(DateTime, default=datetime.utcnow)
    updated = Column(DateTime, default=datetime.utcnow)