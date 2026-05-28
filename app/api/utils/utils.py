# region IMPORTS

# Standard library imports
from flask import request
from werkzeug.datastructures import FileStorage
import os

# Local imports
from config import Config

# endregion


class Utils:
    "Utility functions for the application."

    UNKNOWN = "unknown"
    EDUCATION_WORDS: dict[str, int] = {
        "phd": 4,
        "doctorate": 4,
        #
        "master": 3,
        "masters": 3,
        #
        "bachelor": 2,
        "bachelors": 2,
        #
        "highschool": 1,
        "high school": 1,
        "diploma": 1,
        #
        "none": 0,
    }

    # region QUERY

    @staticmethod
    def allowed_file(filename: str | None) -> bool:
        if filename is None:
            return False

        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
        )

    @staticmethod
    def is_in_uploads_folder(resume_filename: str) -> bool:
        for file in os.listdir(Config.UPLOAD_FOLDER):
            if file == resume_filename:
                return True
        return False

    # endregion
    # region FORM GETTERS

    @staticmethod
    def request_form_get(element_id: str, strip=True) -> str:

        result = request.form.get(element_id)

        if result is not None:
            if strip:
                result = result.strip()
            return result
        else:
            raise ValueError(f"The Request Field: '{element_id}' Is NONE")

    @staticmethod
    def request_form_get_as_int(element_id: str) -> int:

        result = request.form.get(element_id)

        if result is not None:
            try:
                result = int(result)
            except Exception as e:
                raise e
            return result
        else:
            raise ValueError(f"The Request Field: '{element_id}' Is NONE")

    @staticmethod
    def request_form_get_as_list(element_id: str, strip=True) -> list[str]:

        result = request.form.get(element_id)

        if result is not None:
            if strip:
                stripped_result = []
                for r in result.split(","):
                    stripped_result.append(r.strip())
                return stripped_result
            else:
                result = result.split(",")
                return result
        else:
            raise ValueError(f"The Request Field: '{element_id}' Is NONE")

    @staticmethod
    def request_form_get_as_int_list(element_id: str) -> list[int]:

        result = request.form.get(element_id)

        if result is not None:
            new_result = []
            for r in result.split(","):
                try:
                    new_result.append(int(r.strip()))
                except Exception as e:
                    raise ValueError(
                        f"Element '{r}' In Request Field: '{element_id}' Is Not An Integer"
                    ) from e

            return new_result
        else:
            raise ValueError(f"The Request Field: '{element_id}' Is NONE")

    # endregion
    # region FILES GETTERS

    @staticmethod
    def request_files_get_as_list(element_id: str) -> list[FileStorage]:

        result = request.files.getlist(element_id)

        if result is not None or len(result) > 0:
            return result
        else:
            raise ValueError(
                f"The Request Files Field: '{element_id}' Is NONE or Empty"
            )

    # endregion
    # region MATCH SCORE

    from ..models.models import Job

    @staticmethod
    def calculate_match_score(
        extracted_skills: list[str],
        extracted_education: str,
        extracted_experience: int,
        job_requirements,
    ) -> float:
        """
        Calculates the professional match score percentage based on extracted data
        and job requirements weights dynamically.
        """
        if not job_requirements:
            return 0.0

        score = 0.0

        # 1. Calculate Experience Score component
        if extracted_experience >= job_requirements.min_years_exp:
            score += float(job_requirements.min_exp_weight)
        elif job_requirements.min_years_exp > 0:
            # Partial score if candidate has experience but less than required
            experience_ratio = extracted_experience / job_requirements.min_years_exp
            score += float(job_requirements.min_exp_weight) * experience_ratio

        # 2. Calculate Education Score component using levels map
        candidate_edu_level = Utils.EDUCATION_WORDS.get(
            extracted_education.lower().strip(), 0
        )
        required_edu_level = Utils.EDUCATION_WORDS.get(
            job_requirements.min_edu.lower().strip(), 0
        )

        if candidate_edu_level >= required_edu_level:
            score += float(job_requirements.min_edu_weight)

        # 3. Calculate Skills Score component matching requirements dict
        job_skills_dict = job_requirements.skillname_skillweight_dict or {}
        if job_skills_dict:
            # Normalize extracted skills for comparison
            normalized_extracted = [s.lower().strip() for s in extracted_skills]

            for req_skill, skill_weight in job_skills_dict.items():
                if req_skill.lower().strip() in normalized_extracted:
                    score += float(skill_weight)

        # Ensure the final score is clamped between 0 and 100
        return min(100.0, max(0.0, round(score, 1)))

    # endregion
