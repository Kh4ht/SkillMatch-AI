"""
SkillMatch-AI — ATS Scoring Engine
====================================
app/api/models/ats_scorer.py

Three scoring algorithms:
  1. TF-IDF cosine similarity  (sublinear TF, length-normalised)
  2. BM25 Okapi                (probabilistic term ranking)
  3. Experience + Education    (structured signals)

Skill matching is intentionally weighted based on JD quality:
  - Structured JD (has bullet list / requirements section) → skills carry 45%
  - Vague paragraph JD (no structure) → text similarity carries more, skills carry 20%

This prevents the common case where a vague one-paragraph JD causes everyone
to score identically on skills (since no one has "engineering team" in their CV).
"""

import math
import re
import warnings
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Job


# ─────────────────────────────────────────────
# SBERT (optional — graceful fallback if not installed)
# ─────────────────────────────────────────────
_sbert_model = None


def _get_sbert_model():
    global _sbert_model
    if _sbert_model is not None:
        return _sbert_model
    try:
        from sentence_transformers import SentenceTransformer

        _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _sbert_model = None
    return _sbert_model


def _sbert_cosine(r: str, j: str) -> float:
    model = _get_sbert_model()
    if not model:
        return 0.0
    emb = model.encode([r[:1000], j[:1000]], convert_to_numpy=True)
    a, b = emb[0], emb[1]
    dot = float(a @ b)
    na = float((a**2).sum() ** 0.5)
    nb = float((b**2).sum() ** 0.5)
    return dot / (na * nb) if na and nb else 0.0


# ─────────────────────────────────────────────
# spaCy (optional — graceful fallback)
# ─────────────────────────────────────────────
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    except Exception:
        _nlp = None
    return _nlp


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
EDUCATION_LEVELS = {
    "phd": 4,
    "doctorate": 4,
    "master": 3,
    "masters": 3,
    "bachelor": 2,
    "bachelors": 2,
    "highschool": 1,
    "diploma": 1,
    "none": 0,
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "in",
    "on",
    "at",
    "for",
    "to",
    "of",
    "with",
    "is",
    "are",
    "be",
    "have",
    "has",
    "been",
    "we",
    "our",
    "you",
    "i",
    "my",
    "it",
    "its",
    "this",
    "that",
    "as",
    "by",
    "from",
    "was",
    "were",
    "will",
    "can",
    "should",
    "must",
    "may",
    "not",
    "but",
    "if",
    "so",
    "do",
    "did",
    "who",
    "what",
    "how",
    "when",
    "where",
    "also",
    "than",
    "more",
    "some",
    "any",
    "all",
    "into",
    "over",
    "after",
    "about",
    "no",
    "just",
    "them",
    "then",
    "there",
    "these",
    "those",
    "would",
    "could",
    "both",
    "each",
}

# Words that make a noun phrase NOT a skill
NOT_SKILL = {
    "year",
    "years",
    "experience",
    "exp",
    "month",
    "months",
    "minimum",
    "background",
    "degree",
    "bachelor",
    "master",
    "phd",
    "doctorate",
    "diploma",
    "university",
    "college",
    "education",
    "school",
    "graduate",
    "undergraduate",
    "msc",
    "bsc",
    "mba",
    "ability",
    "skill",
    "skills",
    "knowledge",
    "understanding",
    "familiarity",
    "proficiency",
    "team",
    "role",
    "position",
    "candidate",
    "applicant",
    "employer",
    "employee",
    "company",
    "opportunity",
    "environment",
    "culture",
    "benefit",
    "salary",
    "package",
    "office",
    "location",
    "responsibilities",
    "requirement",
    "requirements",
    "qualifications",
    "preferred",
    "required",
    "plus",
    "bonus",
    "advantage",
    "developer",
    "engineer",
    "manager",
    "designer",
    "analyst",
    "architect",
    "consultant",
    "specialist",
    "coordinator",
    "director",
    "intern",
    "lead",
    "head",
    "officer",
    "associate",
    "assistant",
    "senior",
    "junior",
    "mid",
    "entry",
    "solution",
    "solutions",
    "service",
    "services",
    "system",
    "systems",
    "platform",
    "product",
    "products",
    "technology",
    "technologies",
    "stack",
    "framework",
    "client",
    "clients",
    "project",
    "projects",
    "business",
    "member",
    "members",
    "build",
    "maintain",
    "collaborate",
    "deliver",
    "join",
    "looking",
    "work",
    "ensure",
    "support",
    "help",
    "use",
    "using",
    "make",
    "create",
    "write",
    "develop",
    "manage",
}

