import logging
import sys
from logging.handlers import QueueHandler, QueueListener
from queue import Queue

def setup_logging(level=logging.INFO):
    log_queue = Queue(-1)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(filename)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    queue_handler = QueueHandler(log_queue)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(queue_handler)

    listener = QueueListener(log_queue, handler)
    listener.start()
    return listener

# #TODO:
# import logging
# import sys
# import contextvars
# from logging.handlers import QueueHandler, QueueListener
# from queue import Queue

# # Context variable to track current sheet name
# sheet_name_var = contextvars.ContextVar("sheet_name", default="GLOBAL")

# # Custom Formatter that safely adds sheet_name if missing
# class SafeFormatter(logging.Formatter):
#     def format(self, record):
#         if not hasattr(record, "sheet_name"):
#             record.sheet_name = sheet_name_var.get()
#         return super().format(record)

# # Custom Filter that injects current sheet name from context
# class SheetContextFilter(logging.Filter):
#     def filter(self, record):
#         record.sheet_name = sheet_name_var.get()
#         return True

# # Setup function to initialize logging
# def setup_logging(level=logging.INFO):
#     log_queue = Queue(-1)
#     handler = logging.StreamHandler(sys.stdout)
#     formatter = SafeFormatter(
#         '[%(asctime)s] [%(levelname)s] [%(sheet_name)s] [%(filename)s] %(message)s',
#         datefmt='%Y-%m-%d %H:%M:%S'
#     )
#     handler.setFormatter(formatter)

#     queue_handler = QueueHandler(log_queue)
#     root_logger = logging.getLogger()
#     root_logger.setLevel(level)
#     root_logger.addHandler(queue_handler)
#     root_logger.addFilter(SheetContextFilter())

#     listener = QueueListener(log_queue, handler)
#     listener.start()
#     return listener
