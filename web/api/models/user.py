# region IMPORTS


# Standard library imports
from flask_login import UserMixin

# Local imports
from .database import Database


# endregion
# #####################################################################

# #####################################################################
# region User Model


class User(UserMixin):
    def __init__(self, id, username, email=None):
        self.id = id
        self.username = username
        self.email = email

    @staticmethod
    def get_user_by_ID(user_id):
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
            )
        return None

    @staticmethod
    def get_user_by_username(username):
        result = Database.execute_select_one(
            "SELECT user_id, username, email FROM users WHERE username = ?", (username,)
        )
        if result:
            user_data = result
            return User(
                id=user_data["user_id"],
                username=user_data["username"],
                email=user_data["email"],
            )
        return None
