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


# print(Database.execute("SELECT * FROM candidates"))

"""
sqlite3 src/api/instance/skillmatch.db
.mode box
SELECT * FROM candidates;
"""

# -- Add a new column --
"""
ALTER TABLE #table_name ADD COLUMN #column_name #TYPE NOT NULL DEAULT #value;
"""

# -- rename table --
"""
ALTER TABLE #old_name RENAME TO #new_name;
"""

# -- delete table --
"""
DROP TABLE #table_name
"""

# -- Insert with all columns specified --
"""
INSERT INTO table_name (column1_name, column2_name, column3_name) 
VALUES (value1, value2, value3);
"""

# -- Insert without specifying columns (must provide values for ALL columns) --
"""
INSERT INTO table_name 
VALUES (value1, value2, value3);
"""

# -- List all triggers --
"""
SELECT name FROM sqlite_master WHERE type='trigger';
"""

# -- Delete a trigger if needed --
"""
DROP TRIGGER IF EXISTS auto_create_user_settings;
"""

# -- Reset auto-increment counter --
"""
DELETE FROM sqlite_sequence WHERE name='users';
"""

# -- List all tables --
"""
.tables
"""

# -- Check your SQLite version --
"""
SELECT sqlite_version();
"""
