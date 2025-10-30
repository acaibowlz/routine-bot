import logging
from datetime import datetime, time

import psycopg
from psycopg.types.json import Json

from routine_bot.constants import TZ_TAIPEI
from routine_bot.enums import ChatStatus
from routine_bot.models import ChatData, EventData, ShareData, UpdateData, UserData

logger = logging.getLogger(__name__)


def table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return cur.fetchone()[0] is not None


def create_users_table(cur: psycopg.Cursor) -> None:
    """
    Users Table
    -----------
    - user_id :
        Unique identifier for each user (corresponds to the LINE user ID).
    - created_at :
        Timestamp when the user record was created.
    - event_count :
        Total number of events owned by the user.
        Users on free plan can have up to 5 events.
    - notification_slot :
        The user's preferred daily notification hour (on the hour, HH:00).
        Used to determine when daily reminder jobs should be sent.
        This value represents a repeating time slot every day, not a specific date-time.
    - is_premium :
        Indicates whether the user is subscribed to a premium plan.
    - premium_until :
        Expiration timestamp of the user's premium feature access.
        Users can unsubscribe at any time, but premium access remains active until this timestamp.
        Post-expiration behavior for users with > 5 events:
        - Can view, update, edit, and delete all existing events
        - Cannot create new events until event_count <= 5 or premium is renewed
        - Will NOT receive notifications/reminders for any events while over the 5-event limit
        (notifications resume once event_count <= 5 or premium is renewed)
    - is_active :
        Indicates whether the user has blocked the bot
    """
    cur.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_count INTEGER NOT NULL DEFAULT 0,
            notification_slot TIME NOT NULL DEFAULT '00:00',
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            premium_until TIMESTAMPTZ,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )


