# region IMPORTS


# Standard Library Imports
import re
from typing import Any
from werkzeug.security import generate_password_hash, check_password_hash

# Local Imports
from .database import Database


# endregion
# #####################################################################

# #####################################################################
# region UserAuth Class


class UserAuth:
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
    def is_user_registered(email_or_username: str) -> bool:
        """Check if a user with the given email or username already exists"""
        result = Database.execute_select_one(
            """
            SELECT user_id FROM users 
            WHERE email = ? OR username = ?
        """,
            (email_or_username, email_or_username),
        )
        return result is not None

    @staticmethod
    def authenticate_user(
        email_or_username, password
    ) -> tuple[dict[str, Any] | None, str]:
        """Authenticate user and return user data"""
        # Execute query and get results
        user = Database.execute_select_one(
            """
            SELECT user_id, username, email, password_hash 
            FROM users 
            WHERE email = ? OR username = ?
        """,
            (email_or_username, email_or_username),
        )

        # Check if user exists
        if not user:
            return None, "User not found"

        # Check password
        if not check_password_hash(user["password_hash"], password):
            return None, "Invalid password"

        # User authenticated successfully, update last login time
        Database.execute_set(
            """
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        """,
            (user["user_id"],),
        )

        return user, "Authenticated successfully"

    @staticmethod
    def get_user_by_id(user_id) -> dict[str, Any] | None:
        """Get user by ID"""
        return Database.execute_select_one(
            """
            SELECT user_id, username, email, created_at, last_login, is_active
            FROM users 
            WHERE user_id = ?
        """,
            (user_id,),
        )


# endregion
