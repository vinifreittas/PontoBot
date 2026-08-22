import logging
import os
from collections import deque
from collections.abc import Callable

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


class DequeLogHandler(logging.Handler):
    """Memory log handler tracking recent logs and error callbacks."""

    def __init__(self, maxlen: int = 500):
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=maxlen)
        self.on_error_callback: Callable[[], None] | None = None

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(self.format(record))
        if self.on_error_callback and record.levelno >= logging.ERROR:
            self.on_error_callback()

    def get_recent_lines(self, count: int | None = 12) -> str:
        """Returns recent log lines in chronological order (or all if count is None)."""
        lines = list(self.buffer)[-count:] if count else list(self.buffer)
        return "\n".join(lines) or "No logs recorded yet."


# Global instance
log_stream = DequeLogHandler(maxlen=500)


def setup_logging() -> None:
    """Configures the root logger with stream and console handlers safely."""
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    log_stream.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    if not root.handlers:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
        root.addHandler(log_stream)
