from dataclasses import dataclass
from datetime import datetime, time

from routine_bot.constants import FREE_PLAN_MAX_EVENTS, TZ_TAIPEI


@dataclass
class UserData:
    user_id: str
    event_count: int
    notification_slot: time
    is_premium: bool
    premium_until: datetime | None
    is_active: bool

    @property
    def has_premium_access(self) -> bool:
        return self.premium_until is not None and self.premium_until > datetime.now(TZ_TAIPEI)

    @property
    def reached_free_plan_max_events(self) -> bool:
        return self.event_count > FREE_PLAN_MAX_EVENTS

    @property
    def is_limited(self) -> bool:
        return self.reached_free_plan_max_events and not self.has_premium_access


@dataclass
class ChatData:
    chat_id: str
    user_id: str
    chat_type: str
    current_step: str | None
    payload: dict[str, str]
    status: str


@dataclass
class EventData:
    event_id: str
    user_id: str
    event_name: str
    reminder_enabled: bool
    event_cycle: str | None
    last_done_at: datetime
    next_due_at: datetime | None
    share_count: int
    is_active: bool


@dataclass
class UpdateData:
    update_id: str
    event_id: str
    event_name: str
    user_id: str
    done_at: datetime


@dataclass
class ShareData:
    share_id: str
    event_id: str
    event_name: str
    owner_id: str
    recipient_id: str
