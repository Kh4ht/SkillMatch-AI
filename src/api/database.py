import sqlite3, os


class Database:
    """Database class to handle all database operations"""

    # Get database path (relative to this file)
    __db_path = os.path.join(os.path.dirname(__file__), "instance", "skillmatch.db")

    @classmethod
    def __get_db(cls):
        """Get database connection"""
        conn = sqlite3.connect(cls.__db_path)
        conn.row_factory = sqlite3.Row  # This lets us access columns by name
        return conn

    # @classmethod
    # def init_db(cls):
    #     """Create tables if they don't exist"""
    #     with cls.__get_db() as conn:  # "with" statement ensures connection is closed after use
    #         # candidates table
    #         conn.execute(
    #             """
    #             CREATE TABLE IF NOT EXISTS candidates (
    #                 id INTEGER PRIMARY KEY AUTOINCREMENT,
    #                 name TEXT,
    #                 email TEXT UNIQUE,
    #                 phone TEXT,
    #                 resume_filename TEXT
    #             )
    #             """
    #         )
    #         conn.commit()

    @classmethod
    def execute(cls, query: str, params=()):
        """Execute a custom query and return results if it's a SELECT, otherwise return number affected rows"""
        with cls.__get_db() as conn:
            cursor = conn.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                return [
                    dict(c) for c in cursor.fetchall()
                ]  # Return results as list of dicts
            else:
                conn.commit()
                return cursor.rowcount  # Return number of affected rows


# if Database.add_candidate("Jamie bong", "jamiebt@gmial.com", "0612340971", "jamie.pdf"):
#     print("Candidate added successfully.")
# else:
#     print("Failed to add candidate. Email may already exist.")