def create_chats_table(cur: psycopg.Cursor) -> None:
    """
    Chats Table
    ------------
    - chat_id :
        Unique identifier for each chat session.
    - created_at :
        Timestamp indicating when the chat record was created.
    - user_id :
        Identifier of the user associated with the chat session.
    - chat_type :
        Specifies the purpose of the chat, i.e., which event or action is being processed.
        Refer to `ChatType` in `constants.py`.
    - current_step :
        Indicates the current processing stage within the chat workflow.
        Refer to the corresponding `*Steps` constants in `constants.py`.
        Set to NULL when the chat session is completed.
    - payload :
        JSON object containing intermediate data collected during the chat flow.
    - status :
        The current status of the chat session.
        Refer to `ChatStatus` in `constants.py`.
    """
    cur.execute(
        """
        CREATE TABLE chats (
            chat_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id TEXT NOT NULL REFERENCES users(user_id),
            chat_type TEXT NOT NULL,
            current_step TEXT,
            payload JSON,
            status TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_user_status ON chats (user_id, status)")


def create_events_table(cur: psycopg.Cursor) -> None:
    """
    Events Table
    ------------
    - event_id :
        Unique identifier for each event.
    - created_at :
        Timestamp indicating when the event record was created.
    - user_id :
        Identifier of the user who owns the event.
    - event_name :
        Name of the event.
    - reminder_enabled :
        Indicates whether reminders are enabled for the event.
    - event_cycle :
        Specifies the recurrence interval of the event (e.g., daily, weekly).
    - last_done_at :
        Timestamp of the most recent time the user completed the event.
        Event completion timestamps are stored at day-level precision,
        with the time set to 00:00 (UTC+8).
    - next_due_at :
        If the current time is later than this timestamp, the event is considered due,
        and the bot will send the reminder on its next scheduled run.
    - share_count :
        The number of users this event is shared with.
        All shared users will also receive reminder notifications.
    - is_active :
        If a user blocks the bot, the events they own are marked as inactive,
        and their associated reminders will no longer be triggered.
    """

    cur.execute(
        """
        CREATE TABLE events (
            event_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            user_id TEXT NOT NULL REFERENCES users(user_id),
            event_name TEXT NOT NULL,
            reminder_enabled BOOLEAN NOT NULL,
            event_cycle TEXT,
            last_done_at TIMESTAMPTZ NOT NULL,
            next_due_at TIMESTAMPTZ,
            share_count INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            -- Prevent duplicate event names per user
            UNIQUE (user_id, event_name)
        )
        """
    )


def create_updates_table(cur: psycopg.Cursor) -> None:
    """
    Updates Table
    --------------
    - update_id :
        Unique identifier for each update entry.
        This table records every instance in which a user updates
        the completion time of an event.
    - created_at :
        Timestamp indicating when the update entry was created.
    - event_id :
        Identifier of the event associated with this update.
    - event_name :
        Name of the event associated with this update.
    - user_id :
        Identifier of the user who owns the event.
    - done_at :
        Timestamp representing the newly updated completion time of the event.
        Event completion times are stored with day-level precision,
        with the time component normalized to 00:00 (UTC+8).
    """
    cur.execute(
        """
        CREATE TABLE updates (
            update_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            done_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def create_shares_table(cur: psycopg.Cursor) -> None:
    """
    Shares Table
    ------------
    - share_id :
        Unique identifier for each share record.
        The shared events will also send reminder notification to receipients.
    - created_at :
        Timestamp indicating when the share record was created.
    - event_id :
        Identifier of the event being shared.
    - event_name :
        Name of the event being shared.
    - owner_id :
        Identifier of the user who owns the event.
    - recipient_id :
        Identifier of the user with whom the event is shared.
    """
    cur.execute(
        """
        CREATE TABLE shares (
            share_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            owner_id TEXT NOT NULL REFERENCES users(user_id),
            recipient_id TEXT NOT NULL
        )
        """
    )


def init_db(conn: psycopg.Connection):
    table_creators = {
        "users": create_users_table,
        "chats": create_chats_table,
        "events": create_events_table,
        "updates": create_updates_table,
        "shares": create_shares_table,
    }
    with conn.cursor() as cur:
        for table, creator_func in table_creators.items():
            if table_exists(cur, table):
                continue
            creator_func(cur)
            logger.info(f"Table created: {table}")
    conn.commit()
    logger.info("Database initialized")


# -------------------------------- User Table -------------------------------- #


def add_user(user_id: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id)
            VALUES (%s)
            """,
            (user_id,),
        )
    conn.commit()
    logger.debug(f"User inserted: {user_id}")


def get_user(user_id: str, conn: psycopg.Connection) -> UserData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                user_id,
                event_count,
                notification_slot,
                is_premium,
                premium_until,
                is_active
            FROM users
            WHERE user_id = %s
            """,
            (user_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return UserData(*result)


def user_exists(user_id: str, conn: psycopg.Connection) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        return cur.fetchone() is not None


def list_active_users_by_notification_slot(time_slot: time, conn: psycopg.Connection) -> list[UserData]:
    if time_slot.minute or time_slot.second or time_slot.microsecond:
        raise ValueError(f"Not a valid time slot: {time_slot}")
    logger.info(f"Current notification slot: {time_slot.strftime('%H:%M')}")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                user_id,
                event_count,
                notification_slot,
                is_premium,
                premium_until,
                is_active
            FROM users
            WHERE notification_slot = %s
            AND is_active = TRUE
            """,
            (time_slot,),
        )
        result = cur.fetchall()
        if len(result):
            logger.info(f"{len(result)} active users found within current time slot")
        else:
            logger.info("No active user found within current time slot")
        return [UserData(*row) for row in result]


def increment_user_event_count(user_id: str, by: int, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET event_count = event_count + %s
            WHERE user_id = %s
            """,
            (by, user_id),
        )
    conn.commit()
    logger.debug(f"User event_count incremented by {by}: {user_id}")


def set_user_activeness(user_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE user_id = %s
            """,
            (to, user_id),
        )
    conn.commit()
    logger.debug(f"User is_active updated: {user_id}")


def set_user_notification_slot(user_id: str, time_slot: time, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE users
            SET notification_slot = %s
            WHERE user_id = %s
            """,
            (time_slot, user_id),
        )
    conn.commit()
    logger.debug(f"User notification_slot updated: {user_id}")


# -------------------------------- Chat Table -------------------------------- #


def add_chat(chat: ChatData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chats (chat_id, user_id, chat_type, current_step, payload, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                chat.chat_id,
                chat.user_id,
                chat.chat_type,
                chat.current_step,
                Json(chat.payload),
                chat.status,
            ),
        )
    conn.commit()
    logger.debug(f"Chat inserted: {chat.chat_id}")


def get_chat(chat_id: str, conn: psycopg.Connection) -> ChatData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id, user_id, chat_type, current_step, payload, status
            FROM chats
            WHERE chat_id = %s
            """,
            (chat_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return ChatData(*result)


def get_ongoing_chat_id(user_id: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chat_id
            FROM chats
            WHERE user_id = %s AND status = %s
            """,
            (user_id, ChatStatus.ONGOING.value),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def set_chat_current_step(chat_id: str, current_step: str | None, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET current_step = %s
            WHERE chat_id = %s
            """,
            (current_step, chat_id),
        )
    conn.commit()
    logger.debug(f"Chat current_step updated: {chat_id}")


def set_chat_payload(chat_id: str, payload: dict, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET payload = %s
            WHERE chat_id = %s
            """,
            (Json(payload), chat_id),
        )
    conn.commit()
    logger.debug(f"Chat payload updated: {chat_id}")


def set_chat_status(chat_id: str, status: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE chats
            SET status = %s
            WHERE chat_id = %s
            """,
            (status, chat_id),
        )
    conn.commit()
    logger.debug(f"Chat status updated: {chat_id}")


# -------------------------------- Event Table ------------------------------- #


def add_event(event: EventData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO events (
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event.event_id,
                event.user_id,
                event.event_name,
                event.reminder_enabled,
                event.event_cycle,
                event.last_done_at,
                event.next_due_at,
                0,
                True,
            ),
        )
    conn.commit()
    logger.debug(f"Event inserted: {event.event_id}")


def get_event(event_id: str, conn: psycopg.Connection) -> EventData | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            FROM events
            WHERE event_id = %s
            """,
            (event_id,),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return EventData(*result)


def delete_event(event_id: str, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM events
            WHERE event_id = %s
            """,
            (event_id,),
        )
    conn.commit()
    logger.debug(f"Event deleted: {event_id}")


def get_event_id(user_id: str, event_name: str, conn: psycopg.Connection) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT event_id
            FROM events
            WHERE user_id = %s AND event_name = %s
            """,
            (user_id, event_name),
        )
        result = cur.fetchone()
        if result is None:
            return None
        return result[0]


def list_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    pass


def list_overdue_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                event_id,
                user_id,
                event_name,
                reminder_enabled,
                event_cycle,
                last_done_at,
                next_due_at,
                share_count,
                is_active
            FROM events
            WHERE user_id = %s
            AND reminder_enabled = TRUE
            AND next_due_at <= NOW()
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]


def set_event_activeness(event_id: str, to: bool, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET is_active = %s
            WHERE event_id = %s
            """,
            (to, event_id),
        )
    conn.commit()
    logger.debug(f"Event is_active updated: {event_id}")


def set_event_activeness_by_user(user_id: str, to: bool, conn: psycopg.Connection):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE events
            SET is_active = %s
            WHERE user_id = %s
            """,
            (to, user_id),
        )
    conn.commit()
    logger.info(f"All events activeness set to {to}: {user_id}")


# ------------------------------- Update Table ------------------------------- #


def add_update(update: UpdateData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO updates (update_id, event_id, event_name, user_id, done_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                update.update_id,
                update.event_id,
                update.event_name,
                update.user_id,
                update.done_at,
            ),
        )
    conn.commit()
    logger.debug(f"Update inserted: {update.update_id}")


def list_event_recent_update_times(event_id: str, conn: psycopg.Connection, limit: int = 10) -> list[datetime]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT done_at
            FROM updates
            WHERE event_id = %s
            ORDER BY done_at DESC
            LIMIT %s
            """,
            (event_id, limit),
        )
        result = cur.fetchall()
        return [row[0] for row in result]


def delete_updates_by_event_id(event_id: str, conn: psycopg.Connection) -> None:
    logger.debug(f"Deleting updates by event_id: {event_id}")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT update_id
            FROM updates
            WHERE event_id = %s
            """,
            (event_id,),
        )
        update_ids = [row[0] for row in cur.fetchall()]

        cur.execute(
            """
            DELETE FROM updates
            WHERE event_id = %s
            """,
            (event_id,),
        )
    conn.commit()
    for update_id in update_ids:
        logger.debug(f"Update deleted: {update_id}")


# ------------------------------- Share Table -------------------------------- #


def add_share(share: ShareData, conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO shares (share_id, event_id, event_name, owner_id, recipient_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                share.share_id,
                share.event_id,
                share.event_name,
                share.owner_id,
                share.recipient_id,
            ),
        )
    conn.commit()
    logger.debug(f"Share inserted: {share.share_id}")


def list_shared_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    pass


def list_overdue_shared_events_by_user(user_id: str, conn: psycopg.Connection) -> list[EventData]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                e.event_id,
                e.user_id,
                e.event_name,
                e.reminder_enabled,
                e.event_cycle,
                e.last_done_at,
                e.next_due_at,
                e.share_count,
                e.is_active
            FROM events e
            WHERE e.reminder_enabled = TRUE
            AND e.next_due_at <= NOW()
            AND EXISTS (
                SELECT 1
                FROM shares s
                WHERE s.recipient_id = %s
                AND s.event_id = e.event_id
            )
            """,
            (user_id,),
        )
        result = cur.fetchall()
        return [EventData(*row) for row in result]
