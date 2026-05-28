"""
SkillMatch-AI — ATS Scoring Engine
====================================
Drop this file into:  app/api/models/ats_scorer.py

This plugs directly into your existing pipeline.
It REPLACES only Utils.calculate_match_score().
Everything else (Extractors, Database, Flask routes) stays untouched.

Algorithms used:
  1. TF-IDF + Cosine Similarity  — keyword frequency vectors
  2. BM25 (Okapi)                — probabilistic relevance ranking
  3. Semantic NER                — synonym-aware skill graph
  4. SBERT + Cosine Similarity   — deep semantic sentence embeddings
  5. Weighted Ensemble           — combines all signals + your job weights
"""

import math
import re
import warnings
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Job


# ──────────────────────────────────────────────
# ALGORITHM 4 — SBERT LOADER
# Loads once when the app starts, reused for every request.
# Falls back gracefully if sentence-transformers is not installed.
# ──────────────────────────────────────────────

_sbert_model = None  # cached model — loaded only once

def _get_sbert_model():
    """
    Lazy-loads the SBERT model on first use.
    Uses 'all-MiniLM-L6-v2' — small (80MB), fast, and accurate.
    Returns None if sentence-transformers is not installed.
    """
    global _sbert_model
    if _sbert_model is not None:
        return _sbert_model
    try:
        from sentence_transformers import SentenceTransformer
        _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        warnings.warn(
            "sentence-transformers not installed. SBERT disabled.\n"
            "Run: pip install sentence-transformers\n"
            "The other 4 algorithms will still run normally."
        )
        _sbert_model = None
    return _sbert_model


def _sbert_cosine(resume_text: str, job_text: str) -> float:
    """
    Encodes resume and job description into 384-dimensional vectors
    using SBERT (all-MiniLM-L6-v2), then returns cosine similarity.

    Example:
      resume: "Python developer with ML experience"
      job:    "Looking for an AI engineer who knows Python"
      → high similarity because SBERT understands they mean the same thing

    Returns float in [0, 1], or 0.0 if SBERT is unavailable.
    """
    model = _get_sbert_model()
    if model is None:
        return 0.0

    # Truncate to 512 tokens max (SBERT limit) — take first 1000 chars as proxy
    r = resume_text[:1000]
    j = job_text[:1000]

    embeddings = model.encode([r, j], convert_to_numpy=True)

    # Manual cosine similarity (avoids needing sklearn)
    vec_a, vec_b = embeddings[0], embeddings[1]
    dot    = float(vec_a @ vec_b)
    norm_a = float((vec_a ** 2).sum() ** 0.5)
    norm_b = float((vec_b ** 2).sum() ** 0.5)
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ──────────────────────────────────────────────
# SKILL SYNONYM GRAPH
# Maps canonical skill names → list of aliases
# ──────────────────────────────────────────────
SKILL_SYNONYMS: dict[str, list[str]] = {
    "python":           ["python", "python3", "py"],
    "java":             ["java", "spring boot", "jvm"],
    "c++":              ["c++", "cpp", "c plus plus"],
    "javascript":       ["javascript", "js", "typescript", "ts", "node.js", "nodejs"],
    "sql":              ["sql", "mysql", "postgresql", "sqlite", "database"],
    "machine learning": ["machine learning", "ml", "statistical learning"],
    "deep learning":    ["deep learning", "dl", "neural network", "neural networks"],
    "tensorflow":       ["tensorflow", "tf", "keras"],
    "pytorch":          ["pytorch", "torch"],
    "nlp":              ["nlp", "natural language processing", "text classification", "text mining"],
    "computer vision":  ["computer vision", "cv", "image recognition", "object detection"],
    "data analysis":    ["data analysis", "data analytics", "data science", "pandas", "numpy"],
    "power bi":         ["power bi", "powerbi", "tableau", "data visualization"],
    "excel":            ["excel", "spreadsheet", "google sheets"],
    "docker":           ["docker", "containerization", "container"],
    "kubernetes":       ["kubernetes", "k8s"],
    "aws":              ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "azure":            ["azure", "microsoft azure"],
    "git":              ["git", "github", "gitlab", "version control"],
    "rest api":         ["rest api", "restful", "api", "fastapi", "flask"],
    "agile":            ["agile", "scrum", "kanban", "sprint"],
    "react":            ["react", "reactjs", "react.js"],
    "spark":            ["spark", "apache spark", "pyspark"],
    "statistics":       ["statistics", "statistical", "probability", "regression"],
    "scikit-learn":     ["scikit-learn", "sklearn"],
}

# Education level map (same as your Utils.EDUCATION_WORDS)
EDUCATION_LEVELS: dict[str, int] = {
    "phd": 4, "doctorate": 4,
    "master": 3, "masters": 3,
    "bachelor": 2, "bachelors": 2,
    "highschool": 1, "high school": 1, "diploma": 1,
    "none": 0,
}

