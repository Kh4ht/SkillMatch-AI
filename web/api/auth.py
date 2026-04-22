# region IMPORTS

# Standard library imports
import re
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
    """Display Registration Form"""

    return render_template("register.html")


@auth_bp.route("/register", methods=["POST"])
def register_submit():
    """Process Registration Form Submission"""

    user_name = request.form.get("user_name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    company_name = request.form.get("company_name")

    # Validate Requests
    if (
        user_name is None
        or email is None
        or password is None
        or confirm_password is None
        or company_name is None
    ):
        raise ValueError("A Request Field Is NONE")

    success, msg = User.create_new_user(
        user_name=user_name,
        email=email,
        password=password,
        confirm_password=confirm_password,
        company_name=company_name,
    )

    if success:
        flash(
            f"Congratulations For Created Your Account {user_name}! Please login.",
            "success",
        )
        return redirect(url_for("auth.login_page"))
    else:
        flash(msg, "error")
        return render_template(
            "register.html", user_name=user_name, email=email, company_name=company_name
        )


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
    password = request.form.get("password")
    # If Checkbox Is Not Checked It Will Be None
    remember_me_value = request.form.get("remember_me_value")

    if email_or_username is None or password is None:
        raise ValueError("A Request Field Is NONE")

    email_or_username.strip()
    remember_me = remember_me_value == "on"

    user, error_message = User.authenticate_user(email_or_username, password)

    if user:
        # Create Flask-Login user object
        login_success = login_user(
            user=user,
            remember=remember_me,
            duration=timedelta(days=30),
        )

        if login_success:
            # User authenticated successfully, update last login time
            Database.UPDATE_user_last_login(user_id=user.id)

            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Login Failed!", "error")
            return render_template("login.html", email_or_username=email_or_username)
    else:
        flash(error_message, "error")
        return render_template("login.html", email_or_username=email_or_username)


# endregion
# #####################################################################

# #####################################################################
# region LOGOUT


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("You Have Been Logged Out!", "info")
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
