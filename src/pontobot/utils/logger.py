# utils/logger.py
from collections import deque
import logging
import os
from typing import Callable, override

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

class DequeLogHandler(logging.Handler):
    """Custom memory handler to avoid memory leaks and track errors dynamically."""
    def __init__(self, maxlen: int = 500):
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=maxlen)
        self.on_error_callback: Callable[[], None] | None = None

    @override
    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append(self.format(record))
        if self.on_error_callback and record.levelno >= logging.ERROR:
            self.on_error_callback()

    def getvalue(self) -> str:
        return "\n".join(self.buffer)

# Global instances available to the entire application
log_stream = DequeLogHandler(maxlen=500)

def setup_logging() -> None:
    """Initializes global logging configurations. Call this once at your entry point."""
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),  # Standard console output
            log_stream                # In-memory backup stream
        ]
    )