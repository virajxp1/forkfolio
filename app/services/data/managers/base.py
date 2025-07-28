from app.services.data.supabase_client import get_db_connection


class BaseManager:
    def __init__(self):
        self.db = get_db_connection()
        self.cursor = self.db.cursor()
