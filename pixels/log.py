import os
from functools import wraps
from typing import Dict, Optional

import structlog


class BoundLogger:
    def __init__(
        self, bind=None, context: Optional[Dict[str, str]] = None, log_id=None
    ):
        """
        Parameters
        ----------
            bind: ref
                The object to associate the logger with
            context: dict
                Contains a dictionary with the human names and
                the attribute names of the instance that we
                want to print in every logging message.
            log_id: str
                An ID for this logger, generated if None
        """
        self.bind = bind or self
        # Unique and fast id for the instance
        self.log_id = log_id or os.urandom(4).hex()
        self.logger = structlog.get_logger(self.log_id)

        self.context = context or {}

        if os.environ.get("AWS_BATCH_JOB_ID"):
            self.context["AWS_BATCH_JOB_ID"] = os.environ.get("AWS_BATCH_JOB_ID")
            self.context["AWS_BATCH_JOB_ATTEMPT"] = os.environ.get(
                "AWS_BATCH_JOB_ATTEMPT"
            )

    def _log_context(self):
        context = {"log_id": self.log_id}

        for name, key in self.context.items():
            context[name] = key

        return context

    def debug(self, message, **kwargs):
        self.logger.debug(message, **self._log_context(), **kwargs)

    def info(self, message, **kwargs):
        self.logger.info(message, **self._log_context(), **kwargs)

    def warning(self, message, **kwargs):
        self.logger.warning(message, **self._log_context(), **kwargs)

    def error(self, message, **kwargs):
        self.logger.error(message, **self._log_context(), **kwargs)


def log_function(func):
    """Logs the function name, bounds and arguments.

    Works in uni and multiprocessing, for multithreading,
    the logger needs to be reset on each thread.

    If we are going to log the function bounds of a function
    that will be run as a thread, we would need to reset
    the logger on a wrapper function.
    """

    @wraps(func)
    def func_logger(*args, **kwargs):
        old_function = logger.context.pop("function", None)
        logger.context["function"] = func.__name__
        logger.info("start", function_args=args, function_kwargs=kwargs)
        func_return = func(*args, **kwargs)
        logger.info("end")
        if old_function:
            logger.context["function"] = old_function
        else:
            logger.context.pop("function")
        return func_return

    return func_logger


def reset_logger():
    """Creates a new instance of the bound logger."""
    global logger
    logger = BoundLogger()


logger = BoundLogger()
