from flask import Flask, render_template, request, redirect, url_for, flash
import os
from extractors import (
    extract_text_as_list,
    extract_text_as_str,
    EDUCATION_WORDS,
)
from database import Database
from candidate import Candidate

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


# region index


@app.route("/")
def index():
    return render_template("index.html", EDUCATION_WORDS=EDUCATION_WORDS)


# endregion
# #####################################################################

# #####################################################################
# region results


@app.route("/results")
def results():
    candidates = Database.execute_select("SELECT * FROM candidates")
    return render_template("results.html", candidates=candidates)


# endregion
# #####################################################################

# #####################################################################
# region about


@app.route("/about")
def about():
    return render_template("about.html")


# endregion
# #####################################################################

# #####################################################################
# region upload


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
# region delete_candidates


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


# region Run Flask App
if __name__ == "__main__":  # to prevent unwanted execution
    app.run(debug=True)
# endregion
