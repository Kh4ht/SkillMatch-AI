import secrets
from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from .database import Database
from datetime import datetime, timedelta
import re

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


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
        result = Database.execute_select_one(
            """
            SELECT user_id, username, email, created_at, last_login, is_active
            FROM users 
            WHERE user_id = ?
        """,
            (user_id,),
        )

        return result


# region register


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username")
    if username is None:
        raise ValueError("username field is missing")

    email = request.form.get("email")
    if email is None:
        raise ValueError("email field is missing")

    password = request.form.get("password")
    if password is None:
        raise ValueError("password field is missing")

    confirm_password = request.form.get("confirm_password")
    if confirm_password is None:
        raise ValueError("confirm_password field is missing")

    if password != confirm_password:
        flash("Passwords don't match", "error")
        return render_template("register.html", username=username, email=email)

    username = username.strip()
    email = email.strip()

    success, result = UserAuth.create_new_user(username, email, password)

    if success:
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login"))
    else:
        flash(result, "error")
        return render_template("register.html", username=username, email=email)


# endregion
# #####################################################################

# #####################################################################
# region login


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email_or_username = request.form.get("email_or_username", "").strip()
    password = request.form.get("password")
    remember_me = request.form.get("remember_me") == "on"

    user, error_message = UserAuth.authenticate_user(email_or_username, password)

    if user:
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]

        if remember_me:
            session.permanent = True
            from flask import current_app

            current_app.permanent_session_lifetime = timedelta(days=30)

        flash(f"Welcome back, {user['username']}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))
    else:
        flash(error_message, "error")
        return render_template("login.html")


# endregion
# #####################################################################

# #####################################################################
# region profile


@auth_bp.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Please login to view your profile", "warning")
        return redirect(url_for("auth.login"))

    user = UserAuth.get_user_by_id(session["user_id"])

    if not user:
        flash("User not found", "error")
        return redirect(url_for("auth.login"))

    return render_template("profile.html", user=user)


# endregion
# #####################################################################

# #####################################################################
# region settings


@auth_bp.route("/settings")
def settings():
    return render_template("settings.html")


# endregion
# #####################################################################

# #####################################################################
# region logout


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for("index"))


# endregion
# #####################################################################

# #####################################################################
# region create_session


# Optional: Add session management
@auth_bp.route("/create_session", methods=["POST"])
def create_session():
    """Create a user session (for remember me functionality)"""
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(days=30)

    Database.execute_set(
        """
        INSERT INTO user_sessions (session_id, user_id, expires_at)
        VALUES (?, ?, ?)
    """,
        (session_id, session["user_id"], expires_at),
    )

    return {"session_id": session_id}


# endregion
# #####################################################################

# #####################################################################
# region validate_session


@auth_bp.route("/validate_session", methods=["POST"])
def validate_session():
    """Validate a session token"""
    data = request.get_json()
    session_id = data.get("session_id")

    if not session_id:
        return {"valid": False}, 400

    results = Database.execute_select(
        """
        SELECT user_id FROM user_sessions 
        WHERE session_id = ? AND expires_at > CURRENT_TIMESTAMP
    """,
        (session_id,),
    )

    if results:
        return {"valid": True, "user_id": results[0]["user_id"]}
    return {"valid": False}


# endregion
