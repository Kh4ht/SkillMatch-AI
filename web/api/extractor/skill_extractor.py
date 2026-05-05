import spacy
from spacy.matcher import PhraseMatcher

nlp = spacy.load("en_core_web_sm")

skills_list = [
    "python", "java", "c++", "sql",
    "machine learning", "deep learning",
    "tensorflow", "pytorch",
    "nlp", "data analysis",
    "excel", "power bi"
]

def normalize_skill(skill):
    mapping = {
        "ml": "machine learning",
        "dl": "deep learning"
    }
    return mapping.get(skill.lower(), skill.lower())


def build_matcher():
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in skills_list]
    matcher.add("SKILLS", patterns)
    return matcher


def extract_skills(text):
    doc = nlp(text)
    matcher = build_matcher()
    matches = matcher(doc)

    found = set()
    for _, start, end in matches:
        skill = doc[start:end].text
        found.add(normalize_skill(skill))

    return list(found)