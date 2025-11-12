import logging

import psycopg

from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))


def _table_exists(cur: psycopg.Cursor, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    result = cur.fetchone()
    assert result is not None
    return result[0] is not None


def _create_users_table(cur: psycopg.Cursor) -> None:
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
    - time_slot :
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
            time_slot TIME NOT NULL DEFAULT '00:00',
            is_premium BOOLEAN NOT NULL DEFAULT FALSE,
            premium_until TIMESTAMPTZ,
            is_active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """
    )


def _create_chats_table(cur: psycopg.Cursor) -> None:
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


def _create_events_table(cur: psycopg.Cursor) -> None:
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


def _create_records_table(cur: psycopg.Cursor) -> None:
    """
    Records Table
    --------------
    - record_id :
        Unique identifier for each completion record.
    - created_at :
        When this record entry was created.
    - event_id :
        ID of the related event.
    - event_name :
        Name of the related event.
    - user_id :
        ID of the user who owns the event.
    - done_at :
        Date the event was marked as completed (00:00 UTC+8 precision).
    """
    cur.execute(
        """
        CREATE TABLE records (
            record_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_id TEXT NOT NULL REFERENCES events(event_id),
            event_name TEXT NOT NULL,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            done_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def _create_shares_table(cur: psycopg.Cursor) -> None:
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
        "users": _create_users_table,
        "chats": _create_chats_table,
        "events": _create_events_table,
        "records": _create_records_table,
        "shares": _create_shares_table,
    }
    with conn.cursor() as cur:
        for table, creator_func in table_creators.items():
            if _table_exists(cur, table):
                continue
            creator_func(cur)
            logger.info(f"Creating table: {table}")