_HAS_DIGIT = re.compile(r"\d")
_BULLET_RE = re.compile(
    r"^\s*(?:[•\-\u2013\u2014*\u25aa\u25ba\u2713\u2714\u25cb\u25cf\u25e6]"
    r"|\d+[.)]\s*|[a-z][.)]\s*)\s*",
    re.MULTILINE,
)
_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:required|requirements?|qualifications?|skills?\s*(?:required|needed)?"
    r"|what you(?:\'ll)? need|must[- ]have|technical skills?|key skills?"
    r"|core skills?|minimum qualifications?)\s*:?\s*(?:\n|$)",
    re.IGNORECASE,
)
_BOILERPLATE = re.compile(
    r"^(?:knowledge\s+of|familiarity\s+with|experience\s+(?:with|in|using)|"
    r"expertise\s+in|proficiency\s+in|understanding\s+of|ability\s+to|"
    r"working\s+knowledge\s+of|solid\s+understanding\s+of|"
    r"good\s+knowledge\s+of|hands[- ]on\s+experience\s+(?:with|in))\s+",
    re.IGNORECASE,
)
_NOISE = {
    "similar languages",
    "similar tools",
    "equivalent",
    "or equivalent",
    "related field",
    "bonus",
    "advantage",
    "preferred",
    "nice to have",
}
# Known tech keywords to pull directly from a paragraph-style JD
_TECH_KEYWORDS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "nodejs",
    "ruby",
    "php",
    "golang",
    "rust",
    "scala",
    "kotlin",
    "swift",
    "c++",
    "cpp",
    "c#",
    "flask",
    "django",
    "fastapi",
    "spring",
    "express",
    "rails",
    "laravel",
    "react",
    "vue",
    "angular",
    "html",
    "css",
    "sass",
    "sql",
    "mysql",
    "postgresql",
    "sqlite",
    "mongodb",
    "redis",
    "elasticsearch",
    "rest api",
    "restful",
    "graphql",
    "grpc",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "linux",
    "bash",
    "git",
    "machine learning",
    "deep learning",
    "tensorflow",
    "pytorch",
    "pandas",
    "numpy",
    "scikit-learn",
    "web api",
    "web apis",
    "microservices",
    "api",
    "apis",
    "ci/cd",
    "devops",
    "agile",
    "scrum",
]


# ─────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────
def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1 and t not in STOPWORDS]


def _stem(w: str) -> str:
    w = w.lower().rstrip("s")
    if w.endswith("ie"):
        w = w[:-2] + "y"
    return w


def _is_valid_skill(phrase: str) -> bool:
    if _HAS_DIGIT.search(phrase):
        return False
    words = phrase.lower().split()
    if not words or len(words) > 4:
        return False
    meaningful = [w for w in words if len(w) > 2]
    if meaningful and all(w in NOT_SKILL for w in meaningful):
        return False
    return True


def _strip_article(s: str) -> str:
    for art in ("a ", "an ", "the "):
        if s.startswith(art):
            return s[len(art) :]
    return s


