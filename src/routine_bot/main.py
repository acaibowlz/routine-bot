import logging

import psycopg
from fastapi import FastAPI

from routine_bot.constants import DATABASE_URL
from routine_bot.db.init import init_db
from routine_bot.logger import format_logger_name, setup_logging
from routine_bot.routers import router

setup_logging()

logger = logging.getLogger(format_logger_name(__name__))

with psycopg.connect(conninfo=DATABASE_URL) as conn:
    init_db(conn)

app = FastAPI()
app.include_router(router)
