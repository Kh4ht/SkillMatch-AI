# region IMPORTS


# Standard library imports
import sqlite3, os
from typing import Any

# Local imports
from .models import Job, JobSkill
from .database_query import (
    JobsCol,
    UsersCol,
    JobSkillsCol,
    CandidatesCol,
    UserSettingsCol,
)


# endregion
# #####################################################################

# #####################################################################
# region Database Class


class Database:
    """Database Class To Handle All Database Operations"""

    # region SQL methods

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

            # Users table using constants
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {UsersCol.TABLE_NAME} (
                    {UsersCol.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                    {UsersCol.NAME} TEXT UNIQUE NOT NULL,
                    {UsersCol.EMAIL} TEXT UNIQUE NOT NULL,
                    {UsersCol.PASSWORD_HASH} TEXT NOT NULL,
                    {UsersCol.COMPANY_NAME} TEXT NOT NULL,
                    {UsersCol.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    {UsersCol.IS_ACTIVE} INTEGER DEFAULT 1,
                    {UsersCol.LAST_LOGIN} TIMESTAMP
                )
            """
            )

            # User settings table
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {UserSettingsCol.TABLE_NAME} (
                    {UserSettingsCol.USER_ID} INTEGER PRIMARY KEY,
                    {UserSettingsCol.THEME} TEXT DEFAULT 'light',
                    FOREIGN KEY ({UserSettingsCol.USER_ID}) REFERENCES {UsersCol.TABLE_NAME}({UsersCol.ID}) ON DELETE CASCADE
                )
            """
            )

            # Jobs table
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {JobsCol.TABLE_NAME} (
                    {JobsCol.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                    {JobsCol.USER_ID} INTEGER NOT NULL,
                    {JobsCol.TITLE} TEXT NOT NULL,
                    {JobsCol.MIN_EDU} TEXT NOT NULL,
                    {JobsCol.MIN_YEARS_EXP} INTEGER NOT NULL,
                    {JobsCol.MIN_EDU_WEIGHT} INTEGER DEFAULT 1,
                    {JobsCol.MIN_EXP_WEIGHT} INTEGER DEFAULT 1,
                    {JobsCol.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    {JobsCol.UPDATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY ({JobsCol.USER_ID}) REFERENCES {UsersCol.TABLE_NAME}({UsersCol.ID}) ON DELETE CASCADE
                )
            """
            )

            # Job skills table
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {JobSkillsCol.TABLE_NAME} (
                    {JobSkillsCol.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                    {JobSkillsCol.JOB_ID} INTEGER NOT NULL,
                    {JobSkillsCol.NAME} TEXT NOT NULL,
                    {JobSkillsCol.WEIGHT} INTEGER DEFAULT 1,
                    FOREIGN KEY ({JobSkillsCol.JOB_ID}) REFERENCES {JobsCol.TABLE_NAME}({JobsCol.ID}) ON DELETE CASCADE
                )
            """
            )

            # Candidates table
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {CandidatesCol.TABLE_NAME} (
                    {CandidatesCol.ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                    {CandidatesCol.JOB_ID} INTEGER NOT NULL,
                    {CandidatesCol.NAME} TEXT NOT NULL,
                    {CandidatesCol.EMAIL} TEXT UNIQUE NOT NULL,
                    {CandidatesCol.PHONE} TEXT,
                    {CandidatesCol.RESUME_FILENAME} TEXT,
                    {CandidatesCol.EDUCATION} TEXT,
                    {CandidatesCol.SKILLS} TEXT,
                    {CandidatesCol.MATCH_SCORE} REAL,
                    {CandidatesCol.CREATED_AT} TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY ({CandidatesCol.JOB_ID}) REFERENCES {JobsCol.TABLE_NAME}({JobsCol.ID}) ON DELETE CASCADE
                )
            """
            )

            # ========== CREATE TRIGGERS ==========

            # Trigger: Auto-create user settings when user is created
            conn.execute("DROP TRIGGER IF EXISTS auto_create_user_settings")
            conn.execute(
                f"""
                CREATE TRIGGER auto_create_user_settings
                AFTER INSERT ON {UsersCol.TABLE_NAME}
                BEGIN
                    INSERT INTO {UserSettingsCol.TABLE_NAME} ({UserSettingsCol.USER_ID})
                    VALUES (NEW.{UsersCol.ID});
                END
            """
            )

            # Trigger: Update job timestamp when job is updated
            conn.execute("DROP TRIGGER IF EXISTS update_jobs_timestamp")
            conn.execute(
                f"""
                CREATE TRIGGER update_jobs_timestamp 
                AFTER UPDATE ON {JobsCol.TABLE_NAME}
                BEGIN
                    UPDATE {JobsCol.TABLE_NAME} 
                    SET {JobsCol.UPDATED_AT} = CURRENT_TIMESTAMP 
                    WHERE {JobsCol.ID} = NEW.{JobsCol.ID};
                END
            """
            )

            # ========== CREATE INDEXES ==========

            # Users indexes
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_users_email ON {UsersCol.TABLE_NAME}({UsersCol.EMAIL})"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_users_username ON {UsersCol.TABLE_NAME}({UsersCol.NAME})"
            )

            # Jobs indexes
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_jobs_user_id ON {JobsCol.TABLE_NAME}({JobsCol.USER_ID})"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_jobs_title ON {JobsCol.TABLE_NAME}({JobsCol.TITLE})"
            )

            # Job skills indexes
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_job_skills_job_id ON {JobSkillsCol.TABLE_NAME}({JobSkillsCol.JOB_ID})"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_job_skills_name ON {JobSkillsCol.TABLE_NAME}({JobSkillsCol.NAME})"
            )

            # Candidates indexes
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_candidates_job_id ON {CandidatesCol.TABLE_NAME}({CandidatesCol.JOB_ID})"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_candidates_email ON {CandidatesCol.TABLE_NAME}({CandidatesCol.EMAIL})"
            )
            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_candidates_match_score ON {CandidatesCol.TABLE_NAME}({CandidatesCol.MATCH_SCORE})"
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
    def execute_set(cls, query: str, params=()) -> int | None:
        """Execute INSERT/UPDATE/DELETE query.

        Returns:
            - For INSERT: The last inserted row ID (cursor.lastrowid).
            - For UPDATE/DELETE: Number of affected rows (cursor.rowcount)
        """

        with cls.__get_db() as conn:
            cursor = conn.execute(query, params)
            conn.commit()

            # Check query type to determine what to return
            query_type = query.strip().upper().split()[0]

            if query_type == "INSERT":
                if cursor.lastrowid is None:
                    raise ValueError("INSERT operation failed to return a row ID")
                return cursor.lastrowid
            else:  # UPDATE, DELETE, REPLACE, etc.
                return cursor.rowcount  # Return number of affected rows

    @classmethod
    def begin_transaction(cls):
        """Start a manual transaction"""
        conn = cls.__get_db()
        conn.execute("BEGIN TRANSACTION")
        return conn

    @classmethod
    def commit_transaction(cls, conn):
        """Commit a transaction"""
        if conn:
            conn.commit()
            conn.close()

    @classmethod
    def rollback_transaction(cls, conn):
        """Rollback a transaction"""
        if conn:
            conn.rollback()
            conn.close()

    # endregion

    # region USER QUERIES

    @classmethod
    def UPDATE_user_last_login(cls, user_id: int) -> bool:
        """Update the last_login timestamp for a user. Returns True if successful."""

        try:
            affected_rows_count = cls.execute_set(
                f"""
                UPDATE {UsersCol.TABLE_NAME} 
                SET {UsersCol.LAST_LOGIN} = CURRENT_TIMESTAMP 
                WHERE {UsersCol.ID} = ?
                """,
                (user_id,),
            )

            if not affected_rows_count or affected_rows_count == 0:
                # User with this ID doesn't exist
                print(f"Warning: No user found with id {user_id}")
                return False
            else:
                return True

        except Exception as e:
            print(f"Error updating last_login for user {user_id}: {e}")
            return False

    @classmethod
    def SELECT_user_BY_username_or_email(
        cls, user_name_or_email: str
    ) -> dict[str, Any] | None:
        """Get User By Username Or Email, And Return User Data If Found"""

        return cls.execute_select_one(
            f"""
            SELECT *
            FROM {UsersCol.TABLE_NAME} 
            WHERE {UsersCol.EMAIL} = ? OR {UsersCol.NAME} = ?
            """,
            (user_name_or_email, user_name_or_email),
        )

    @classmethod
    def SELECT_user(cls, user_id: int) -> dict[str, Any] | None:
        """Get User By ID, And Return User Data If Found"""

        return cls.execute_select_one(
            f"""
            SELECT *
            FROM {UsersCol.TABLE_NAME}
            WHERE {UsersCol.ID} = ?
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
            cls.execute_set(
                f"""
                INSERT INTO {UsersCol.TABLE_NAME}
                ({UsersCol.NAME}, {UsersCol.EMAIL}, {UsersCol.PASSWORD_HASH}, {UsersCol.COMPANY_NAME})
                VALUES (?, ?, ?, ?)
                """,
                (user_name, email, password_hash, company_name),
            )

            return (True, "User Created Successfully!")

        # Handle UNIQUE Constraint Violations
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if (
                UsersCol.NAME in error_msg
                or f"{UsersCol.TABLE_NAME}.{UsersCol.NAME}" in error_msg
            ):
                return (
                    False,
                    f"{UsersCol.NAME} '{user_name}' is already taken. Please choose a different one.",
                )
            elif (
                UsersCol.EMAIL in error_msg
                or f"{UsersCol.TABLE_NAME}.{UsersCol.EMAIL}" in error_msg
            ):
                return (
                    False,
                    f"{UsersCol.EMAIL} '{email}' is already registered. Please use a different one.",
                )
            else:
                return False, f"Database Integrity Error: {error_msg}"

        except Exception as e:
            # Handle any other unexpected errors
            return False, f"An Unexpected Error Occurred: {str(e)}"

    # endregion
    # region JOB QUERIES

    @classmethod
    def INSERT_job(
        cls,
        user_id: int,
        job_title: str,
        min_edu: str,
        min_years_exp: int,
        min_edu_weight: int,
        min_exp_weight: int,
        skill_name_weight: dict[str, int],
    ) -> tuple[bool, str]:
        """Add A New Job To The jobs Table And Returns True If Added Successfully."""

        conn = None
        try:
            # Start transaction
            conn = cls.begin_transaction()
            cursor = conn.cursor()

            # Insert job
            cursor.execute(
                f"""
                INSERT INTO {JobsCol.TABLE_NAME}
                ({JobsCol.USER_ID}, {JobsCol.TITLE}, {JobsCol.MIN_EDU}, {JobsCol.MIN_YEARS_EXP}, {JobsCol.MIN_EDU_WEIGHT}, {JobsCol.MIN_EXP_WEIGHT})
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    job_title,
                    min_edu,
                    min_years_exp,
                    min_edu_weight,
                    min_exp_weight,
                ),
            )

            job_id = cursor.lastrowid
            if not job_id:
                cls.rollback_transaction(conn)
                return False, "Error Getting Job ID After Insertion"

            # Insert skills
            for skill_name, skill_weight in skill_name_weight.items():
                cursor.execute(
                    f"""
                    INSERT INTO {JobSkillsCol.TABLE_NAME}
                    ({JobSkillsCol.JOB_ID}, {JobSkillsCol.NAME}, {JobSkillsCol.WEIGHT})
                    VALUES (?, ?, ?)
                    """,
                    (job_id, skill_name, skill_weight),
                )

            # Commit all changes
            cls.commit_transaction(conn)
            return True, "Job Created Successfully!"

        except sqlite3.IntegrityError as e:
            if conn:
                cls.rollback_transaction(conn)
            error_msg = str(e)
            if JobsCol.TITLE in error_msg:
                return False, f"Title '{job_title}' Is Already Taken."
            return False, f"Database Integrity Error: {error_msg}"

        except Exception as e:
            if conn:
                cls.rollback_transaction(conn)
            return False, f"Unexpected Error: {str(e)}"

    @classmethod
    def SELECT_job_skills(cls, job_id) -> list[JobSkill]:
        data_list = cls.execute_select(
            f"""
            SELECT * FROM {JobSkillsCol.TABLE_NAME}
            WHERE {JobSkillsCol.JOB_ID} = ?
            """,
            (job_id,),
        )

        result_list: list[JobSkill] = []

        for js in data_list:
            result_list.append(
                JobSkill(
                    id=js[JobSkillsCol.ID],
                    job_id=js[JobSkillsCol.JOB_ID],
                    name=js[JobSkillsCol.NAME],
                    weight=js[JobSkillsCol.WEIGHT],
                )
            )

        return result_list

    @classmethod
    def SELECT_jobs(cls, user_id) -> list[Job]:

        jobs_data = cls.execute_select(
            f"""
            SELECT * FROM {JobsCol.TABLE_NAME}
            WHERE {JobsCol.USER_ID} = ?
            """,
            (user_id,),
        )

        result: list[Job] = []

        for job in jobs_data:

            skill_name_weight: dict[str, int] = {}

            job_skills = cls.SELECT_job_skills(job[JobsCol.ID])

            for skill in job_skills:
                skill_name_weight[skill.name] = skill.weight

            result.append(
                Job(
                    id=job[JobsCol.ID],
                    user_id=job[JobsCol.USER_ID],
                    job_title=job[JobsCol.TITLE],
                    min_edu=job[JobsCol.MIN_EDU],
                    min_years_exp=job[JobsCol.MIN_YEARS_EXP],
                    skill_name_weight=skill_name_weight,
                )
            )

        return result

    @classmethod
    def SELECT_job(cls, user_id: int, job_id: int) -> Job | None:

        job_data = cls.execute_select_one(
            f"""
            SELECT * FROM {JobsCol.TABLE_NAME}
            WHERE {JobsCol.USER_ID} = ? AND {JobsCol.ID} = ?
            """,
            (user_id, job_id),
        )

        if not job_data:
            return None

        skill_name_weight: dict[str, int] = {}

        job_skills = cls.SELECT_job_skills(job_data[JobsCol.ID])

        for skill in job_skills:
            skill_name_weight[skill.name] = skill.weight

        return Job(
            id=job_data[JobsCol.ID],
            user_id=job_data[JobsCol.USER_ID],
            job_title=job_data[JobsCol.TITLE],
            min_edu=job_data[JobsCol.MIN_EDU],
            min_years_exp=job_data[JobsCol.MIN_YEARS_EXP],
            skill_name_weight=skill_name_weight,
        )

    @classmethod
    def DELETE_job(cls, user_id: int, job_id: int) -> tuple[bool, str]:
        """Delete a job and all related data for a specific user"""
        try:
            # Delete the job
            affected_rows = cls.execute_set(
                f"DELETE FROM {JobsCol.TABLE_NAME} WHERE {JobsCol.ID} = ? AND {JobsCol.USER_ID} = ?",
                (job_id, user_id),
            )

            if affected_rows and affected_rows > 0:
                return True, "Job deleted successfully!"
            else:
                return False, "No job was deleted!"

        except Exception as e:
            return False, f"Unexpected Error While Deleting Job: {str(e)}"

    # endregion


# endregion


"""
sqlite3 web/instance/skillmatch.db
.mode box
SELECT * FROM users;
"""
