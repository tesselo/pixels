import logging
import sys

import structlog
from structlog_sentry import SentryJsonProcessor

__version__ = "0.1"

# Set standard logging config.
logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.WARNING)

# Set structlog logging config.
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        SentryJsonProcessor(level=logging.ERROR, tag_keys="__all__"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
