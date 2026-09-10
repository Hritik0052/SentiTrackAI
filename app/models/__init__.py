"""Import all models here so Alembic autogenerate can see them via Base.metadata."""

from app.database.base import Base
from app.models.insight import Insight
from app.models.journal_entry import JournalEntry
from app.models.refresh_token import RefreshToken
from app.models.sentiment import Sentiment
from app.models.streak_profile import StreakProfile
from app.models.subscription_plan import SubscriptionPlan
from app.models.usage_event import UsageEvent
from app.models.user import User
from app.models.user_badge import UserBadge
from app.models.user_challenge import UserChallenge
from app.models.user_subscription import UserSubscription
from app.models.weekly_summary import WeeklySummary
from app.models.xp_event import XpEvent
from app.models.xp_profile import XpProfile

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "JournalEntry",
    "Sentiment",
    "WeeklySummary",
    "Insight",
    "StreakProfile",
    "XpProfile",
    "XpEvent",
    "UserBadge",
    "UserChallenge",
    "SubscriptionPlan",
    "UserSubscription",
    "UsageEvent",
]
