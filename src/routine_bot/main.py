import logging
from datetime import datetime

import psycopg
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi, PushMessageRequest

import routine_bot.db as db
import routine_bot.messages as msg
from routine_bot.constants import DATABASE_URL, LOGGING_CONFIG, REMINDER_TOKEN, TZ_TAIPEI
from routine_bot.handlers import configuration, get_user_profile, handler

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

with psycopg.connect(conninfo=DATABASE_URL) as conn:
    db.init_db(conn)

app = FastAPI()


@app.post("/webhook")
async def webhook(request: Request):
    """
    The entry point of out LINE bot.
    """
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Line-Signature header not found")

    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature. Please check your channel secret and access token.",
        )
    except Exception as e:
        logger.error(str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

    return Response(status_code=status.HTTP_200_OK)


def send_reminders_for_user_owned_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> None:
    events = db.list_overdue_events_by_user(user_id, conn)
    if len(events):
        logger.info(f"{len(events)} overdue events found")
    else:
        logger.info("No overdue event found")
    for event in events:
        push_msg = msg.Reminder.user_owned_event(event)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Notification sent: {event.event_id}")


def send_reminders_for_shared_events(user_id: str, line_bot_api: MessagingApi, conn: psycopg.Connection) -> None:
    events = db.list_overdue_shared_events_by_user(user_id, conn)
    if len(events):
        logger.info(f"{len(events)} overdue shared events found")
    else:
        logger.info("No overdue shared event found")
    for event in events:
        owner_profile = get_user_profile(event.user_id)
        push_msg = msg.Reminder.shared_event(event, owner_profile)
        line_bot_api.push_message(PushMessageRequest(to=user_id, messages=[push_msg]))
        logger.info(f"Notification sent: {event.event_id}")


@app.post("/reminder/run")
async def run_reminder(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ")[1]
    if token != REMINDER_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    logger.info("Starting the reminder process")
    with psycopg.connect(conninfo=DATABASE_URL) as conn, ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        time_slot = datetime.now(TZ_TAIPEI).replace(minute=0, second=0, microsecond=0).time()
        users = db.list_active_users_by_notification_slot(time_slot, conn)
        for user in users:
            if user.is_limited:
                logger.info("Failed to send reminders: reached max events allowed")
                error_msg = msg.Error.reminder_disabled()
                line_bot_api.push_message(PushMessageRequest(to=user.user_id, messages=[error_msg]))
                continue
            logger.info(f"Sending reminders for user: {user.user_id}")
            send_reminders_for_user_owned_events(user.user_id, line_bot_api, conn)
            send_reminders_for_shared_events(user.user_id, line_bot_api, conn)
            logger.info(f"Finished sending reminders for user: {user.user_id}")
    logger.info("Reminder process completed")

    return Response(status_code=status.HTTP_200_OK)
