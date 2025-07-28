import os

import psycopg2
import psycopg2.extras

# Construct Supabase connection string using environment variables
password = os.getenv("SUPABASE_PASSWORD")
DATABASE_URL = f"postgresql://postgres:{password}@db.ddrjsrzmbnovwqnstnvo.supabase.co:5432/postgres"


def get_db_connection():
    """Get a synchronous database connection"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
