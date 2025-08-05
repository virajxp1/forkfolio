from app.services.data.supabase_client import get_db_connection


class BaseManager:
    def __init__(self):
        self.db = get_db_connection()
        self.cursor = self.db.cursor()

    def close(self):
        """Close database connection"""
        if hasattr(self, "cursor") and self.cursor:
            self.cursor.close()
        if hasattr(self, "db") and self.db:
            self.db.close()
