from dataclasses import dataclass, field
from datetime import datetime, time

from routine_bot.constants import FREE_PLAN_MAX_EVENTS, TZ_TAIPEI
from routine_bot.enums import ChatStatus


@dataclass
class UserData:
    user_id: str
    notification_slot: time
    event_count: int
    is_premium: bool
    premium_until: datetime | None
    is_active: bool

    @property
    def has_premium_access(self) -> bool:
        return self.premium_until and self.premium_until > datetime.now(TZ_TAIPEI)

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
    payload: dict = field(default_factory=dict)
    status: str = ChatStatus.ONGOING.value


@dataclass
class EventData:
    event_id: str
    event_name: str
    user_id: str
    last_done_at: datetime
    reminder_enabled: bool
    event_cycle: str | None = None
    next_due_at: datetime | None = None
    share_count: int = 0


@dataclass
class UpdateData:
    update_id: str
    event_id: str
    event_name: str
    user_id: str
    done_at: str


@dataclass
class ShareData:
    share_id: str
    event_id: str
    event_name: str
    owner_id: str
    recipient_id: str
