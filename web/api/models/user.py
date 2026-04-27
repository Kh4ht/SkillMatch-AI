# region IMPORTS


# Standard library imports
from flask_login import UserMixin, current_user
import re
from werkzeug.security import generate_password_hash, check_password_hash


# Local imports
from .models import Job
from .database_query import UsersCol
from .database import Database


# endregion
# #####################################################################

# #####################################################################
# region User Class


class User(UserMixin):
    def __init__(self, id, username, company_name, created_at, last_login, email):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login
        self.company_name = company_name

    @staticmethod
    def create_new_user(
        user_name: str,
        email: str,
        password: str,
        confirm_password: str,
        company_name: str,
    ) -> tuple[bool, str]:
        """"""

        # Validate inputs
        user_name = user_name.strip()
        email = email.strip()
        company_name = (
            company_name.strip() if len(company_name.strip()) > 0 else "unknown"
        )

        if password != confirm_password:
            return False, "Passwords Don't Match"

        if len(user_name) < 3:
            return False, "Username Must Be At Least 3 Characters"

        if len(password) < 8:
            return False, "Password must be at least 8 characters"

        if not re.match(r"^[a-zA-Z0-9_]+$", user_name):
            return False, "Username Can Only Contain Letters, Numbers, And Underscores"

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return False, "Invalid Email Format"

        # Hash the password
        password_hash = generate_password_hash(password)

        return Database.INSERT_user(
            user_name=user_name,
            email=email,
            password_hash=password_hash,
            company_name=company_name,
        )

    @staticmethod
    def authenticate_user(user_name_or_email, password):
        """Authenticate user and return user object"""

        user_data = Database.SELECT_user_BY_username_or_email(
            user_name_or_email=user_name_or_email
        )

        # Check if user exists
        if not user_data:
            return None, "User Not Found!"

        # Check password
        if not check_password_hash(user_data["password_hash"], password):
            return None, "Incorrect Password!"

        return (
            User(
                id=user_data[UsersCol.ID],
                username=user_data[UsersCol.NAME],
                email=user_data[UsersCol.EMAIL],
                company_name=user_data[UsersCol.COMPANY_NAME],
                created_at=user_data[UsersCol.CREATED_AT],
                last_login=user_data[UsersCol.LAST_LOGIN],
            ),
            "Authenticated successfully!",
        )

    # region JOBS

    @staticmethod
    def add_job(
        user_id: int,
        job_title: str,
        min_edu: str,
        min_years_exp: int,
        min_edu_weight: int,
        min_exp_weight: int,
        skill_name_weight: dict[str, int],
    ) -> tuple[bool, str]:
        """Add a new job for the user"""

        if not skill_name_weight:
            return False, "At Least One Skill Is Required For The Job"

        return Database.INSERT_job(
            user_id=user_id,
            job_title=job_title,
            min_edu=min_edu,
            min_years_exp=min_years_exp,
            min_edu_weight=min_edu_weight,
            min_exp_weight=min_exp_weight,
            skill_name_weight=skill_name_weight,
        )

    @staticmethod
    def get_jobs() -> list[Job]:

        return Database.SELECT_jobs(current_user.id)

    # endregion


# endregion
