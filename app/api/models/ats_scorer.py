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
  3. spaCy NER Skill Match       — lemmatization + PhraseMatcher (any domain)
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
            "The other algorithms will still run normally."
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
    dot = float(vec_a @ vec_b)
    norm_a = float((vec_a**2).sum() ** 0.5)
    norm_b = float((vec_b**2).sum() ** 0.5)
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


# ──────────────────────────────────────────────
# ALGORITHM 3 — spaCy NER LOADER
# Same model already used by extractors.py (en_core_web_sm).
# Loaded once and reused for every request.
# ──────────────────────────────────────────────

_nlp = None  # cached spaCy model


def _get_nlp():
    """
    Lazy-loads the spaCy model on first use.
    Reuses 'en_core_web_sm' — already a project dependency (see extractors.py).
    Returns None if spaCy is not installed or model is missing.
    """
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy

        _nlp = spacy.load("en_core_web_sm")
    except ImportError:
        warnings.warn(
            "spaCy not installed. Algorithm 3 will fall back to basic text matching.\n"
            "Run: pip install spacy && python -m spacy download en_core_web_sm"
        )
        _nlp = None
    except OSError:
        warnings.warn(
            "spaCy model 'en_core_web_sm' not found. Algorithm 3 will fall back.\n"
            "Run: python -m spacy download en_core_web_sm"
        )
        _nlp = None
    return _nlp


