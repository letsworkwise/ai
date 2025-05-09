import multiprocessing
import os
import logging
logger = logging.getLogger(__name__)

import multiprocessing

def get_dynamic_semaphore(default_min=2, default_max=20, multiplier=2) -> int:
    """
    Dynamically decide concurrency based on CPU cores.
    :param default_min: Minimum concurrency
    :param default_max: Maximum concurrency
    :param multiplier: Multiplier per CPU core
    """
    try:
        cpu_cores = multiprocessing.cpu_count()
        suggested = min(max(default_min, int(cpu_cores * multiplier)), default_max)
        logger.info(f"Using dynamic concurrency: {suggested}")
        return suggested
    except Exception:
        logger.warning(f"Failed to get CPU cores, using default min concurrency: {default_min}")
        return default_min