# ─────────────────────────────────────────────
# ALGORITHM 1 — TF-IDF (sublinear, length-normalised)
# ─────────────────────────────────────────────
def _tfidf_cosine(resume_text: str, job_text: str) -> float:
    corpus = [resume_text, job_text]
    tokenized = [_tokenize(d) for d in corpus]
    vocab = set(t for d in tokenized for t in d)
    N = 2

    def vec(tokens):
        tf = Counter(tokens)
        v = {}
        for t in vocab:
            c = tf.get(t, 0)
            tf_val = (1 + math.log(c)) if c > 0 else 0.0
            df = sum(1 for d in tokenized if t in d)
            idf = math.log((N + 1) / (df + 1)) + 1
            v[t] = tf_val * idf
        return v

    v1, v2 = vec(tokenized[0]), vec(tokenized[1])
    dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in vocab)
    n1 = math.sqrt(sum(x**2 for x in v1.values()))
    n2 = math.sqrt(sum(x**2 for x in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


# ─────────────────────────────────────────────
# ALGORITHM 2 — BM25 (Okapi)
# ─────────────────────────────────────────────
def _bm25(query: str, doc: str, k1: float = 1.5, b: float = 0.75) -> float:
    corpus = [query, doc]
    tc = [_tokenize(x) for x in corpus]
    qt = _tokenize(query)
    dt = _tokenize(doc)
    adl = sum(len(d) for d in tc) / len(tc)
    dtf = Counter(dt)
    score = 0.0
    for t in qt:
        df = sum(1 for d in tc if t in d)
        idf = math.log((2 - df + 0.5) / (df + 0.5) + 1)
        tf = dtf.get(t, 0)
        score += idf * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * len(dt) / adl)))
    mp = len(qt) * math.log(3)
    return min(score / mp, 1.0) if mp > 0 else 0.0


# ─────────────────────────────────────────────
# ALGORITHM 3 — SKILL MATCH (stem + substring)
# ─────────────────────────────────────────────
def _semantic_skill_score(
    resume_text: str,
    job_skill_dict: dict,
) -> tuple[float, list[str], list[str]]:
    if not job_skill_dict:
        return 1.0, [], []

    nlp = _get_nlp()

    if nlp:
        from spacy.matcher import PhraseMatcher

        matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
        skill_docs = {}
        for skill in job_skill_dict:
            sdoc = nlp(skill.lower()[:200])
            skill_docs[skill] = sdoc
            matcher.add(skill, [sdoc])

        resume_doc = nlp(resume_text.lower()[:50_000])
        matched_ids = {nlp.vocab.strings[mid] for mid, _, __ in matcher(resume_doc)}
        matched, unmatched = [], []
        for skill in job_skill_dict:
            (matched if skill in matched_ids else unmatched).append(skill)

        resume_lemmas = {
            t.lemma_
            for t in resume_doc
            if not t.is_punct and not t.is_space and not t.is_stop
        }
        missing = []
        for skill in unmatched:
            sl = {
                t.lemma_ for t in skill_docs[skill] if not t.is_punct and not t.is_space
            }
            if sl and len(sl & resume_lemmas) / len(sl) >= 0.6:
                matched.append(skill)
            else:
                missing.append(skill)

        return len(matched) / len(job_skill_dict), matched, missing

    # Stem-based fallback
    text_lower = resume_text.lower()
    resume_stems = {_stem(t) for t in _tokenize(resume_text)}
    matched, missing = [], []
    for skill in job_skill_dict:
        if skill.lower() in text_lower:
            matched.append(skill)
            continue
        skill_stems = {_stem(t) for t in _tokenize(skill)}
        if skill_stems and len(skill_stems & resume_stems) / len(skill_stems) >= 0.6:
            matched.append(skill)
        else:
            missing.append(skill)

    return len(matched) / len(job_skill_dict), matched, missing


# ─────────────────────────────────────────────
# JD QUALITY DETECTION
#
# A "structured" JD has explicit bullet points or a requirements section.
# A "vague" JD is a plain paragraph.
#
# This matters because:
#   - Structured JD → skill matching is reliable and should dominate
#   - Vague JD      → skill matching is unreliable (everyone matches the same
#                     generic terms), so text similarity + experience should dominate
# ─────────────────────────────────────────────
def _jd_is_structured(jd_text: str) -> bool:
    has_section = bool(_SECTION_RE.search(jd_text))
    has_bullets = bool(_BULLET_RE.search(jd_text))
    has_list = jd_text.count(",") >= 3 and any(
        len(part.split()) <= 4 for part in jd_text.split(",")
    )
    return has_section or has_bullets or has_list


