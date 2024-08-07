import os

RESET = "\x1b[0m"
RED = "\x1b[31;20m"
BOLD_RED = "\x1b[31;1m"
GREEN = "\x1b[32;20m"
YELLOW = "\x1b[33;20m"
BLUE = "\x1b[36;20m"
GREY = "\x1b[38;20m"


def capitalize(message):
    return "\n".join(
        ((m[0].upper() if len(m) > 0 else "") + (m[1:] if len(m) > 1 else "") for m in message.split("\n"))
    )


def get_env(key):
    return os.environ.get(key, "false").lower() in ("true", "t", "1")
