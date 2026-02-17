from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import sqlite3
import logging

logger = logging.getLogger("QLM.Database")

# Define retry strategy for DB locks
db_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.1, min=0.1, max=2.0),
    retry=retry_if_exception_type(sqlite3.OperationalError),
    reraise=True
)
