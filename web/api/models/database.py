# region IMPORTS


# Standard library imports
import sqlite3, os
from typing import Any


# endregion
# #####################################################################

# #####################################################################
# region Database Class


class Database:
    """Database class to handle all database operations"""

    # Get database path (relative to this file)
    __db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "instance",
        "skillmatch.db",
    )

    @classmethod
    def __get_db(cls):
        """Get database connection"""
        conn = sqlite3.connect(cls.__db_path)
        conn.row_factory = sqlite3.Row  # This lets us access columns by name
        return conn

    @classmethod
    def init_db(cls):
        """Initialize database with all tables and triggers"""
        with cls.__get_db() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON;")

            # ========== CREATE TABLES ==========

            # Users table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    last_login TIMESTAMP
                )
            """
            )

            # User settings table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    theme TEXT DEFAULT 'light',
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """
            )

            # User sessions table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """
            )

            # Jobs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    job_name TEXT NOT NULL,
                    min_edu TEXT,
                    min_edu_weight INTEGER DEFAULT 1,
                    min_exp INTEGER,
                    min_exp_weight INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """
            )

            # Job skills table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_skills (
                    skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    skill_weight INTEGER DEFAULT 1,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
            """
            )

            # Candidates table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    resume_filename TEXT,
                    education TEXT,
                    skills TEXT,
                    match_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
                )
            """
            )

            # ========== CREATE TRIGGERS ==========

            # Trigger: Auto-create user settings when user is created
            conn.execute("DROP TRIGGER IF EXISTS auto_create_user_settings")
            conn.execute(
                """
                CREATE TRIGGER auto_create_user_settings
                AFTER INSERT ON users
                BEGIN
                    INSERT INTO user_settings (user_id)
                    VALUES (NEW.user_id);
                END
            """
            )

            # Trigger: Update job timestamp when job is updated
            conn.execute("DROP TRIGGER IF EXISTS update_jobs_timestamp")
            conn.execute(
                """
                CREATE TRIGGER update_jobs_timestamp 
                AFTER UPDATE ON jobs
                BEGIN
                    UPDATE jobs 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE job_id = NEW.job_id;
                END
            """
            )

            # ========== CREATE INDEXES (for performance) ==========

            # Users indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
            )

            # User sessions indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at)"
            )

            # Jobs indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON jobs(user_id)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_job_name ON jobs(job_name)"
            )

            # Job skills indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_skills_job_id ON job_skills(job_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_job_skills_name ON job_skills(skill_name)"
            )

            # Candidates indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON candidates(job_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_candidates_match_score ON candidates(match_score)"
            )

            conn.commit()
            print("✓ Database initialized successfully with all tables and triggers")

    @classmethod
    def execute_select(cls, query: str, params=()) -> list[dict[str, Any]]:
        """Execute a SELECT query and return results or an empty list if no results found."""
        with cls.__get_db() as conn:
            cursor = conn.execute(query, params)
            return [
                dict(c) for c in cursor.fetchall()
            ]  # Return results as list of dicts

    @classmethod
    def execute_select_one(cls, query: str, params=()) -> dict[str, Any] | None:
        """Execute a SELECT query and return one result or None if not found."""
        with cls.__get_db() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
            # Return first result as dict or None if no result

    @classmethod
    def execute_set(cls, query: str, params=()) -> int:
        """Execute a custom query (UPDATE/INSERT) and return number of affected rows"""
        with cls.__get_db() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount  # Return number of affected rows


# endregion

# print(Database.execute("SELECT * FROM candidates"))

"""
sqlite3 src/api/instance/skillmatch.db
.mode box
SELECT * FROM candidates;
"""

# -- Add a new column --
"""
ALTER TABLE #table_name ADD COLUMN #column_name #TYPE NOT NULL DEFAULT #value;
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
