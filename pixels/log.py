from functools import wraps

from pixels.utils import BoundLogger

logger = BoundLogger()


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
