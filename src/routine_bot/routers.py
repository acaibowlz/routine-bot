import logging
import time
from datetime import datetime

import psycopg
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi, PushMessageRequest

import routine_bot.db.users as user_db
import routine_bot.messages as msg
from routine_bot.constants import DATABASE_URL, ENV, SENDER_TOKEN, TZ_TAIPEI
from routine_bot.handlers.main import configuration, handler
from routine_bot.handlers.reminder import send_reminders_for_shared_events, send_reminders_for_user_owned_events
from routine_bot.utils import format_logger_name

logger = logging.getLogger(format_logger_name(__name__))

router = APIRouter()


@router.post("/webhook")
async def webhook(request: Request):
    """
    The endpoint for LINE bot.
    """
    signature = request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Line-Signature header not found",
        )

    body = await request.body()

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature. Please check your channel secret and access token.",
        )
    except Exception as e:
        if ENV == "develop":
            logger.error(e, exc_info=True)
        else:
            logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    return Response(status_code=status.HTTP_200_OK)


@router.post("/reminder/send")
async def send_reminder(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = auth_header.split(" ")[1]
    if token != SENDER_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    logger.info("Starting the reminder sending process")
    start_time = time.perf_counter()
    execution_start = datetime.now(TZ_TAIPEI)
    try:
        with (
            psycopg.connect(conninfo=DATABASE_URL) as conn,
            ApiClient(configuration) as api_client,
        ):
            line_bot_api = MessagingApi(api_client)
            time_slot = datetime.now(TZ_TAIPEI).replace(minute=0, second=0, microsecond=0).time()
            logger.info(f"Current time slot: {time_slot}")
            users = user_db.list_active_users_by_time_slot(time_slot, conn)
            logger.info(f"Users found in this time slot: {len(users)}")
            limited_users = 0
            user_owned_events = 0
            shared_events = 0
            for user in users:
                logger.info(f"Processing for user: {user.user_id}")
                if user.is_limited:
                    limited_users += 1
                    logger.info("Failed to send reminders: User has exceeded free plan max event count")
                    error_msg = msg.error.reminder_disabled()
                    line_bot_api.push_message(PushMessageRequest(to=user.user_id, messages=[error_msg]))
                    continue
                user_owned_events += send_reminders_for_user_owned_events(user.user_id, line_bot_api, conn)
                shared_events += send_reminders_for_shared_events(user.user_id, line_bot_api, conn)
                logger.info(f"Process completed for user: {user.user_id}")
        processed_users = len(users) - limited_users
        elapsed_time = time.perf_counter() - start_time
        logger.info("Reminder sending process completed")
        logger.info("┌── Sender Summary ─────────────────────────")
        logger.info(f"│ Time Slot: {time_slot}")
        logger.info(f"│ Execution Start: {execution_start}")
        logger.info(f"│ All Users: {len(users)}")
        logger.info(f"│ Processed Users: {processed_users}")
        logger.info(f"│ Limited Users: {limited_users}")
        logger.info(f"│ All Events Sent: {user_owned_events + shared_events}")
        logger.info(f"│ User Owned Events: {user_owned_events}")
        logger.info(f"│ Shared Events: {shared_events}")
        logger.info(f"│ Elapsed Time: {round(elapsed_time)} sec")
        logger.info("└───────────────────────────────────────────")

    except Exception as e:
        if ENV == "develop":
            logger.error(f"An error occurred during the reminder sending process: {e}", exc_info=True)
        else:
            logger.error(f"An error occurred during the reminder sending process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )

    return Response(
        content=str(
            {
                "status": "success",
                "execution_details": {
                    "time_slot": str(time_slot),
                    "execution_start": execution_start.isoformat(),
                    "all_users": len(users),
                    "processed_users": processed_users,
                    "limited_users": limited_users,
                    "all_events_sent": user_owned_events + shared_events,
                    "user_owned_events": user_owned_events,
                    "shared_events": shared_events,
                    "elapsed_time_sec": round(elapsed_time),
                },
            }
        ),
        media_type="application/json",
        status_code=status.HTTP_200_OK,
    )
