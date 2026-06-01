# region IMPORTS

# Standard library imports


# Local imports

# endregion
# #####################################################################

# #####################################################################
# region UsersCol


class UsersCol:
    """Column names for the users table"""

    ID = "id"
    NAME = "user_name"
    EMAIL = "email"
    PASSWORD_HASH = "password_hash"
    COMPANY_NAME = "company_name"
    CREATED_AT = "created_at"
    IS_ACTIVE = "is_active"
    LAST_LOGIN = "last_login"

    # Table Name
    TABLE_NAME = "users"

    # All columns as a list for easy iteration
    ALL_COLUMNS = [
        ID,
        NAME,
        EMAIL,
        PASSWORD_HASH,
        COMPANY_NAME,
        CREATED_AT,
        IS_ACTIVE,
        LAST_LOGIN,
    ]


# endregion
# #####################################################################

# #####################################################################
# region UserSettingsCol


class UserSettingsCol:
    """Column names for the user_settings table"""

    USER_ID = "user_id"
    THEME = "theme"

    # Table Name
    TABLE_NAME = "user_settings"

    ALL_COLUMNS = [USER_ID, THEME]


# endregion
# #####################################################################

# #####################################################################
# region JobsCol


class JobsCol:
    """Column names for the jobs table"""

    ID = "id"
    USER_ID = "user_id"
    TITLE = "title"
    DESCRIPTION = "description"
    MIN_EDU = "min_edu"
    MIN_YEARS_EXP = "min_years_exp"
    MIN_EDU_WEIGHT = "min_edu_weight"
    MIN_EXP_WEIGHT = "min_exp_weight"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Table Name
    TABLE_NAME = "jobs"

    ALL_COLUMNS = [
        ID,
        USER_ID,
        TITLE,
        DESCRIPTION,
        MIN_EDU,
        MIN_YEARS_EXP,
        MIN_EDU_WEIGHT,
        MIN_EXP_WEIGHT,
        CREATED_AT,
        UPDATED_AT,
    ]


# endregion
# #####################################################################

# #####################################################################
# region JobSkillsCol


class JobSkillsCol:
    """Column names for the job_skills table"""

    ID = "id"
    JOB_ID = "job_id"
    NAME = "name"
    WEIGHT = "weight"

    # Table Name
    TABLE_NAME = "job_skills"

    ALL_COLUMNS = [ID, JOB_ID, NAME, WEIGHT]


# endregion
# #####################################################################

# #####################################################################
# region CandidatesCol


class CandidatesCol:
    """Column names for the candidates table"""

    ID = "id"
    JOB_ID = "job_id"
    USER_ID = "user_id"
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    EDUCATION = "education"
    EXPERIENCE = "experience"
    SKILLS = "skills"
    MATCH_SCORE = "match_score"
    CREATED_AT = "created_at"
    FILENAME = "resume_filename"
    ORIGINAL_FILENAME = "original_resume_filename"
    FILE_PATH = "filepath"
    FILE_SIZE = "file_size"
    FILE_TEXT = "file_text"

    # Table Name
    TABLE_NAME = "candidates"


# endregion
