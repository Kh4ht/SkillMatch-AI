# region IMPORTS


# Standard Library Imports
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager
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


# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Go up one level to project root (from web/api/ to SkillMatch-AI/)
project_root = os.path.dirname(os.path.dirname(script_dir))

# Set template and static folders
template_dir = os.path.join(project_root, "web", "templates")
static_dir = os.path.join(project_root, "web", "static")

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
)

app.secret_key = "dev-key-please-change-in-production"

# Register Blueprints
app.register_blueprint(auth_bp)


# endregion
# #####################################################################

# #####################################################################
# region LOGIN SETUP


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore # Will create this route
login_manager.login_message = "Please log in to access this page"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.get_user_by_ID(user_id)


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
# region ADD JOB


@app.route("/add_job", methods=["POST"])
def add_new_job_submit():
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


if __name__ == "__main__":  # to prevent unwanted execution
    app.run(debug=True)


# endregion