# Education level map (same as your Utils.EDUCATION_WORDS)
EDUCATION_LEVELS: dict[str, int] = {
    "phd": 4,
    "doctorate": 4,
    "master": 3,
    "masters": 3,
    "bachelor": 2,
    "bachelors": 2,
    "highschool": 1,
    "high school": 1,
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


# ──────────────────────────────────────────────
# TEXT HELPERS
# ──────────────────────────────────────────────


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [t for t in text.split() if len(t) > 1 and t not in STOPWORDS]


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
    n1 = math.sqrt(sum(x**2 for x in v1.values()))
    n2 = math.sqrt(sum(x**2 for x in v2.values()))
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
# ALGORITHM 3 — spaCy NER SKILL MATCH
#
# HOW IT WORKS (replaces the old hardcoded SKILL_SYNONYMS graph):
#
# Step 1 — PhraseMatcher on LEMMA attribute
#   spaCy reduces every word to its base form (lemma) before matching.
#   This means:
#     "surgeries"  → lemma "surgery"   ✓ matches job skill "surgery"
#     "managing"   → lemma "manage"    ✓ matches job skill "management"
#     "algorithms" → lemma "algorithm" ✓ matches job skill "algorithm"
#   This works for ANY domain — medicine, law, finance, tech — with no
#   hardcoded lists because lemmatization is language-level, not domain-level.
#
# Step 2 — Token Overlap fallback (partial credit)
#   For multi-word skills that PhraseMatcher didn't catch exactly, we check
#   what fraction of the skill's lemma tokens appear anywhere in the resume.
#   Threshold: 60% overlap → counted as a match.
#   Example:
#     job skill:  "cardiothoracic surgery"  (2 tokens)
#     resume has: "surgery"                 (1/2 = 50% → miss)
#     resume has: "cardiothoracic surgery"  (2/2 = 100% → hit)
#     resume has: "cardiothoracic"          (1/2 = 50% → miss)
#
# Step 3 — Basic substring fallback (if spaCy is unavailable)
#   Falls back to simple lowercase substring matching, same behavior as
#   the old algorithm but without synonyms.
#
# DOMAIN EXAMPLES:
#   Tech resume:     "Python, PyTorch, Docker"    → works exactly as before
#   Medical resume:  "cardiology, CABG, ICU care" → now correctly matched
#   Legal resume:    "contract drafting, litigation, arbitration" → works
#   Finance resume:  "portfolio management, derivatives, hedging" → works
# ──────────────────────────────────────────────


def _semantic_skill_score(
    resume_text: str,
    job_skill_dict: dict[str, int],
) -> tuple[float, list[str], list[str]]:
    """
    For each required skill in the job, checks if it (or its lemmatized form)
    appears in the resume using spaCy's PhraseMatcher.

    No hardcoded synonym lists — works for any domain out of the box.

    Returns:
      - raw_score in [0, 1]
      - matched skill names
      - missing skill names
    """
    if not job_skill_dict:
        return 1.0, [], []

    nlp = _get_nlp()

    # ── spaCy unavailable: plain substring fallback ───────────────────
    if nlp is None:
        text_lower = resume_text.lower()
        matched = [s for s in job_skill_dict if s.lower() in text_lower]
        missing = [s for s in job_skill_dict if s not in matched]
        score = len(matched) / len(job_skill_dict)
        return score, matched, missing

    # ── Step 1: PhraseMatcher on LEMMA ───────────────────────────────
    # Build one matcher with all job skills as patterns.
    # LEMMA attribute means "surgery" pattern matches "surgeries" in text.
    from spacy.matcher import PhraseMatcher

    matcher = PhraseMatcher(nlp.vocab, attr="LEMMA")
    skill_docs: dict[str, object] = {}

    for skill in job_skill_dict:
        # Cap skill text length to avoid edge cases
        skill_doc = nlp(skill.lower()[:200])
        skill_docs[skill] = skill_doc
        matcher.add(skill, [skill_doc])

    # Process the resume (cap at 50k chars to avoid OOM on huge docs)
    resume_doc = nlp(resume_text.lower()[:50_000])

    # Collect every skill that was matched
    matched_ids = {
        nlp.vocab.strings[match_id] for match_id, _start, _end in matcher(resume_doc)
    }

    matched: list[str] = []
    unmatched: list[str] = []

    for skill in job_skill_dict:
        if skill in matched_ids:
            matched.append(skill)
        else:
            unmatched.append(skill)

    # ── Step 2: Token Overlap fallback for unmatched skills ───────────
    # Catches partial matches like "cardiac surgery" vs "cardiothoracic surgery".
    # Uses the full set of lemmatized, non-stop resume tokens for fast lookup.
    resume_lemma_set = {
        token.lemma_
        for token in resume_doc
        if not token.is_punct and not token.is_space and not token.is_stop
    }

    still_missing: list[str] = []
    for skill in unmatched:
        skill_doc = skill_docs[skill]
        skill_lemmas = {
            token.lemma_
            for token in skill_doc  # type: ignore
            if not token.is_punct and not token.is_space
        }
        if not skill_lemmas:
            still_missing.append(skill)
            continue

        overlap_ratio = len(skill_lemmas & resume_lemma_set) / len(skill_lemmas)

        # 60% of the skill's tokens appear in the resume → count as match
        if overlap_ratio >= 0.6:
            matched.append(skill)
        else:
            still_missing.append(skill)

    score = len(matched) / len(job_skill_dict)
    return score, matched, still_missing


# ──────────────────────────────────────────────
# AUTO-EXTRACTION ENGINE
# Reads a plain job description and returns everything
# calculate_match_score() needs — no user input required.
#
# HOW EACH FIELD IS DERIVED:
#
#  skills          — spaCy noun chunks filtered to genuine skill phrases only.
#                    Phrases containing digits, experience words, or education
#                    words are explicitly excluded so "5+ years", "a bachelor
#                    degree", and "an experience" never appear as skills.
#
#  min_years_exp   — Regex over patterns like "5+ years", "minimum 3 years",
#                    "at least 2 years of experience". Seniority-title fallback
#                    (senior → 5, junior → 1). Returns 0 if not found.
#
#  min_edu         — Scans for PhD/Master/Bachelor/diploma keywords.
#                    Returns "none" if education is not mentioned.
#
#  weights         — Fixed logical split that always sums to 100%:
#                      Skills:     60%  (split equally across extracted skills)
#                      Experience: 25%
#                      Education:  15%
#                    Urgency language ("required" / "preferred") shifts
#                    exp/edu weights ±5 points while keeping the total at 100%.
# ──────────────────────────────────────────────

# Words that disqualify a noun chunk from being treated as a skill.
_EXP_WORDS = {
    "year",
    "years",
    "experience",
    "exp",
    "month",
    "months",
    "minimum",
    "least",
    "require",
    "required",
    "background",
}
_EDU_WORDS = {
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
}
_GENERIC_WORDS = {
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
}
_DISQUALIFY = _EXP_WORDS | _EDU_WORDS | _GENERIC_WORDS
_HAS_DIGIT = re.compile(r"\d")


def _strip_article(phrase: str) -> str:
    """Remove leading articles that spaCy attaches to noun chunks."""
    for art in ("a ", "an ", "the "):
        if phrase.startswith(art):
            return phrase[len(art) :]
    return phrase


def _is_valid_skill_phrase(phrase: str) -> bool:
    """
    Returns True only if the phrase looks like a genuine skill/technology.
    Articles must be stripped BEFORE calling this function.
    """
    if _HAS_DIGIT.search(phrase):
        return False
    tokens = phrase.lower().split()
    if not tokens or len(phrase) <= 1:
        return False
    meaningful = [t for t in tokens if len(t) > 2]
    if meaningful and all(t in _DISQUALIFY for t in meaningful):
        return False
    return True


def auto_extract_job_requirements(
    job_description: str,
    job_title: str = "",
) -> dict:
    """
    Reads a plain-text job description and returns a dict with all
    fields needed to score candidates — no user input required.
    """
    text = (job_title + " " + job_description).strip()
    text_lower = text.lower()

    # ── Extract min_years_exp ─────────────────────────────────────────
    exp_patterns = [
        r"(\d+)\s*\+?\s*years?\s+of\s+experience",
        r"(\d+)\s*\+?\s*years?\s+experience",
        r"minimum\s+of\s+(\d+)\s+years?",
        r"minimum\s+(\d+)\s+years?",
        r"at\s+least\s+(\d+)\s+years?",
        r"experience\s*[:\-]\s*(\d+)\s*\+?\s*years?",
        r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:relevant\s+)?exp",
        r"(\d+)\s*[-\u2013]\s*\d+\s*years?",
        r"(\d+)\s*\+\s*years?",
    ]
    seniority_map = {
        "principal": 7,
        "staff": 6,
        "senior": 5,
        "lead": 5,
        "mid-level": 3,
        "mid level": 3,
        "intermediate": 3,
        "junior": 1,
        "entry level": 0,
        "entry-level": 0,
        "graduate": 0,
    }

    min_years_exp = 0
    for pattern in exp_patterns:
        m = re.search(pattern, text_lower)
        if m:
            try:
                min_years_exp = int(m.group(1))
                break
            except (ValueError, IndexError):
                continue

    if min_years_exp == 0:
        for keyword, years in seniority_map.items():
            if keyword in text_lower:
                min_years_exp = years
                break

    # ── Extract min_edu ───────────────────────────────────────────────
    edu_priority = [
        ("phd", 4),
        ("doctorate", 4),
        ("ph.d", 4),
        ("master", 3),
        ("msc", 3),
        ("m.sc", 3),
        ("mba", 3),
        ("bachelor", 2),
        ("bsc", 2),
        ("b.sc", 2),
        ("undergraduate", 2),
        ("degree", 2),
        ("diploma", 1),
        ("high school", 1),
        ("highschool", 1),
    ]
    min_edu = "none"
    best_edu_level = 0
    for keyword, level in edu_priority:
        if keyword in text_lower and level > best_edu_level:
            if keyword in ("msc", "m.sc", "mba"):
                min_edu = "master"
            elif keyword in ("bsc", "b.sc", "undergraduate", "degree"):
                min_edu = "bachelor"
            elif keyword in ("ph.d", "doctorate"):
                min_edu = "phd"
            else:
                min_edu = keyword
            best_edu_level = level

    # ── Urgency detection ─────────────────────────────────────────────
    high_urgency = ["required", "must have", "essential", "mandatory"]
    low_urgency = ["preferred", "nice to have", "bonus", "desirable"]

    def _is_high(kws):
        for s in re.split(r"[.;\n]", text_lower):
            if any(k in s for k in kws) and any(u in s for u in high_urgency):
                return True
        return False

    def _is_low(kws):
        for s in re.split(r"[.;\n]", text_lower):
            if any(k in s for k in kws) and any(u in s for u in low_urgency):
                return True
        return False

    base_exp = (
        30
        if _is_high(["experience", "years", "exp"])
        else (20 if _is_low(["experience", "years", "exp"]) else 25)
    )
    base_edu = (
        20
        if _is_high(["education", "degree", "bachelor", "master", "phd"])
        else (
            10 if _is_low(["education", "degree", "bachelor", "master", "phd"]) else 15
        )
    )
    skills_total = 100 - base_exp - base_edu
    min_exp_weight = base_exp
    min_edu_weight = base_edu

    # ── Extract skills ────────────────────────────────────────────────
    nlp = _get_nlp()
    skill_names: list[str] = []

    if nlp:
        doc = nlp(text[:50_000])
        candidates: set[str] = set()

        for chunk in doc.noun_chunks:
            # Strip determiner first — spaCy attaches "a/an/the" to chunks
            phrase = _strip_article(chunk.text.strip().lower())
            content_tokens = [
                t
                for t in chunk
                if not t.is_stop
                and not t.is_punct
                and t.text.lower() not in ("a", "an", "the")
            ]
            if (
                1 <= len(phrase.split()) <= 4
                and content_tokens
                and _is_valid_skill_phrase(phrase)
            ):
                candidates.add(phrase)

        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART", "LAW"):
                phrase = _strip_article(ent.text.strip().lower())
                if 1 <= len(phrase.split()) <= 4 and _is_valid_skill_phrase(phrase):
                    candidates.add(phrase)

        skill_names = sorted(candidates, key=lambda x: (-len(x.split()), x))[:30]

    else:
        # Fallback: token frequency approach — works on plain lowercase JDs
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.\-]{1,25}\b", text)
        seen: dict[str, int] = {}
        for t in tokens:
            tl = t.lower()
            if (
                tl not in STOPWORDS
                and tl not in _DISQUALIFY
                and not _HAS_DIGIT.search(tl)
                and len(tl) > 2
            ):
                seen[tl] = seen.get(tl, 0) + 1
        capitalised = {t.lower() for t in tokens if t[0].isupper() and len(t) > 2}
        skill_names = [
            w
            for w, count in sorted(seen.items(), key=lambda x: -x[1])
            if count > 1 or w in capitalised
        ][:30]

    # ── Assign skill weights ──────────────────────────────────────────
    num_skills = len(skill_names) or 1
    per_skill_weight = max(1, skills_total // num_skills)
    skill_name_weight = {name: per_skill_weight for name in skill_names}

    return {
        "skills": skill_name_weight,
        "min_edu": min_edu,
        "min_years_exp": min_years_exp,
        "min_edu_weight": min_edu_weight,
        "min_exp_weight": min_exp_weight,
    }


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
      3. spaCy NER skill match      (lemma-based, domain-agnostic)
      4. SBERT + cosine similarity  (deep semantic sentence embeddings)
      5. Experience score           (non-linear ratio)
      6. Education score            (ordinal level comparison)

    AUTO MODE: if the job has a description but no user-defined skill
    weights, auto_extract_job_requirements() fills everything in
    automatically — no user input needed.

    Returns: float in [0.0, 100.0]
    """

    if not job_requirements:
        return 0.0

    # ── Auto-fill missing job requirements from description ───────────
    # If the user did not define any skills/weights, extract them
    # automatically from the job description text.
    jd_text = job_description_text or getattr(job_requirements, "job_description", "")

    if not job_requirements.skillname_skillweight_dict and jd_text:
        auto = auto_extract_job_requirements(
            job_description=jd_text,
            job_title=job_requirements.job_title or "",
        )
        job_requirements.skillname_skillweight_dict = auto["skills"]
        if not job_requirements.min_edu or job_requirements.min_edu == "none":
            job_requirements.min_edu = auto["min_edu"]
        if not job_requirements.min_years_exp:
            job_requirements.min_years_exp = auto["min_years_exp"]
        if not job_requirements.min_edu_weight:
            job_requirements.min_edu_weight = auto["min_edu_weight"]
        if not job_requirements.min_exp_weight:
            job_requirements.min_exp_weight = auto["min_exp_weight"]

    # Use the job description as the JD text for text-based algorithms
    if not jd_text:
        jd_text = " ".join(job_requirements.skillname_skillweight_dict.keys())

    # ── Weights for the full ensemble ────────────────────────────────
    #
    #  With raw text:  all algorithms run
    #  Without text:   falls back to NER + exp + edu only
    #
    has_text = bool(resume_text and jd_text)
    sbert_available = _get_sbert_model() is not None
    spacy_available = _get_nlp() is not None

    if has_text and sbert_available:
        # Full mode — all algorithms active
        W_SBERT = 0.30  # Algorithm 4 — deep semantic understanding
        W_TFIDF = 0.15  # Algorithm 1 — keyword frequency
        W_BM25 = 0.10  # Algorithm 2 — probabilistic ranking
        W_SEMANTIC = 0.25  # Algorithm 3 — spaCy NER lemma match
        W_EXP = 0.12  # structured experience score
        W_EDU = 0.08  # structured education score
    elif has_text:
        # SBERT not installed — 4-algorithm mode
        W_SBERT = 0.0
        W_TFIDF = 0.20
        W_BM25 = 0.15
        W_SEMANTIC = 0.35
        W_EXP = 0.20
        W_EDU = 0.10
    else:
        # No raw text — NER + exp + edu only
        W_SBERT = 0.0
        W_TFIDF = 0.0
        W_BM25 = 0.0
        W_SEMANTIC = 0.55
        W_EXP = 0.30
        W_EDU = 0.15

    total_score = 0.0

    # ── Algorithm 1: TF-IDF Cosine Similarity ─────────────────────────
    if has_text:
        tfidf_score = _tfidf_cosine(resume_text, jd_text)
        total_score += tfidf_score * W_TFIDF

    # ── Algorithm 2: BM25 (Okapi) ─────────────────────────────────────
    if has_text:
        bm25_score = _bm25(jd_text, resume_text)
        total_score += bm25_score * W_BM25

    # ── Algorithm 3: spaCy NER Skill Match ────────────────────────────
    job_skills_dict = job_requirements.skillname_skillweight_dict or {}
    semantic_score, matched_skills, missing_skills = _semantic_skill_score(
        resume_text if resume_text else " ".join(extracted_skills),
        job_skills_dict,
    )
    total_score += semantic_score * W_SEMANTIC

    # ── Algorithm 4: SBERT + Cosine Similarity ────────────────────────
    if has_text and sbert_available:
        sbert_score = _sbert_cosine(resume_text, jd_text)
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
    required_edu = EDUCATION_LEVELS.get(
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
