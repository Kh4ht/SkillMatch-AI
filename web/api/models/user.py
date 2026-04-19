# region IMPORTS


# Standard library imports
from typing import Any, Literal
from flask_login import UserMixin
import re
from werkzeug.security import generate_password_hash, check_password_hash

# Local imports
from .database import Database


# endregion
# #####################################################################

# #####################################################################
# region USER


class User(UserMixin):
    def __init__(self, id, username, created_at, last_login, email):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login

    @staticmethod
    def create_new_user(username: str, email: str, password: str) -> tuple[bool, str]:
        """Create a new user with validation and return (success, message/user_id)"""

        # Validate inputs
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters"

        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return False, "Username can only contain letters, numbers, and underscores"

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return False, "Invalid email format"

        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        # Hash the password
        password_hash = generate_password_hash(password)

        try:
            result = Database.execute_set(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            """,
                (username, email, password_hash),
            )

            # Get the last inserted user_id
            user = Database.execute_select("SELECT last_insert_rowid() as user_id")
            user_id = user[0]["user_id"]

            return True, user_id
        except Exception as e:
            if "UNIQUE" in str(e):
                return False, "Username or email already exists"
            return False, f"Error creating user: {str(e)}"

    @staticmethod
    def authenticate_user(email_or_username, password):
        """Authenticate user and return user object"""
        # Execute query and get results
        user_dict = Database.execute_select_one(
            """
            SELECT user_id, username, email, password_hash 
            FROM users 
            WHERE email = ? OR username = ?
        """,
            (email_or_username, email_or_username),
        )

        # Check if user exists
        if not user_dict:
            return None, "User not found"

        # Check password
        if not check_password_hash(user_dict["password_hash"], password):
            return None, "Invalid password"

        # User authenticated successfully, update last login time
        Database.execute_set(
            """
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        """,
            (user_dict["user_id"],),
        )

        return (
            User(
                id=user_dict["user_id"],
                username=user_dict["username"],
                email=user_dict["email"],
                created_at=user_dict["created_at"],
                last_login=user_dict["last_login"],
            ),
            "Authenticated successfully",
        )

    @staticmethod
    def is_user_registered(email_or_username: str) -> bool:
        """Check if a user with the given email or username already exists"""
        user_ID = Database.execute_select_one(
            """
            SELECT user_id FROM users 
            WHERE email = ? OR username = ?
        """,
            (email_or_username, email_or_username),
        )
        return user_ID is not None

    @staticmethod
    def get_user_by_ID(user_id: int):
        """Get user by ID and return User object"""
        # Query your database for user
        result = Database.execute_select_one(
            "SELECT user_id, username, email FROM users WHERE user_id = ?", (user_id,)
        )
        if result:
            user_data = result
            return User(
                id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                created_at=user_data["created_at"],
                last_login=user_data["last_login"],
            )
        return None

    @staticmethod
    def get_user_by_username(username: str):
        """Get user by username and return User object"""
        result = Database.execute_select_one(
            "SELECT user_id, username, email FROM users WHERE username = ?", (username,)
        )
        if result:
            user_data = result
            return User(
                id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
                created_at=user_data["created_at"],
                last_login=user_data["last_login"],
            )
        return None

    @staticmethod
    def add_new_job_for_user(
        user_id: int, job_title: str, job_skills: tuple, job_min_education: str
    ):
        """Add a new job for the user"""
        try:
            Database.execute_set(
                """
                INSERT INTO jobs (user_id, job_title, job_skills, job_min_education)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, job_title, ",".join(job_skills), job_min_education),
            )
            return True, "Job added successfully"
        except Exception as e:
            return False, f"Error adding job: {str(e)}"
