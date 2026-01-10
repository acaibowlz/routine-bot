import copy
import logging
import sys

from routine_bot.constants import ENV


def shorten_uuid(uuid: str, prefix_len: int = 8) -> str:
    return uuid[:prefix_len]


def format_logger_name(module_name: str) -> str:
    return module_name.split(".", maxsplit=1)[1]


class ContextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        r = copy.copy(record)
        message = r.getMessage()

        chat_id = getattr(r, "chat_id", None)
        event_id = getattr(r, "event_id", None)
        user_id = getattr(r, "user_id", None)
        share_id = getattr(r, "share_id", None)
        record_id = getattr(r, "record_id", None)

        if chat_id:
            r.msg = f"[chat:{shorten_uuid(chat_id)}] - {message}"
        elif event_id:
            r.msg = f"[event:{shorten_uuid(event_id)}] - {message}"
        elif user_id:
            r.msg = f"[user:{shorten_uuid(user_id)}] - {message}"
        elif share_id:
            r.msg = f"[share:{shorten_uuid(share_id)}] - {message}"
        elif record_id:
            r.msg = f"[record:{shorten_uuid(record_id)}] - {message}"
        else:
            r.msg = message

        r.args = ()
        return super().format(r)


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
    uvicorn_error.propagate = False
    uvicorn_error.addHandler(handler)

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.setLevel(logging.ERROR)
    uvicorn_access.handlers.clear()
    uvicorn_access.propagate = False
    uvicorn_access.addHandler(handler)


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
