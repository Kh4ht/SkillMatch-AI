from database import Database
from extractors import *


class Candidate:
    def __init__(
        self,
        name,
        email,
        phone,
        skills,
        experience,
        education,
        resume_filename,
        match_score,
    ):
        self.name: str = name
        self.email: str = email
        self.phone: str = phone
        self.skills = skills
        self.experience: str = experience
        self.education: str = education
        self.resume_filename: str = resume_filename
        self.match_score: float = match_score

    def add_to_database(self):
        Database.execute(
            "INSERT INTO candidates (name, email, phone, resume_filename, match_score) VALUES (?, ?, ?, ?, ?)",
            (self.name, self.email, self.phone, self.resume_filename, self.match_score),
        )

    @classmethod
    def from_string(
        cls, resume_text: str, resume_filename: str, required_skills: list[str]
    ):

        return cls(
            extract_name(resume_text),
            extract_email(resume_text),
            extract_phone(resume_text),
            extract_skills(resume_text, required_skills),
            extract_experience(resume_text),
            extract_education(resume_text),
            resume_filename,
            0,  # TODO: Add match_score Calculation Logic
        )
