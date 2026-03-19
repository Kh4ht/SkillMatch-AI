from PyPDF2 import PdfReader
import re

EDUCATION_WORDS: dict[str, int] = {
    "none": 0,
    "highschool": 1,
    "bachelor": 2,
    "master": 3,
    "phd": 4,
}


# Text Extractors ###########################################################


def _extract_text(file) -> str | None:
    """Extract raw text from a (PDF,)."""

    try:
        reader = PdfReader(file)
        text = ""

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        return text.strip()

    except Exception as e:
        print(f"Error extracting text from PDF: {e}")


def extract_text_as_list(file) -> list[str] | None:
    """Return the resume text split into words."""

    text = _extract_text(file)
    if text is None:
        return None

    return text.split()


def extract_text_as_str(file) -> str | None:
    """Return the resume text as a single string."""

    return _extract_text(file)


# Info Extractors ###########################################################


def extract_email(text: str):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else "unknown"


def extract_phone(text: str):
    match = re.search(r"\+?\d[\d\s\-]{8,15}", text)
    return match.group(0) if match else "unknown"


def extract_skills(text: str, required_skills: list[str]) -> list[str]:
    text_lower = text.lower()
    found = []

    for skill in required_skills:
        if skill in text_lower and skill not in found:
            found.append(skill)

    return found


def extract_education(text: str) -> str:
    lines = text.split("\n")

    if not lines:
        return "unknown"

    result: str = "none"
    c = EDUCATION_WORDS["none"]

    for line in lines:
        for word in EDUCATION_WORDS:
            if word in line.lower():
                if EDUCATION_WORDS[word] > c:
                    result = word
    return result


# def extract_experience(text: str) -> list[str]:
#     lines = text.split("\n")

#     experience = []
#     capture = False

#     for line in lines:
#         if "experience" in line.lower():
#             capture = True
#             continue

#         if capture:
#             if line.strip() == "":
#                 break
#             experience.append(line)

#     return experience


def extract_name(text: str) -> str:
    lines = text.split("\n")

    for line in lines[:5]:
        if len(line.split()) <= 4 and "@" not in line:
            return line.strip()

    return "unknown"
