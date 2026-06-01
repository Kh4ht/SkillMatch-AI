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
