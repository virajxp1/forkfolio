import os

import psycopg2
import psycopg2.extras


def get_db_connection():
    """Get a synchronous database connection"""
    password = os.getenv("SUPABASE_PASSWORD")
    if not password:
        raise ValueError("SUPABASE_PASSWORD environment variable is required")

    database_url = f"postgresql://postgres:{password}@db.ddrjsrzmbnovwqnstnvo.supabase.co:5432/postgres"
    return psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
