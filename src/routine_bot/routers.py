import logging
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
        if ENV == "develop":
            logger.error(str(e), exc_info=True)
        else:
            logger.error(str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

    return Response(status_code=status.HTTP_200_OK)


@router.post("/reminder/send")
async def send_reminder(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth_header.split(" ")[1]
    if token != SENDER_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid token")

    logger.info("Starting the reminder sending process")
    with psycopg.connect(conninfo=DATABASE_URL) as conn, ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        time_slot = datetime.now(TZ_TAIPEI).replace(minute=0, second=0, microsecond=0).time()
        logger.info(f"Current time slot: {time_slot}")
        users = user_db.list_active_users_by_notification_slot(time_slot, conn)
        logger.info(f"Number of users to process: {len(users)}")
        for user in users:
            if user.is_limited:
                logger.info(f"User {user.user_id} failed to receive reminders: reached max events allowed")
                error_msg = msg.info.reminder_disabled()
                line_bot_api.push_message(PushMessageRequest(to=user.user_id, messages=[error_msg]))
                continue
            logger.info(f"Processing for user: {user.user_id}")
            send_reminders_for_user_owned_events(user.user_id, line_bot_api, conn)
            send_reminders_for_shared_events(user.user_id, line_bot_api, conn)
            logger.info(f"Processing completed for user: {user.user_id}")
    logger.info("Reminder sending process completed")

    return Response(status_code=status.HTTP_200_OK)
