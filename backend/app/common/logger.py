import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Resolve logs relative to the backend directory.
BACKEND_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BACKEND_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = LOG_DIR / f"log_{timestamp}.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(filename)s:%(lineno)d | %(message)s"
)


def setup_logging() -> None:
    """Configure common application logging once."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if setup is called more than once.
    if not any(
        getattr(handler, "_policy_generation_handler", False)
        for handler in root_logger.handlers
    ):
        formatter = logging.Formatter(LOG_FORMAT)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler._policy_generation_handler = True
        root_logger.addHandler(console_handler)

        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            
            
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler._policy_generation_handler = True
        root_logger.addHandler(file_handler)

    # Suppress routine third-party INFO logs.
    for logger_name in (
        "azure",
        "azure.identity",
        "azure.core",
        "azure.core.pipeline.policies.http_logging_policy",
        "httpx",
        "httpcore",
        "openai",
        "urllib3",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for an application module."""
    return logging.getLogger(name)