STOPWORDS = {
    'a','an','the','and','or','in','on','at','for','to','of','with','is','are',
    'be','have','has','been','we','our','you','i','my','it','its','this','that',
    'as','by','from','was','were','will','can','should','must','may','not','but',
    'if','so','do','did','who','what','how','when','where','also','than','more',
    'some','any','all','into','over','after','about','no','just','them','then',
    'there','these','those','would','could','both','each',
}


# ──────────────────────────────────────────────
# TEXT HELPERS
# ──────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return [t for t in text.split() if len(t) > 1 and t not in STOPWORDS]


def _skill_in_text(skill: str, text_lower: str) -> bool:
    """Check if a skill (or any of its synonyms) appears in the text."""
    aliases = SKILL_SYNONYMS.get(skill.lower(), [skill.lower()])
    return any(alias in text_lower for alias in aliases)


# ──────────────────────────────────────────────
# ALGORITHM 1 — TF-IDF COSINE SIMILARITY
# ──────────────────────────────────────────────

def _tfidf_cosine(resume_text: str, job_text: str) -> float:
    """
    Builds TF-IDF vectors for resume and job description,
    then returns their cosine similarity in [0, 1].
    """
    corpus = [resume_text, job_text]
    tokenized = [_tokenize(d) for d in corpus]
    vocab = set(t for doc in tokenized for t in doc)
    N = len(corpus)

    def vec(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        total = len(tokens) or 1
        v = {}
        for term in vocab:
            tf_val = tf.get(term, 0) / total
            df = sum(1 for doc in tokenized if term in doc)
            idf = math.log((N + 1) / (df + 1)) + 1
            v[term] = tf_val * idf
        return v

    v1 = vec(tokenized[0])
    v2 = vec(tokenized[1])

    dot = sum(v1.get(k, 0) * v2.get(k, 0) for k in vocab)
    n1 = math.sqrt(sum(x ** 2 for x in v1.values()))
    n2 = math.sqrt(sum(x ** 2 for x in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


# ──────────────────────────────────────────────
# ALGORITHM 2 — BM25 (Okapi)
# ──────────────────────────────────────────────

def _bm25(query_text: str, doc_text: str, k1: float = 1.5, b: float = 0.75) -> float:
    """
    Scores doc_text against query_text using Okapi BM25.
    Uses a 2-document corpus (query as one doc, resume as the other).
    Returns a normalized score in [0, 1].
    """
    corpus = [query_text, doc_text]
    tokenized_corpus = [_tokenize(d) for d in corpus]
    q_tokens = _tokenize(query_text)
    d_tokens = _tokenize(doc_text)

    avg_dl = sum(len(d) for d in tokenized_corpus) / len(tokenized_corpus)
    d_len = len(d_tokens)
    N = len(tokenized_corpus)
    d_tf = Counter(d_tokens)

    score = 0.0
    for term in q_tokens:
        df = sum(1 for d in tokenized_corpus if term in d)
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        tf = d_tf.get(term, 0)
        numerator = tf * (k1 + 1)
        denominator = tf + k1 * (1 - b + b * d_len / avg_dl)
        score += idf * (numerator / denominator)

    max_possible = len(q_tokens) * math.log(N + 1)
    return min(score / max_possible, 1.0) if max_possible > 0 else 0.0


# ──────────────────────────────────────────────
# ALGORITHM 3 — SEMANTIC SKILL SIMILARITY
# ──────────────────────────────────────────────

def _semantic_skill_score(
    resume_text: str,
    job_skill_dict: dict[str, int],
) -> tuple[float, list[str], list[str]]:
    """
    For each required skill in the job, checks if it (or a semantic synonym)
    appears in the resume text. Returns:
      - raw_score in [0, 1]
      - matched skill names
      - missing skill names
    """
    if not job_skill_dict:
        return 1.0, [], []

    text_lower = resume_text.lower()
    matched, missing = [], []

    for skill in job_skill_dict:
        if _skill_in_text(skill, text_lower):
            matched.append(skill)
        else:
            missing.append(skill)

    score = len(matched) / len(job_skill_dict)
    return score, matched, missing


# ──────────────────────────────────────────────
# MAIN SCORER — drop-in replacement for Utils.calculate_match_score
# ──────────────────────────────────────────────

def calculate_match_score(
    extracted_skills: list[str],
    extracted_education: str,
    extracted_experience: int,
    job_requirements: "Job",
    resume_text: str = "",
    job_description_text: str = "",
) -> float:
    """
    Advanced ATS scoring engine — weighted ensemble of:
      1. TF-IDF cosine similarity   (text-level keyword alignment)
      2. BM25 relevance score       (probabilistic term ranking)
      3. Semantic skill match       (synonym-aware NER skill graph)
      4. Experience score           (non-linear ratio)
      5. Education score            (ordinal level comparison)

    Fully backward-compatible with your existing pipeline:
      - Works with only (extracted_skills, extracted_education,
        extracted_experience, job_requirements) — same as before.
      - Optionally pass resume_text + job_description_text to activate
        TF-IDF and BM25 (recommended for better accuracy).

    Returns: float in [0.0, 100.0]  (same as before)
    """

    if not job_requirements:
        return 0.0

    # ── Weights for the full 5-algorithm ensemble ─────────────────────
    #
    #  With raw text:  all 5 algorithms run
    #  Without text:   falls back to NER + exp + edu only
    #
    has_text = bool(resume_text and job_description_text)
    sbert_available = _get_sbert_model() is not None

    if has_text and sbert_available:
        # Full 5-algorithm mode
        W_SBERT    = 0.30   # Algorithm 4 — deep semantic understanding
        W_TFIDF    = 0.15   # Algorithm 1 — keyword frequency
        W_BM25     = 0.10   # Algorithm 2 — probabilistic ranking
        W_SEMANTIC = 0.25   # Algorithm 3 — synonym-aware NER
        W_EXP      = 0.12   # structured experience score
        W_EDU      = 0.08   # structured education score
    elif has_text:
        # SBERT not installed — 4-algorithm mode
        W_SBERT    = 0.0
        W_TFIDF    = 0.20
        W_BM25     = 0.15
        W_SEMANTIC = 0.35
        W_EXP      = 0.20
        W_EDU      = 0.10
    else:
        # No raw text — 3-algorithm fallback
        W_SBERT    = 0.0
        W_TFIDF    = 0.0
        W_BM25     = 0.0
        W_SEMANTIC = 0.55
        W_EXP      = 0.30
        W_EDU      = 0.15

    total_score = 0.0

    # ── Algorithm 1: TF-IDF Cosine Similarity ─────────────────────────
    # Converts resume + JD into keyword frequency vectors,
    # measures how aligned they are via cosine similarity.
    if has_text:
        tfidf_score = _tfidf_cosine(resume_text, job_description_text)
        total_score += tfidf_score * W_TFIDF

    # ── Algorithm 2: BM25 (Okapi) ─────────────────────────────────────
    # Probabilistic ranking — smarter than TF-IDF because it uses
    # a saturation function so repeating keywords doesn't inflate score.
    if has_text:
        bm25_score = _bm25(job_description_text, resume_text)
        total_score += bm25_score * W_BM25

    # ── Algorithm 3: Semantic NER Skill Match ─────────────────────────
    # Checks each required skill using a synonym graph:
    # "torch" matches "PyTorch", "ml" matches "machine learning", etc.
    job_skills_dict = job_requirements.skillname_skillweight_dict or {}
    semantic_score, matched_skills, missing_skills = _semantic_skill_score(
        resume_text if resume_text else " ".join(extracted_skills),
        job_skills_dict,
    )
    total_score += semantic_score * W_SEMANTIC

    # ── Algorithm 4: SBERT + Cosine Similarity ────────────────────────
    # Encodes both texts into 384-dimensional sentence embeddings
    # using a pre-trained transformer (all-MiniLM-L6-v2).
    # Understands meaning — "AI engineer" ≈ "ML developer" even with
    # zero keyword overlap.
    if has_text and sbert_available:
        sbert_score = _sbert_cosine(resume_text, job_description_text)
        total_score += sbert_score * W_SBERT

    # ── Experience Score ──────────────────────────────────────────────
    # Non-linear: partial credit for close experience,
    # small bonus for exceeding the requirement.
    min_exp = job_requirements.min_years_exp or 0
    if min_exp <= 0:
        exp_score = 1.0
    elif extracted_experience >= min_exp:
        exp_score = min(1.0, 0.9 + (extracted_experience - min_exp) * 0.02)
    else:
        exp_score = extracted_experience / min_exp

    exp_weight_factor = (job_requirements.min_exp_weight or 20) / 100.0
    total_score += exp_score * W_EXP * (1 + exp_weight_factor)

    # ── Education Score ───────────────────────────────────────────────
    # Ordinal comparison: PhD > Master > Bachelor > Diploma
    candidate_edu = EDUCATION_LEVELS.get(extracted_education.lower().strip(), 0)
    required_edu  = EDUCATION_LEVELS.get(
        (job_requirements.min_edu or "none").lower().strip(), 0
    )
    edu_score = min(1.0, candidate_edu / required_edu) if required_edu > 0 else 1.0

    edu_weight_factor = (job_requirements.min_edu_weight or 10) / 100.0
    total_score += edu_score * W_EDU * (1 + edu_weight_factor)

    # ── Normalize to 0–100 and clamp ─────────────────────────────────
    final = total_score * 100.0
    return round(min(100.0, max(0.0, final)), 1)


# ──────────────────────────────────────────────
# HELPER — get matched/missing skills for display
# ──────────────────────────────────────────────

def get_skill_breakdown(
    resume_text: str,
    job_skill_dict: dict[str, int],
) -> tuple[list[str], list[str]]:
    """
    Returns (matched_skills, missing_skills) for a resume vs job.
    Useful for showing detailed feedback in your UI.
    """
    _, matched, missing = _semantic_skill_score(resume_text, job_skill_dict)
    return matched, missing
