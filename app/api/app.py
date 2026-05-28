# region IMPORTS


# Standard Library Imports
from flask import Flask, render_template, request
from flask_login import LoginManager
import sys
import os

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Local Imports
from .models.database import Database
from .models.models import User
from config import Config

# Import blueprints
from .auth import auth_bp
from .parse_resumes import parse_resumes_bp

# endregion
# #####################################################################

# #####################################################################
# region FLASK SETUP


def create_app():
    """Application factory pattern"""

    # Create Flask
    app = Flask(
        __name__,
        template_folder=os.path.join(Config.PROJECT_ROOT, "app", "templates"),
        static_folder=os.path.join(Config.PROJECT_ROOT, "app", "static"),
    )

    # Initialize database
    Database.init_db()
    # Initialize upload folder
    Config.init_upload_folder()

    app.secret_key = "dev-key-please-change-in-production"

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(parse_resumes_bp)

    # Configure Flask app
    app.config["UPLOAD_FOLDER"] = Config.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

    return app


# Create App
app = create_app()


# endregion
# #####################################################################

# #####################################################################
# region LOGIN SETUP


login_manager = LoginManager()
login_manager.init_app(app)
# When Login Is Required To View A Route/ Page, Will Redirect To This Login Route
login_manager.login_view = "auth.login_page"  # type: ignore

# flash() message content
login_manager.login_message = "Please Log In To Access This Page"

# flash() message category
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):

    user_data = Database.SELECT_user(user_id)

    if user_data:
        return User(
            id=user_data["id"],
            username=user_data["user_name"],
            email=user_data["email"],
            company_name=user_data["company_name"],
            created_at=user_data["created_at"],
            last_login=user_data["last_login"],
        )
    else:
        return None


# endregion
# #####################################################################

# #####################################################################
# region INDEX


@app.route("/")
def index():
    return render_template("index.html")


# endregion
