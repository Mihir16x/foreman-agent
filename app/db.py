import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def connect():
    """Open a database connection. Rows come back as dicts, e.g. row["title"]."""
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)