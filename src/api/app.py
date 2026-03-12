from flask import Flask, render_template, request, redirect
import os

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

SPORTS = [
    "Basketball",
    "Soccer",
    "Table Tennis",
]
REGISTRANTS = {}


@app.route("/")
def index():
    return render_template("index.html", sports=SPORTS)


@app.route("/register", methods={"POST"})
def register():
    error = False
    em = ""
    if not request.form.get("name"):
        error = True
        em = "You Need To Enter Your Name!"
    if request.form.get("sport") not in SPORTS:
        error = True
        em += "\n\nYou Need To Enter Your Favorite Sport!"

    if error:
        return render_template("error.html", error_message=em)
    # if not request.form.get("name") or request.form.get("sport") not in SPORTS:

    REGISTRANTS[request.form.get("name")] = request.form.get("sport")
    return redirect("/registrants")


@app.route("/registrants")
def method_name():
    return render_template("registrants.html", registrants=REGISTRANTS)


if __name__ == "__main__":
    app.run(debug=True)
