import logging

import psycopg
from fastapi import FastAPI

from routine_bot.constants import DATABASE_URL, LOGGING_CONFIG
from routine_bot.db.init import init_db
from routine_bot.routers import router
from routine_bot.utils import format_logger_name

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(format_logger_name(__name__))

with psycopg.connect(conninfo=DATABASE_URL) as conn:
    init_db(conn)

app = FastAPI()
app.include_router(router)
