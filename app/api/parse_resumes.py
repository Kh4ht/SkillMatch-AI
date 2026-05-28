# region IMPORTS


# Standard library imports
from datetime import datetime
import os
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    current_app,
    send_from_directory,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

# Local imports
from config import Config
from .models.extractors import Extractors
from .models.models import Candidate
from .utils.utils import Utils
from .models.ats_scorer import calculate_match_score as advanced_score

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

    return render_template("parse_resumes.html")


# endregion
# #####################################################################

# #####################################################################
# region ADD JOB


@parse_resumes_bp.route("/add_job", methods=["POST"])
def add_job_submit():
    required_skills = Utils.request_form_get_as_list("required_skills")
    required_skills_weight = Utils.request_form_get_as_int_list(
        "required_skills_weight"
    )

    min_years_exp = Utils.request_form_get_as_int("min_years_exp")
    min_education_weight = Utils.request_form_get_as_int("min_education_weight")
    min_years_exp_weight = Utils.request_form_get_as_int("min_years_exp_weight")

    job_title = Utils.request_form_get("job_title")
    min_education = Utils.request_form_get("min_edu")

    skill_name_weight: dict[str, int] = {}

    for name, weight in zip(required_skills, required_skills_weight):
        skill_name_weight[name] = weight

    success, error_msg = current_user.add_job(
        job_title=job_title,
        min_edu=min_education,
        min_years_exp=min_years_exp,
        min_edu_weight=min_education_weight,
        min_exp_weight=min_years_exp_weight,
        skill_name_weight=skill_name_weight,
    )

    if success:
        flash(error_msg, "success")
    else:
        flash(error_msg, "error")

    return redirect("/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region ADD CANDIDATES


@parse_resumes_bp.route("/add_candidates", methods=["POST"])
def add_candidates_submit():

    files = Utils.request_files_get_as_list("resumeUpload")
    job_id = Utils.request_form_get_as_int("selected_job_id")

    target_job = current_user.get_job(job_id)
    if target_job is None:
        flash("Job not found, ID could be wrong.", "error")
        return redirect("/parse_resumes")

    if len(files) == 0 or files[0].filename == "":
        flash("No files selected", "error")
        return redirect("/parse_resumes")

    # List of original filenames for successfully uploaded resumes
    successful_uploads: list[str] = []
    # List of (filename, error_message) for failed uploads
    failed_uploads: list[tuple[str, str]] = []

    for file in files:
        if file and Utils.allowed_file(file.filename):

            # Secure the filename
            original_filename: str = file.filename  # type: ignore
            secure_name: str = secure_filename(original_filename)  # type: ignore

            # Add timestamp to avoid filename conflicts
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{secure_name}"

            success, file_text = Extractors.extract_text_from_file(file)
            if not success:
                failed_uploads.append((original_filename, file_text))
                continue

            # Save file path
            file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)

            try:
                # Get file size directly from memory stream
                file.seek(0, os.SEEK_END)
                file_size_bytes = file.tell()
                file.seek(0)

                # 1. Extract all entities dynamically from code layout
                extracted_name = Extractors.extract_name(file_text)
                extracted_email = Extractors.extract_email(file_text)
                extracted_phone = Extractors.extract_phone(file_text)
                extracted_education = Extractors.extract_education(file_text)
                extracted_experience = Extractors.extract_experience_years(file_text)

                # 🛠️ Extract skills as a clean List directly
                extracted_skills_list = Extractors.extract_skills(
                    file_text, target_job.skillname_skillweight_dict
                )

                # 2. Calculate the advanced match score using TF-IDF + BM25 + Semantic NER ensemble
                calculated_score = advanced_score(
                    extracted_skills=extracted_skills_list,
                    extracted_education=extracted_education,
                    extracted_experience=extracted_experience,
                    job_requirements=target_job,
                    resume_text=file_text,        # enables TF-IDF + BM25
                    job_description_text=" ".join(target_job.skillname_skillweight_dict.keys()),      # optionally pass JD text
                )

                # 3. Insert candidate: Pass extracted_skills_list directly as a list to avoid double-join artifacts
                success_insert, msg = current_user.add_candidate(
                    job_id=job_id,
                    name=extracted_name,
                    email=extracted_email,
                    phone=extracted_phone,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=float(file_size_bytes),
                    education=extracted_education,
                    skills=extracted_skills_list,  # 👈 مرر القائمة مباشرة هنا لحل التشوهات
                    experience_years=extracted_experience,
                    match_score=calculated_score,
                )

                if not success_insert:
                    failed_uploads.append((original_filename, msg))
                    continue

                file.save(file_path)
                successful_uploads.append(original_filename)

            except Exception as e:
                failed_uploads.append((original_filename, str(e)))
                continue
        else:
            failed_uploads.append(
                (
                    original_filename,
                    f"Invalid file type (allowed types: {', '.join(Config.ALLOWED_EXTENSIONS)})",
                )
            )

    if successful_uploads:
        flash(
            f'Successfully uploaded {len(successful_uploads)} resume(s): {", ".join(successful_uploads)}',
            "success",
        )

    if failed_uploads:
        flash(
            f'Failed to upload {len(failed_uploads)} file(s): {", ".join(failed_uploads[0])}',
            "error",
        )

    return redirect("/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region DELETE JOB


@parse_resumes_bp.route("/delete_job", methods=["POST"])
@login_required
def delete_job_submit():
    job_id = Utils.request_form_get_as_int("job_id")

    success, error_msg = current_user.delete_job(job_id=job_id)

    if success:
        flash(error_msg, "success")
    else:
        flash(error_msg, "error")

    return redirect("/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region DELETE CANDIDATE


@parse_resumes_bp.route("/delete_candidate", methods=["POST"])
@login_required
def delete_candidates_submit():
    candidates_ids = Utils.request_form_get_as_int_list("candidate_ids_to_delete")

    success_count = 0
    error_count = 0
    for c_id in candidates_ids:
        success, error_msg = current_user.delete_candidate(candidate_id=c_id)

        if success:
            success_count += 1
        else:
            error_count += 1

    if error_count > 0:
        flash(f"{error_count} candidate(s) could not be deleted", "error")
    else:
        flash(f"{success_count} candidate(s) deleted successfully", "success")

    return redirect("/parse_resumes")


# endregion
# #####################################################################

# #####################################################################
# region VIEW RESUME


@parse_resumes_bp.route("/view_resume/<int:candidate_id>")
@login_required
def view_resume_by_id(candidate_id):
    """Fetches the actual filename from the database using candidate ID and serves it securely."""

    candidate: Candidate | None = current_user.get_candidate_by_id(candidate_id)

    if candidate is None:
        flash("Candidate not found.", "error")
        return redirect("/parse_resumes")

    file_path = candidate.file_path

    if not Utils.is_in_uploads_folder(candidate.filename):
        flash("Resume file not found in uploads folder.", "error")
        return redirect("/parse_resumes")

    return send_from_directory(Config.UPLOAD_FOLDER, os.path.basename(file_path))


# endregion
