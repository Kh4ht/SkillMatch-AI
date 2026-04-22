# region IMPORTS


# Standard Library Imports
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_required
import os

# Local Imports
from models.database import Database
from models.candidate import Candidate
from models.user import User
from models.extractors import extract_text_as_str

# Import blueprints
from auth import auth_bp


# endregion
# #####################################################################

# #####################################################################
# region FLASK SETUP


def create_app():
    """Application factory pattern"""

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to project root (from web/api/ to SkillMatch-AI/)
    project_root = os.path.dirname(os.path.dirname(script_dir))

    # Set template and static folders
    template_dir = os.path.join(project_root, "web", "templates")
    static_dir = os.path.join(project_root, "web", "static")

    # Create Flask app only once
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )

    # Initialize database when app starts (call once)
    Database.init_db()

    app.secret_key = "dev-key-please-change-in-production"

    # Register Blueprints
    app.register_blueprint(auth_bp)

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

    user_data = Database.SELECT_user_BY_id(user_id=user_id)

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
# #####################################################################

# #####################################################################
# region PARSE RESUMES


@app.route("/parse_resumes")
@login_required
def parse_resumes_page():
    return render_template("parse_resumes.html")


# endregion
# #####################################################################

# #####################################################################
# region RESULTS


@app.route("/results")
def results():
    candidates = Database.execute_select("SELECT * FROM candidates")
    return render_template("results.html", candidates=candidates)


# endregion
# #####################################################################

# #####################################################################
# region UPLOAD


@app.route("/upload", methods=["POST"])
def upload():
    uploaded_resumes = request.files.getlist("uploaded_resumes")
    if uploaded_resumes is None:
        raise ValueError("uploaded_resumes field is missing")

    required_skills = request.form.get("skills")
    if required_skills is None:
        raise ValueError("skills field is missing")

    min_education = request.form.get("min_education")
    if min_education is None:
        raise ValueError("min_education field is missing")

    required_skills = [
        s.strip() for s in required_skills.split(",")
    ]  # list of required skills

    # Loop Through Resumes.
    for r in uploaded_resumes:
        extracted_text = extract_text_as_str(r)
        if extracted_text:
            Candidate.from_string(
                resume_text=extracted_text,
                resume_filename=r.filename or "unknown",
                required_skills=required_skills,
                min_education=min_education,
            ).add_to_database()

        else:
            # TODO: Show And Save The File That Have A Problem.
            print("error extracting text from:", r.filename)

    return redirect("/")


# endregion
# #####################################################################

# #####################################################################
# region ADD JOB SUBMIT


@app.route("/add_job", methods=["POST"])
def add_job_submit():
    job_title = request.form.get("job_title")
    required_skills = request.form.get("required_skills")
    min_education = request.form.get("min_education")

    if not job_title or not required_skills or not min_education:
        flash("All fields are required to add a job", "error")
        return redirect("/parse_resumes")

    Database.execute_set(
        "INSERT INTO jobs (title, required_skills, min_education) VALUES (?, ?, ?)",
        (job_title, required_skills, min_education),
    )
    flash(f"Job '{job_title}' added successfully!", "success")
    return redirect("/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region DELETE CANDIDATES


@app.route("/delete_candidates", methods=["POST"])
def delete_candidates():
    selected_ids = request.form.getlist("selected_candidates")

    if selected_ids:
        Database.execute_set(
            "DELETE FROM candidates WHERE id IN ({})".format(
                ",".join(["?"] * len(selected_ids))
            ),
            selected_ids,
        )
        # "DELETE FROM candidates

        flash(f"Successfully deleted {len(selected_ids)} candidate(s)", "success")
    else:
        flash("No candidates selected", "error")
    return redirect("/results")


# endregion
# #####################################################################

# #####################################################################
# region RUN APP


if __name__ == "__main__":
    app.run(debug=True)


# endregion
