import logging
import re

_SECRET_PATTERNS = [
    re.compile(r"(BOT_TOKEN\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(API_HASH\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(Authorization[:=]\s*)\S+", re.IGNORECASE),
]


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for pattern in _SECRET_PATTERNS:
            msg = pattern.sub(r"\1[REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)

    # aiogram/pyrogram/httpx бувають надто говіркі на DEBUG
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
