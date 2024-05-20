from enum import IntEnum, Enum


class StatusEnum(IntEnum):
    created = 1
    processing = 2
    processed = 3
    deleted = 4
    failed = 5


class SubscriptionTypeEnum(IntEnum):
    Unlimited = 1
    Lower_price = 2


class FeedbackEnum(IntEnum):
    like = 1
    dislike = 2
    empty = 3


class StatEventTypeEnum(Enum):
    bought_minutes = "Bought minutes"
    login = "Login"