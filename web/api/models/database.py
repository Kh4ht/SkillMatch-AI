# region IMPORTS


# Standard library imports
import sqlite3, os
from typing import Any

# Local imports


# endregion
# #####################################################################

# #####################################################################
# region Database Class


class Database:
    """Database Class To Handle All Database Operations"""

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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    
                    user_name TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    company_name TEXT,
                    
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
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Jobs table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT UNIQUE NOT NULL,
                    min_edu TEXT,
                    min_exp INTEGER,
                    min_edu_weight INTEGER DEFAULT 1,
                    min_exp_weight INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )

            # Job skills table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    weight INTEGER DEFAULT 1,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """
            )

            # Candidates table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT,
                    resume_filename TEXT,
                    education TEXT,
                    skills TEXT,
                    match_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
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
                    VALUES (NEW.id);
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
                    WHERE id = NEW.id;
                END
            """
            )

            # ========== CREATE INDEXES (for performance) ==========

            # Users indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(user_name)"
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)")

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

    # region USER QUERIES

    @classmethod
    def UPDATE_user_last_login(cls, user_id: int) -> bool:
        """Update the last_login timestamp for a user. Returns True if successful."""

        try:
            affected_rows_count = cls.execute_set(
                """
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (user_id,),
            )

            if affected_rows_count > 0:
                return True
            else:
                # User with this ID doesn't exist
                print(f"Warning: No user found with id {user_id}")
                return False

        except Exception as e:
            print(f"Error updating last_login for user {user_id}: {e}")
            return False

    @classmethod
    def SELECT_user_BY_username_or_email(
        cls, user_name_or_email: str
    ) -> dict[str, Any] | None:
        """Get User By Username Or Email, And Return User Data If Found"""

        return cls.execute_select_one(
            """
            SELECT *
            FROM users 
            WHERE email = ? OR user_name = ?
        """,
            (user_name_or_email, user_name_or_email),
        )

    @classmethod
    def SELECT_user_BY_id(cls, user_id: int) -> dict[str, Any] | None:
        """Get User By ID, And Return User Data If Found"""

        return cls.execute_select_one(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (user_id),
        )

    @classmethod
    def INSERT_user(
        cls,
        user_name: str,
        email: str,
        password_hash: str,
        company_name: str = "unknown",
    ) -> tuple[bool, str]:
        """Add A New User To The users Table And Returns True If Added Successfully."""
        try:
            affected_rows_count = cls.execute_set(
                """
                INSERT INTO users
                (user_name, email, password_hash, company_name)
                VALUES (?, ?, ?, ?)
                """,
                (user_name, email, password_hash, company_name),
            )

            return (
                (True, "User created successfully")
                if affected_rows_count > 0
                else (False, "Insertion Failed")
            )
        except sqlite3.IntegrityError as e:
            # Handle unique constraint violations
            error_msg = str(e)
            if "user_name" in error_msg or "users.user_name" in error_msg:
                return (
                    False,
                    f"Username '{user_name}' is already taken. Please choose a different username.",
                )
            elif "email" in error_msg or "users.email" in error_msg:
                return (
                    False,
                    f"Email '{email}' is already registered. Please use a different email address or log in.",
                )
            else:
                return False, f"Database integrity error: {error_msg}"
        except Exception as e:
            # Handle any other unexpected errors
            return False, f"An unexpected error occurred: {str(e)}"

    # endregion
    # region JOB QUERIES

    @classmethod
    def INSERT_job(
        cls, user_id, title, min_edu, min_exp, min_edu_weight=1, min_exp_weight=1
    ) -> bool:
        """Add A New Job To The jobs Table And Returns True If Added Successfully."""

        affected_rows_num = cls.execute_set(
            """
            INSERT INTO jobs
            (user_id, title, min_edu, min_exp, min_edu_weight, min_exp_weight)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, title, min_edu, min_exp, min_edu_weight, min_exp_weight),
        )
        return affected_rows_num > 0

    # endregion


# endregion


"""
sqlite3 web/instance/skillmatch.db
.mode box
SELECT * FROM users;
"""
