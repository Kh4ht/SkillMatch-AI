# region IMPORTS

# Standard Library Imports
import re
import pdfplumber
from docx import Document
from datetime import datetime

# Local Imports
from ..utils.utils import Utils

# endregion


class Extractors:
    """Functions to extract text and info from resumes."""

    # region TEXT EXTRACTION

    @staticmethod
    def extract_text_from_file(file) -> tuple[bool, str]:
        """Extract raw text from PDF or DOCX files using advanced layout reading."""
        try:
            filename = getattr(file, "filename", "").lower()

            # If the file is a Word document (docx)
            if filename.endswith(".docx"):
                doc = Document(file)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return (True, text.strip())

            # If the file is a PDF document, use pdfplumber to maintain structural layout
            else:
                # Use seek(0) to ensure reading from the beginning of the stream
                file.seek(0)
                text = ""
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text(layout=False)
                        if page_text:
                            text += page_text + "\n"
                return (True, text.strip())

        except Exception as e:
            return (False, f"Error extracting text: {e}")

    # endregion
    # #####################################################################

    # #####################################################################
    # region EMAIL

    @staticmethod
    def extract_email(text: str) -> str:
        pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        emails = re.findall(pattern, text)
        return emails[0] if emails else Utils.UNKNOWN

    # endregion
    # #####################################################################

    # #####################################################################
    # region PHONE

    @staticmethod
    def extract_phone(text: str) -> str:
        """Extract phone number"""
        patterns = [
            r"\+?[\d\s\-\(\)]{10,20}",
            r"\d{3}[-\.\s]?\d{3}[-\.\s]?\d{4}",
            r"\(\d{3}\)\s*\d{3}-\d{4}",
            r"07\d{8}",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group()
                phone = " ".join(phone.split())
                return phone

        return "unknown"

    # endregion
    # #####################################################################

    # #####################################################################
    # region EDUCATION

    @staticmethod
    def extract_education(text: str) -> str:
        text_lower = text.lower()
        lines = [line.strip() for line in text_lower.split("\n") if line.strip()]

        # البحث إذا كانت الكلمة في السطر التالي لعنوان التعليم
        for i, line in enumerate(lines):
            if "education" in line and i + 1 < len(lines):
                next_line = lines[i + 1]
                for word in Utils.EDUCATION_WORDS:
                    if word in next_line:
                        return word

        # فحص شامل كخيار احتياطي
        result: str = "none"
        c = Utils.EDUCATION_WORDS["none"]
        for line in lines:
            for word in Utils.EDUCATION_WORDS:
                if word in line:
                    if Utils.EDUCATION_WORDS[word] > c:
                        result = word
        return result

    # endregion
    # #####################################################################

    # #####################################################################
    # region NAME

    @staticmethod
    def extract_name(text: str) -> str:
        """Extract name by safely removing labels and cleaning multi-column artifacts."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return "unknown"

        for i, line in enumerate(lines[:5]):
            # 1. If the name is explicitly labeled inline
            if re.search(r"^(full\s+)?name\s*:\s*", line, flags=re.IGNORECASE):
                clean_line = re.sub(
                    r"^(full\s+)?name\s*:\s*", "", line, flags=re.IGNORECASE
                ).strip()
                if clean_line:
                    return clean_line

            # 2. If the line contains only the label
            if line.lower().strip() in ["full name:", "name:", "full name", "name"]:
                if i + 1 < len(lines):
                    return lines[i + 1]

        # 3. Handle messy lines by extracting the first 2 to 3 alphabetical words (Standard Name)
        first_line = lines[0]
        # Clean inline symbols like pipelines | or emails often found next to names in PDF extraction
        clean_first_line = first_line.split("|")[0].split(",")[0].strip()
        words = clean_first_line.split()
        if len(words) >= 1:
            return " ".join(words[:3])

        return "unknown"

    # endregion
    # #####################################################################

    # #####################################################################
    # region EXPERIENCE

    @staticmethod
    def extract_experience_years(text: str) -> int:
        """Extract experience years including start-year ranges like 2021 - Present."""

        current_year = datetime.now().year
        text_lower = text.lower()

        # normalize text
        lines = [line.strip() for line in text_lower.split("\n") if line.strip()]

        # -----------------------------
        # 1. Handle YEAR RANGE patterns (most important fix)
        # -----------------------------
        range_patterns = [
            r"(\d{4})\s*[-–]\s*(present|current|\d{4})",
            r"(\d{4})\s*to\s*(present|current|\d{4})",
        ]

        for line in lines:
            for pattern in range_patterns:
                match = re.search(pattern, line)
                if match:
                    start_year = int(match.group(1))
                    end_part = match.group(2)

                    # if still working
                    if end_part in ["present", "current"]:
                        end_year = current_year
                    else:
                        end_year = int(end_part)

                    exp_years = end_year - start_year

                    if 0 <= exp_years <= 50:
                        return exp_years

        # -----------------------------
        # 2. Handle normal "X years experience"
        # -----------------------------
        patterns = [
            # (40 years), 40 years, 40years, 40 yrs, etc.
            r"\(?\s*(\d{1,2})\s*(?:\+|-)?\s*(?:year|years|yr|yrs)\s*\)?",
            # experience: 40 years / experience 40 years
            r"experience\s*[:\-]?\s*\(?\s*(\d{1,2})\s*(?:\+|-)?\s*(?:year|years|yr|yrs)\s*\)?",
            # 40 years experience / 40yrs exp / 40 years exp
            r"\(?\s*(\d{1,2})\s*(?:\+|-)?\s*(?:year|years|yr|yrs)\s*\)?\s*(?:of\s*)?(?:experience|exp)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    exp_years = int(match.group(1))
                    if 0 <= exp_years <= 50:
                        return exp_years
                except ValueError:
                    continue

        # -----------------------------
        # 3. fallback
        # -----------------------------
        return 0

    # endregion
