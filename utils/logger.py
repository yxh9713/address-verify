import logging
import os

from logging.handlers import TimedRotatingFileHandler

def setup_logger(name: str = 'address'):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate log lines if setup_logger is called twice
    if logger.handlers:
        return logger

    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "worker.log"),
        when="midnight", # rotates every night
        interval=1, # every 1 day
        backupCount=90,  # Keep logs for 90 days before auto-deleting
        encoding="utf-8"
    )

    # Rename archived files to match YYYYMMDD.log preference
    # Default outputs worker.log.2026-08-07; this custom suffix formats as YYYYMMDD.log
    file_handler.suffix = "%Y%m%d.log"

    # Format the log output
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Optional: Keep console output for local development debugging
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
