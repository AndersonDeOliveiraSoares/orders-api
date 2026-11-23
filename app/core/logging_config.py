
import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                timezone.utc,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        standard_fields = set(
            logging.makeLogRecord({}).__dict__.keys()
        )

        for key, value in record.__dict__.items():
            if key not in standard_fields and key not in log_data:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            log_data,
            ensure_ascii=False,
            default=str,
        )


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    logging.basicConfig(
        level=logging.INFO,
        handlers=[handler],
        force=True,
    )

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
    ):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)
