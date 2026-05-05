import re

def extract_phone(text):
    pattern = r"\+?\d[\d\s\-]{7,15}"
    return re.findall(pattern, text)