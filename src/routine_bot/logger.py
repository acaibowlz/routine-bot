import logging
import sys

from routine_bot.constants import ENV


def shorten_uuid(uuid: str, prefix_len: int = 8) -> str:
    return uuid[:prefix_len]


def format_logger_name(module_name: str) -> str:
    return module_name.split(".", maxsplit=1)[1]


class ContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        chat_id = getattr(record, "chat_id", None)
        event_id = getattr(record, "event_id", None)
        user_id = getattr(record, "user_id", None)
        share_id = getattr(record, "share_id", None)
        record_id = getattr(record, "record_id", None)

        if chat_id:
            record.msg = f"[chat:{shorten_uuid(chat_id)}] - {record.getMessage()}"
        elif event_id:
            record.msg = f"[event:{shorten_uuid(event_id)}] - {record.getMessage()}"
        elif user_id:
            record.msg = f"[user:{shorten_uuid(user_id)}] - {record.getMessage()}"
        elif share_id:
            record.msg = f"[share:{shorten_uuid(share_id)}] - {record.getMessage()}"
        elif record_id:
            record.msg = f"[record:{shorten_uuid(record_id)}] - {record.getMessage()}"
        else:
            record.msg = record.getMessage()

        return super().format(record)


def setup_logging() -> None:
    # ---- root logger ----
    root = logging.getLogger()
    root_level = logging.DEBUG if ENV == "develop" else logging.INFO
    root.setLevel(root_level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = ContextFormatter("[%(levelname)8s] %(name)s - %(message)s")
    handler.setFormatter(formatter)

    root.addHandler(handler)

    # ---- uvicorn loggers ----
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.setLevel(logging.INFO)
    uvicorn_error.handlers.clear()

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.ERROR)
    uvicorn_access.handlers.clear()


class ContextLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        for k, v in self.extra.items():
            if v is not None:
                extra[k] = v
        return msg, kwargs


def add_context(logger: logging.Logger, **context) -> logging.LoggerAdapter:
    return ContextLoggerAdapter(logger, context)


def indent(text: str, spaces: int = 2) -> str:
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())
