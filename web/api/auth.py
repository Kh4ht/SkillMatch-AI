# region IMPORTS

# Standard library imports
import secrets
from flask_login import login_user, logout_user
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timedelta

# Local imports
from models.database import Database
from models.user import User
from models.user import User


# endregion
# #####################################################################

# #####################################################################
# region SETUP Blueprint


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# endregion
# #####################################################################

# #####################################################################
# region REGISTER


@auth_bp.route("/register", methods=["GET"])
def register_page():
    """Display registration form"""
    return render_template("register.html")


@auth_bp.route("/register", methods=["POST"])
def register_submit():
    """Process registration form submission"""
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

    success, result = User.create_new_user(username, email, password)

    if success:
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("auth.login_page"))
    else:
        flash(result, "error")
        return render_template("register.html", username=username, email=email)


# endregion
# #####################################################################

# #####################################################################
# region LOGIN


@auth_bp.route("/login", methods=["GET"])
def login_page():
    """Display login form"""
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_submit():
    """Process login form submission"""
    email_or_username = request.form.get("email_or_username")
    if email_or_username is None:
        raise ValueError("email_or_username field is missing")

    password = request.form.get("password")
    if password is None:
        raise ValueError("password field is missing")

    remember_me_value = request.form.get("remember_me")
    if remember_me_value is None:
        raise ValueError("remember_me field is missing")

    email_or_username.strip()
    remember_me = remember_me_value == "on"

    user, error_message = User.authenticate_user(email_or_username, password)

    if user:
        # Create Flask-Login user object
        login_user(
            user=user,
            remember=remember_me,
            duration=timedelta(days=30),
        )
        flash(f"Welcome back, {user.username}!", "success")
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))
    else:
        flash(error_message, "error")
        return render_template("login.html")


# endregion
# #####################################################################

# #####################################################################
# region LOGOUT


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("index"))


# endregion
# #####################################################################

# #####################################################################
# region PROFILE


@auth_bp.route("/profile")
def profile():
    return render_template("profile.html")


# endregion
# #####################################################################

# #####################################################################
# region SETTINGS


@auth_bp.route("/settings")
def settings():
    return render_template("settings.html")


# endregion
# #####################################################################

# #####################################################################
# region CREATE SESSION


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
# region VALIDATE SESSION


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
