from PyPDF2 import PdfReader
import re

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


# region Text Extractors


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


# endregion
# region Info Extractors


def extract_email(text: str):
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else "unknown"


def extract_phone(text: str) -> str:
    """Extract phone number"""
    patterns = [
        r"\+?[\d\s\-\(\)]{10,20}",  # International format
        r"\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4}",  # US format
        r"\(\d{3}\)\s*\d{3}-\d{4}",  # (123) 456-7890
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            # Clean up the match
            phone = match.group()
            # Remove extra spaces and clean
            phone = " ".join(phone.split())
            return phone

    return "unknown"


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
        print("text is empty or null")
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
    """Extract name from resume using heuristics"""
    lines = text.split("\n")

    # Look for capitalized phrases in first few lines
    for i in range(min(5, len(lines))):
        line = lines[i].strip()
        if not line:
            continue

        # Check if line looks like a name (2-4 words, all capitalized or title case)
        words = line.split()
        if 1 < len(words) <= 4:
            # Check if all words are capitalized
            if all(w[0].isupper() for w in words if w):
                # Skip lines that look like email or phone
                if "@" not in line and not any(c.isdigit() for c in line):
                    # Skip common non-name headers
                    if not any(
                        word.lower() in line.lower()
                        for word in ["resume", "cv", "curriculum", "vitae"]
                    ):
                        return line

    return "unknown"


# endregion