# ─────────────────────────────────────────────
# JD SKILL EXTRACTION
# ─────────────────────────────────────────────
def auto_extract_job_requirements(
    job_description: str,
    job_title: str = "",
) -> dict:
    """
    Extracts skills, experience, education, and weights from a JD.
    Handles both structured (bullet-point) and unstructured (paragraph) JDs.
    """
    text = (job_title + "\n" + job_description).strip()
    text_lower = text.lower()

    # ── Experience ────────────────────────────────────────────────────
    exp_patterns = [
        # 40+ exp / 40+ years / 40+ yrs experience
        r"(\d+)\s*\+\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        # 40 exp / 40 years / 40yrs exp
        r"(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)",
        # minimum 40 exp / min40 exp / minimum 40 years
        r"(?:minimum|min)\s*(?:of\s*)?\s*(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        # at least 40 exp / atleast40 exp
        r"at\s*least\s*(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        # 3-5 years experience / 3-5 exp
        r"(\d+)\s*[-\u2013]\s*\d+\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
    ]

    seniority = {
        "principal": 7,
        "staff": 6,
        "senior": 5,
        "lead": 5,
        "mid-level": 3,
        "intermediate": 3,
        "junior": 1,
        "entry level": 0,
        "entry-level": 0,
        "graduate": 0,
    }
    min_years_exp = 0
    for pat in exp_patterns:
        m = re.search(pat, text_lower)
        if m:
            try:
                min_years_exp = int(m.group(1))
                break
            except:
                pass
    if not min_years_exp:
        for kw, yrs in seniority.items():
            if kw in text_lower:
                min_years_exp = yrs
                break

    # ── Education ─────────────────────────────────────────────────────
    edu_map = [
        ("phd", 4),
        ("doctorate", 4),
        ("master", 3),
        ("msc", 3),
        ("mba", 3),
        ("bachelor", 2),
        ("bsc", 2),
        ("undergraduate", 2),
        ("degree", 2),
        ("diploma", 1),
        ("high school", 1),
    ]
    min_edu, best = "none", 0
    for kw, lvl in edu_map:
        if kw in text_lower and lvl > best:
            min_edu = {
                "msc": "master",
                "mba": "master",
                "bsc": "bachelor",
                "undergraduate": "bachelor",
            }.get(kw, kw)
            best = lvl

    # ── Urgency weights ───────────────────────────────────────────────
    HIGH = ["required", "must have", "essential", "mandatory"]
    LOW = ["preferred", "nice to have", "bonus", "desirable"]

    def urgency(kws):
        for sent in re.split(r"[.;\n]", text_lower):
            if any(k in sent for k in kws):
                if any(u in sent for u in HIGH):
                    return "high"
                if any(u in sent for u in LOW):
                    return "low"
        return "normal"

    exp_mentioned = any(
        k in text_lower
        for k in [
            "experience",
            "years",
            "year",
            "exp",
            "senior",
            "junior",
            "mid-level",
            "lead",
        ]
    )
    edu_mentioned = any(
        k in text_lower
        for k in [
            "education",
            "degree",
            "bachelor",
            "master",
            "phd",
            "diploma",
            "university",
        ]
    )

    if not exp_mentioned and min_years_exp == 0:
        base_exp = 0
    else:
        exp_u = urgency(["experience", "years", "exp"])
        base_exp = 30 if exp_u == "high" else (20 if exp_u == "low" else 25)

    if not edu_mentioned:
        base_edu = 0
        min_edu = "none"
    else:
        edu_u = urgency(["education", "degree", "bachelor", "master", "phd"])
        base_edu = 20 if edu_u == "high" else (10 if edu_u == "low" else 15)

    skills_pct = 100 - base_exp - base_edu

    # ── Skill extraction ──────────────────────────────────────────────
    structured = _jd_is_structured(job_description)

    if structured:
        skill_names = _extract_structured_skills(job_description)
    else:
        skill_names = _extract_paragraph_skills(text)

    # Deduplicate: remove shorter phrases that are substrings of longer ones
    # e.g. 'api' and 'apis' and 'web api' → keep 'web api' only
    skill_names = _deduplicate_skills(skill_names)[:20]

    n = len(skill_names) or 1
    per_skill = skills_pct // n
    remainder = skills_pct - per_skill * n
    skill_dict = {
        s: per_skill + (remainder if i == 0 else 0) for i, s in enumerate(skill_names)
    }

    return {
        "skills": skill_dict,
        "min_edu": min_edu,
        "min_years_exp": min_years_exp,
        "min_edu_weight": base_edu,
        "min_exp_weight": base_exp,
        "jd_structured": structured,
    }


