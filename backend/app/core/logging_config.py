
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
LOG_DIR = BACKEND_DIR / "logs"
LOG_FILE = LOG_DIR / "policy_generation.log"


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if configuration is called more than once.
    if not getattr(root_logger, "_policy_logging_configured", False):
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger._policy_logging_configured = True

    logging.getLogger(__name__).info(
        "Logging configured | file=%s", LOG_FILE
    )
