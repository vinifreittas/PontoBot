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
    """Initializes global logging configurations safely by targeting the root logger directly."""
    numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    
    # 1. Get the root logger and set its default execution level
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 2. Define your explicit format layout
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. Safely inject your custom log_stream if it isn't there already
    if not any(isinstance(h, DequeLogHandler) for h in root_logger.handlers):
        log_stream.setFormatter(formatter)
        root_logger.addHandler(log_stream)

    # 4. Safely inject a standard console handler if missing
    if not any(type(h) is logging.StreamHandler for h in root_logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)