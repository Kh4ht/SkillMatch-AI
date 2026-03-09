from flask import Flask, render_template, request
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


@app.route("/")
def index():
    # if "name" in request.args:
    #     name = request.args["name"]
    # else:
    #     name = "User"
    name = request.args.get("name", "User")
    return render_template("index.html", placeholder=name)


if __name__ == "__main__":
    app.run(debug=True)
