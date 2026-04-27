# region IMPORTS


# Standard library imports
from flask import Blueprint, flash, redirect, render_template, request
from flask_login import current_user, login_required

# Local imports
from models.models import Job
from models.user import User
from models.database import Database
from utils.utils import request_form_get


# endregion
# #####################################################################

# #####################################################################
# region SETUP Blueprint


parse_resumes_bp = Blueprint("parse_resumes", __name__, url_prefix="/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region PARSE RESUMES


@parse_resumes_bp.route("/")
@login_required
def parse_resumes_page():

    return render_template(
        "parse_resumes.html",
        jobs=User.get_jobs(),
    )


# endregion
# #####################################################################

# #####################################################################
# region ADD JOB


@parse_resumes_bp.route("/add_job", methods=["POST"])
def add_job_submit():
    job_title = request_form_get("job_title")
    required_skills = request_form_get("required_skills")
    min_education = request_form_get("min_edu")
    min_years_exp = request_form_get("min_years_exp")

    skill_name_weight: dict[str, int] = {}

    required_skills = required_skills.split(",")

    for i in required_skills:
        skill_name_weight[i.strip()] = 1

    success, error_msg = User.add_job(
        user_id=current_user.id,
        job_title=job_title,
        min_edu=min_education,
        min_years_exp=int(min_years_exp),
        min_edu_weight=1,
        min_exp_weight=1,
        skill_name_weight=skill_name_weight,
    )

    if success:
        flash(f"Job '{job_title}' added successfully!", "success")
        return redirect("/parse_resumes")
    else:
        flash(error_msg, "error")
        return redirect("/parse_resumes")


# endregion
