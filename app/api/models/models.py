# region IMPORTS


# Standard library imports
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from venv import logger
import re
import os

# Local Imports
from .database_query import UsersCol

# endregion
# #####################################################################

# #####################################################################
# region Job model


class Job:

    def __init__(
        self,
        id: int,
        user_id: int,
        job_title: str,
        min_edu: str,
        min_years_exp: int,
        skillname_skillweight_dict: dict[str, int],
        min_edu_weight: int,
        min_exp_weight: int,
    ):
        self.id = id
        self.user_id = user_id
        self.job_title = job_title
        self.min_edu = min_edu
        self.min_years_exp = min_years_exp
        self.skillname_skillweight_dict = skillname_skillweight_dict
        self.min_edu_weight = min_edu_weight
        self.min_exp_weight = min_exp_weight


# endregion
# #####################################################################

# #####################################################################
# region JobSkill model


class JobSkill:

    def __init__(self, id: int, job_id: int, name: str, weight: int):
        self.id = id
        self.job_id = job_id
        self.name = name
        self.weight = weight


# endregion
# #####################################################################

# #####################################################################
# region Candidate model


class Candidate:

    def __init__(
        self,
        id,
        job_id,
        user_id,
        name,
        email,
        phone,
        filename,
        original_filename,
        file_path,
        file_size,
        experience_years,
        match_score,
        education,
        skills,
        created_at,
    ):
        self.id = id
        self.user_id = user_id
        self.job_id = job_id
        self.name: str = name
        self.email: str = email
        self.phone: str = phone
        self.education: str = education
        self.filename: str = filename
        self.original_filename: str = original_filename
        self.file_path: str = file_path
        self.file_size: float = file_size
        self.experience_years: int = experience_years
        self.match_score: float = match_score
        self.skills: list[str] = skills
        self.created_at = created_at


# endregion
# #####################################################################

# #####################################################################
# region User(UserMixin)


class User(UserMixin):

    def __init__(self, id, username, company_name, created_at, last_login, email):
        self.id = id
        self.username = username
        self.email = email
        self.created_at = created_at
        self.last_login = last_login
        self.company_name = company_name

    # Static methods

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

        from .database import Database

        return Database.INSERT_user(
            user_name=user_name,
            email=email,
            password_hash=password_hash,
            company_name=company_name,
        )

    @staticmethod
    def authenticate_user(user_name_or_email, password):
        """Authenticate user and return user object"""

        from .database import Database

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

    # Instance methods

    def update_profile(
        self, username: str, email: str, company_name: str
    ) -> tuple[bool, str]:
        """Update username, email, and company for this user."""
        username = username.strip()
        email = email.strip()
        company_name = company_name.strip() if company_name.strip() else "unknown"

        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            return False, "Username can only contain letters, numbers, and underscores."
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return False, "Invalid email format."

        from .database import Database

        success, msg = Database.UPDATE_user_profile(
            user_id=self.id,
            username=username,
            email=email,
            company_name=company_name,
        )
        if success:
            self.username = username
            self.email = email
            self.company_name = company_name
        return success, msg

    def update_password(
        self, current_password: str, new_password: str, confirm_password: str
    ) -> tuple[bool, str]:
        """Verify current password then update to new one."""
        from .database import Database

        user_data = Database.SELECT_user(self.id)
        if not user_data:
            return False, "User not found."
        if not check_password_hash(user_data["password_hash"], current_password):
            return False, "Current password is incorrect."
        if new_password != confirm_password:
            return False, "New passwords do not match."
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters."

        new_hash = generate_password_hash(new_password)
        return Database.UPDATE_user_password(user_id=self.id, new_password_hash=new_hash)

    def delete_account(self) -> tuple[bool, str]:
        """Permanently delete this user account."""
        from .database import Database

        return Database.DELETE_user(user_id=self.id)

    def add_job(
        self,
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

        from .database import Database

        return Database.INSERT_job(
            user_id=self.id,
            job_title=job_title,
            min_edu=min_edu,
            min_years_exp=min_years_exp,
            min_edu_weight=min_edu_weight,
            min_exp_weight=min_exp_weight,
            skill_name_weight=skill_name_weight,
        )

    def get_jobs(self) -> list[Job]:

        from .database import Database

        return Database.SELECT_jobs(self.id)

    def get_job(self, job_id: int) -> Job | None:

        from .database import Database

        return Database.SELECT_job(job_id=job_id, user_id=self.id)

    def delete_job(self, job_id: int) -> tuple[bool, str]:

        from .database import Database

        return Database.DELETE_job(
            user_id=self.id,
            job_id=job_id,
        )

    def add_candidate(
        self,
        job_id: int,
        name: str,
        email: str,
        phone: str,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: float,
        education: str,
        skills: list[str],
        experience_years: int,
        match_score: float,
    ) -> tuple[bool, str]:

        from .database import Database

        return Database.INSERT_candidate(
            job_id=job_id,
            user_id=self.id,
            name=name,
            email=email,
            phone=phone,
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            education=education,
            skills=", ".join(skills),
            experience_years=experience_years,
            match_score=match_score,  # Store As Percentage
        )

    def get_candidates(self, job_id: int) -> list[Candidate]:

        from .database import Database

        return Database.SELECT_candidates(user_id=self.id, job_id=job_id)

    def get_candidate_by_id(self, candidate_id: int) -> Candidate | None:

        from .database import Database

        return Database.SELECT_candidate(candidate_id=candidate_id, user_id=self.id)

    def get_candidates_as_dicts(self, job_id: int):

        from .database import Database

        return Database.SELECT_candidates_as_dicts(
            user_id=self.id,
            job_id=job_id,
        )

    def delete_candidate(self, candidate_id: int) -> tuple[bool, str]:

        # also remove the candidate's resume file from the uploads folder
        c = self.get_candidate_by_id(candidate_id)

        if c:
            try:
                if os.path.exists(c.file_path):
                    os.remove(c.file_path)
                else:
                    logger.warning(f"Resume file not found on disk, skipping file deletion: {c.file_path}")

            except Exception as e:
                logger.error(f"Error deleting candidate resume file: {e}")
                # Log but do NOT abort — still delete the database record

        from .database import Database

        success, msg = Database.DELETE_candidate(
            user_id=self.id,
            candidate_id=candidate_id,
        )

        return success, msg


# endregion
