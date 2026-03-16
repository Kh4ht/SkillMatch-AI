from flask import Flask, render_template, request, redirect, url_for
import os
from text_extractor import extract_resume_text
from database import Database
from candidate_info_extractor import *

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


######################################################################
@app.route("/")
def index():
    return render_template("index.html")


######################################################################
@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("uploaded_resumes")

    for file in files:
        candidate = Candidate.from_string(extract_resume_text(file), file.filename)

    return redirect("/")


######################################################################
@app.route("/results")
def results():
    candidates = Database.execute("SELECT * FROM candidates")
    return render_template("results.html", candidates=candidates)


# Run Flask App
if __name__ == "__main__":
    app.run(debug=True)
