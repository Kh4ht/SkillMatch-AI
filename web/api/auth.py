# region IMPORTS

# Standard library imports
from flask_login import login_user, logout_user
from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import timedelta

# Local imports
from models.database import Database
from models.user import User
from utils.utils import request_form_get


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

    user_name = request_form_get("user_name")
    email = request_form_get("email")
    password = request_form_get("password", strip=False)
    confirm_password = request_form_get("confirm_password", strip=False)
    company_name = request_form_get("company_name")

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

    email_or_username = request_form_get("email_or_username")
    password = request_form_get("password", strip=False)
    # If Checkbox Is Not Checked It Will Be None
    remember_me_value = request.form.get("remember_me_value")

    if password is None:
        raise ValueError("A Request Field Is NONE")

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
def logout_submit():
    logout_user()
    flash("You Have Been Logged Out!", "info")
    return redirect(url_for("index"))


# endregion
# #####################################################################

# #####################################################################
# region PROFILE


@auth_bp.route("/profile")
def profile_page():
    return render_template("profile.html")


# endregion
# #####################################################################

# #####################################################################
# region SETTINGS


@auth_bp.route("/settings")
def settings_page():
    return render_template("settings.html")


# endregion
