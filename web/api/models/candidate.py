# region IMPORTS


import sqlite3
from venv import logger

from .database import Database
from .extractors import (
    extract_name,
    extract_email,
    extract_phone,
    extract_education,
    EDUCATION_WORDS,
    extract_skills,
)


# endregion
# #####################################################################

# #####################################################################
# region Candidate Class


class Candidate:
    def __init__(
        self,
        name,
        email,
        phone,
        resume_filename,
        match_score,
        education,
        skills,
    ):
        self.name: str = name
        self.email: str = email
        self.phone: str = phone
        self.education: str = education
        self.resume_filename: str = resume_filename
        self.match_score: float = match_score
        self.skills: list[str] = skills

    def add_to_database(self):
        try:
            Database.execute_set(
                """INSERT INTO candidates (name, email, phone, resume_filename, match_score, education, skills) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    self.name,
                    self.email,
                    self.phone,
                    self.resume_filename,
                    self.match_score * 100,
                    self.education,
                    " | ".join(self.skills),
                ),
            )
        except sqlite3.IntegrityError as e:
            # Handle Duplicate Entries
            logger.error
            raise e

    @classmethod
    def from_string(
        cls,
        resume_text: str,
        resume_filename: str,
        required_skills: list[str],
        min_education: str,
    ):
        education = extract_education(resume_text)

        found_skills = extract_skills(resume_text, required_skills)

        def calculate_match_score() -> float:

            total_weight = len(required_skills) + 1  # 1 for education

            have_min_edu = EDUCATION_WORDS[education] >= EDUCATION_WORDS[min_education]

            return (len(found_skills) + have_min_edu) / total_weight

        return cls(
            name=extract_name(resume_text),
            email=extract_email(resume_text),
            phone=extract_phone(resume_text),
            education=education,
            resume_filename=resume_filename,
            match_score=calculate_match_score(),
            skills=found_skills,
        )


# endregion