def _extract_structured_skills(jd_text: str) -> list[str]:
    """Extract skills from a structured JD (has Requirements: section or bullets)."""
    sections = []
    matches = list(_SECTION_RE.finditer(jd_text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else start + 800
        sections.append(jd_text[start:end])
    section_text = "\n".join(sections) if sections else jd_text

    items = []
    for line in section_text.splitlines():
        clean = _BULLET_RE.sub("", line).strip()
        if not clean or len(clean) < 2:
            continue
        parts = re.split(r"[,;]", clean) if ("," in clean or ";" in clean) else [clean]
        for part in parts:
            part = _BOILERPLATE.sub("", part.strip()).strip()
            if not part:
                continue
            for atom in re.split(r"\s*/\s*|\s+or\s+|\s*&\s*", part):
                atom = atom.strip()
                if atom:
                    items.append(atom)

    skill_names = []
    seen = set()
    for item in items:
        clean = re.sub(r"\s+", " ", item.lower())
        clean = re.sub(r"[^a-z0-9\s#+.\-]", "", clean).strip()
        if not clean or clean in seen or clean in _NOISE:
            continue
        clean = _strip_article(clean)
        if " and " in clean and len(clean.split()) > 3:
            parts2 = [p.strip() for p in clean.split(" and ")]
            if all(len(p.split()) <= 3 for p in parts2):
                for p in parts2:
                    if p and p not in seen and _is_valid_skill(p):
                        seen.add(p)
                        skill_names.append(p)
                continue
        if _is_valid_skill(clean) and clean not in seen:
            seen.add(clean)
            skill_names.append(clean)

    return skill_names


def _extract_paragraph_skills(text: str) -> list[str]:
    """
    Extract skills from a vague paragraph JD.
    Strategy: scan for known tech keywords explicitly.
    This is safer than trying to parse free-form sentences.
    """
    text_lower = text.lower()
    found = []
    seen_stems = set()

    for kw in sorted(_TECH_KEYWORDS, key=lambda x: -len(x)):
        if kw in text_lower:
            # Check it's not already covered by a longer keyword already added
            kw_stems = frozenset(_stem(t) for t in _tokenize(kw))
            if not kw_stems.issubset(seen_stems):
                found.append(kw)
                seen_stems.update(kw_stems)

    return found


def _deduplicate_skills(skills: list[str]) -> list[str]:
    """
    Remove redundant entries.
    'api' is redundant if 'web api' or 'rest api' is present.
    'apis' is a duplicate of 'api'.
    Shorter phrase removed if all its stems appear in a longer phrase's stems.
    """
    skills = list(dict.fromkeys(skills))  # preserve order, remove exact dupes
    stemmed = [frozenset(_stem(t) for t in _tokenize(s)) for s in skills]
    keep = []
    for i, (s, ss) in enumerate(zip(skills, stemmed)):
        # Remove if this skill's stems are a subset of any other skill's stems
        dominated = any(
            ss < stemmed[j] for j in range(len(skills)) if j != i  # strict subset
        )
        if not dominated:
            keep.append(s)
    return keep


# ─────────────────────────────────────────────
# MAIN SCORER
# ─────────────────────────────────────────────
def calculate_match_score(
    extracted_skills: list[str],
    extracted_education: str,
    extracted_experience: int,
    job_requirements: "Job",
    resume_text: str = "",
    job_description_text: str = "",
) -> float:
    """
    Weighted ensemble. Returns float in [0.0, 100.0].
    Always re-extracts job requirements fresh from JD text.
    Adapts weights based on whether the JD is structured or vague.
    """
    if not job_requirements:
        return 0.0

    jd_text = job_description_text or getattr(job_requirements, "job_description", "")

    # Always re-extract — never trust stale DB skills
    if jd_text:
        auto = auto_extract_job_requirements(
            job_description=jd_text,
            job_title=getattr(job_requirements, "job_title", "") or "",
        )
        job_requirements.skillname_skillweight_dict = auto["skills"]
        job_requirements.min_edu = auto["min_edu"]
        job_requirements.min_years_exp = auto["min_years_exp"]
        job_requirements.min_edu_weight = auto["min_edu_weight"]
        job_requirements.min_exp_weight = auto["min_exp_weight"]
        jd_structured = auto.get("jd_structured", True)
    else:
        jd_structured = True

    if not jd_text:
        jd_text = " ".join((job_requirements.skillname_skillweight_dict or {}).keys())

    has_text = bool(resume_text and jd_text)
    sbert_available = _get_sbert_model() is not None

    # ── Weights adapt to JD quality ───────────────────────────────────
    # Structured JD: skill matching is reliable → W_SEMANTIC=0.45
    # Vague JD:      text similarity + exp are the real signals → W_SEMANTIC=0.20
    if has_text and sbert_available:
        if jd_structured:
            W_SBERT = 0.10
            W_TFIDF = 0.08
            W_BM25 = 0.12
            W_SEMANTIC = 0.45
            W_EXP = 0.20
            W_EDU = 0.05
        else:
            W_SBERT = 0.15
            W_TFIDF = 0.15
            W_BM25 = 0.20
            W_SEMANTIC = 0.20
            W_EXP = 0.25
            W_EDU = 0.05
    elif has_text:
        if jd_structured:
            W_SBERT = 0.0
            W_TFIDF = 0.10
            W_BM25 = 0.15
            W_SEMANTIC = 0.45
            W_EXP = 0.25
            W_EDU = 0.05
        else:
            # Vague paragraph JD — text similarity + experience dominate
            W_SBERT = 0.0
            W_TFIDF = 0.20
            W_BM25 = 0.25
            W_SEMANTIC = 0.20
            W_EXP = 0.30
            W_EDU = 0.05
    else:
        W_SBERT = 0.0
        W_TFIDF = 0.0
        W_BM25 = 0.0
        W_SEMANTIC = 0.60
        W_EXP = 0.30
        W_EDU = 0.10

    total = 0.0

    if has_text:
        total += _tfidf_cosine(resume_text, jd_text) * W_TFIDF
        total += _bm25(jd_text, resume_text) * W_BM25

    job_skills = job_requirements.skillname_skillweight_dict or {}
    sem, matched, missing = _semantic_skill_score(
        resume_text if resume_text else " ".join(extracted_skills),
        job_skills,
    )
    total += sem * W_SEMANTIC

    if has_text and sbert_available:
        total += _sbert_cosine(resume_text, jd_text) * W_SBERT

    # Experience
    exp_w = job_requirements.min_exp_weight or 0
    if exp_w > 0:
        min_exp = job_requirements.min_years_exp or 0
        if min_exp <= 0:
            e = 1.0
        elif extracted_experience >= min_exp:
            e = min(1.0, 0.9 + (extracted_experience - min_exp) * 0.02)
        else:
            e = extracted_experience / min_exp
        total += e * W_EXP * (1 + exp_w / 100.0)

    # Education
    edu_w = job_requirements.min_edu_weight or 0
    if edu_w > 0:
        c_edu = EDUCATION_LEVELS.get(extracted_education.lower().strip(), 0)
        r_edu = EDUCATION_LEVELS.get(
            (job_requirements.min_edu or "none").lower().strip(), 0
        )
        edu_s = min(1.0, c_edu / r_edu) if r_edu > 0 else 1.0
        total += edu_s * W_EDU * (1 + edu_w / 100.0)

    return round(min(100.0, max(0.0, total * 100.0)), 1)


def get_skill_breakdown(
    resume_text: str,
    job_skill_dict: dict,
) -> tuple[list[str], list[str]]:
    _, matched, missing = _semantic_skill_score(resume_text, job_skill_dict)
    return matched, missing
