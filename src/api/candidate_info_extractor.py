import re

SKILLS_DB = [
    "python",
    "java",
    "c++",
    "c#",
    "unity",
    "sql",
    "flask",
    "fastapi",
    "react",
    "machine learning",
    "tensorflow",
]

EDUCATION_WORDS = [
    "bachelor",
    "master",
    "phd",
    "university",
    "college",
]


def extract_email(text):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def extract_phone(text):
    match = re.search(r"\+?\d[\d\s\-]{8,15}", text)
    return match.group(0) if match else None


def extract_skills(text):
    text_lower = text.lower()
    found = []

    for skill in SKILLS_DB:
        if skill in text_lower:
            found.append(skill)

    return found


def extract_education(text):
    lines = text.split("\n")

    results = []

    for line in lines:
        for word in EDUCATION_WORDS:
            if word in line.lower():
                results.append(line.strip())

    return results


def extract_experience(text):
    lines = text.split("\n")

    experience = []
    capture = False

    for line in lines:
        if "experience" in line.lower():
            capture = True
            continue

        if capture:
            if line.strip() == "":
                break
            experience.append(line)

    return experience


def extract_name(text):
    lines = text.split("\n")

    for line in lines[:5]:
        if len(line.split()) <= 4 and "@" not in line:
            return line.strip()

    return None


class Candidate:
    def __init__(
        self,
        name,
        email,
        phone,
        skills,
        experience,
        education,
        certifications,
        projects,
        resume_filename,
        match_score,
    ):
        self.name = name
        self.email = email
        self.phone = phone
        self.skills = skills
        self.experience = experience
        self.education = education
        self.certifications = certifications
        self.projects = projects
        self.resume_filename = resume_filename
        self.match_score = match_score

    @classmethod
    def from_string(cls, text, resume_filename):

        name = extract_name(text)
        email = extract_email(text)
        phone = extract_phone(text)

        skills = extract_skills(text)
        education = extract_education(text)
        experience = extract_experience(text)

        # certifications = extract_certifications(text)
        # projects = extract_projects(text)

        return cls(
            name,
            email,
            phone,
            skills,
            experience,
            education,
            None,
            None,
            resume_filename,
            0,
        )
