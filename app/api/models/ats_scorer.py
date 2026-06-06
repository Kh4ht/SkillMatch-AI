"""
SkillMatch-AI — ATS Scoring Engine  (v3)
=========================================
app/api/models/ats_scorer.py

DESIGN PRINCIPLES
-----------------
1. No static keyword lists. Every algorithm is context-free.
2. TF-IDF and BM25 measure full-text similarity between CV and JD.
   They are only meaningful when the JD is a substantial paragraph (≥30 words).
   For short/skill-only JDs they produce misleading low scores because a CV
   with many unrelated words will always score low against a 2-word JD.
3. Skill matching is the primary signal. When a skill is found in the CV,
   it's a match — regardless of domain (basketball, Python, welding, etc.).
4. Weight allocation:
   - Total = 100%. Exp and Edu take their share. Rest goes to skills+text.
   - Text similarity (TF-IDF / BM25 / SBERT) only gets weight when JD is
     long enough to make them meaningful (≥30 words).
   - When JD is short or skills-only, semantic skill match gets all the weight.
5. Importance weighting: skills mentioned with "most importantly", "critical",
   "must have", "primarily", etc. get higher weights. Order also matters.
"""

import math
import re
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Job


# ─────────────────────────────────────────────
# SBERT (optional — graceful fallback)
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
    "phd": 4, "doctorate": 4,
    "master": 3, "masters": 3,
    "bachelor": 2, "bachelors": 2,
    "highschool": 1, "diploma": 1,
    "none": 0,
}

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "for", "to", "of",
    "with", "is", "are", "be", "have", "has", "been", "we", "our", "you",
    "i", "my", "it", "its", "this", "that", "as", "by", "from", "was",
    "were", "will", "can", "should", "must", "may", "not", "but", "if",
    "so", "do", "did", "who", "what", "how", "when", "where", "also",
    "than", "more", "some", "any", "all", "into", "over", "after",
    "about", "no", "just", "them", "then", "there", "these", "those",
    "would", "could", "both", "each",
}

# Words that are NOT skills on their own — used to strip noise from skill phrases
# e.g. "good basketball player" → strip "good" and "player" → core = "basketball"
# e.g. "skilled basketball player" → strip "skilled" and "player" → core = "basketball"
SKILL_QUALIFIER_NOISE = {
    "good", "great", "excellent", "strong", "solid", "proven", "advanced",
    "basic", "intermediate", "proficient", "expert", "experienced",
    "skilled", "skilled", "talented", "qualified", "certified", "trained",
    "competent", "capable", "dedicated", "passionate", "motivated",
    "familiarity", "ability", "skill", "knowledge", "understanding",
    "working", "hands-on", "player", "practitioner", "enthusiast",
    "lover", "fan", "using", "preferred", "required",
}

# These words make a full phrase NOT extractable as a skill
NOT_SKILL = {
    # Education / seniority
    "year", "years", "experience", "exp", "month", "months", "minimum",
    "background", "degree", "bachelor", "master", "phd", "doctorate",
    "diploma", "university", "college", "education", "school", "graduate",
    "undergraduate", "msc", "bsc", "mba",
    # Job roles / titles — should NOT be extracted as skills
    "team", "role", "position", "candidate", "applicant", "employer",
    "employee", "company", "opportunity", "environment", "culture",
    "benefit", "salary", "package", "office", "location",
    "responsibilities", "requirement", "requirements", "qualifications",
    "developer", "engineer", "manager", "designer", "analyst", "architect",
    "consultant", "specialist", "coordinator", "director", "intern",
    "lead", "head", "officer", "associate", "assistant", "senior",
    "junior", "mid", "entry", "programmer", "coder", "hacker",
    # Generic tech/business nouns that appear in JD boilerplate
    "solution", "solutions", "service", "services", "system", "systems",
    "platform", "product", "products", "technology", "technologies",
    "client", "clients", "project", "projects", "business", "member",
    "members", "software", "hardware", "application", "applications",
    "tool", "tools", "stack", "codebase", "repo", "repository",
    "feature", "features", "module", "modules", "component", "components",
    # JD filler words that spaCy tags as NOUN
    "following", "skill", "skills", "knowledge", "ability", "abilities",
    "understanding", "familiarity", "proficiency", "expertise",
    "list", "set", "area", "areas", "field", "fields", "domain",
    "level", "levels", "type", "types", "kind", "approach",
    "focus", "goal", "goals", "task", "tasks", "result", "results",
    "need", "needs", "plus", "bonus", "advantage", "thing", "things",
    "way", "ways", "time", "part", "parts", "point", "points",
    # Action/process verbs that leak as nouns
    "build", "maintain", "collaborate", "deliver", "join", "looking",
    "work", "ensure", "support", "help", "use", "using", "make",
    "create", "write", "develop", "manage", "design", "test",
    "deploy", "monitor", "review", "implement", "integrate",
    # Pronouns / generic subject words
    "someone", "anybody", "everyone", "person", "people", "individual",
    "candidate", "hire", "talent", "whoever", "anyone",
    # Generic verbs that appear as bare words in short JDs
    "knows", "know", "understand", "have", "get", "seek", "find",
    "want", "need", "require", "prefer", "expect", "offer",
    "bring", "show", "demonstrate", "possess", "hold",
    # Generic nouns that are NOT skills
    "boot", "hat", "hand", "foot", "back", "front", "side",
    "base", "core", "top", "bottom", "end", "start", "run",
    "fit", "match", "hire", "team", "culture", "growth",
    # Generic tech/infrastructure words that are NOT specific skills
    "backend", "frontend", "fullstack", "framework", "frameworks",
    "database", "databases", "cloud", "platform", "platforms",
    "pipeline", "pipelines", "environment", "environments",
    "language", "languages", "library", "libraries", "package", "packages",
    "interface", "interfaces", "protocol", "protocols", "pattern", "patterns",
    "architecture", "infrastructure", "integration", "integrations",
    "deployment", "deployments", "container", "containers",
    "queue", "cache", "storage", "network", "networking",
    # Filler words that sneak through
    "such", "plus", "also", "including", "include", "includes",
    "various", "related", "similar", "additional", "general",
    "strong", "solid", "good", "great", "excellent", "deep",
    "broad", "wide", "hand", "proficient", "comfortable",
    "rest", "restful", "soap", "crud",
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
_NOISE_PHRASES = {
    "similar languages", "similar tools", "equivalent", "or equivalent",
    "related field", "bonus", "advantage", "preferred", "nice to have",
}

# Phrases that signal HIGH importance for the next skill
_HIGH_IMPORTANCE_SIGNALS = re.compile(
    r"most\s+importantly|critical(?:ly)?|must.?have|essential(?:ly)?|"
    r"primarily|main(?:ly)?|key\s+skill|top\s+priority|above\s+all|"
    r"especially|particularly|specifically|notably",
    re.IGNORECASE,
)
# Phrases that signal LOW importance
_LOW_IMPORTANCE_SIGNALS = re.compile(
    r"nice\s+to\s+have|preferred|bonus|plus|desirable|optional|"
    r"advantageous|good\s+to\s+have|would\s+be\s+great",
    re.IGNORECASE,
)

# Colon-list detector: "skills : java, php, python" or "requirements: react, node"
# Only matches INLINE lists (items on same line as the keyword).
# Does NOT match when the colon is immediately followed by a newline
# (that indicates a section header like "Requirements:\n- Python\n").
_COLON_LIST_RE = re.compile(
    r"(?:skills?|requirements?|qualifications?|technologies?|tools?|"
    r"languages?|frameworks?|expertise|stack|proficiencies)"
    r"\s*:\s*(?!\s*\n)(.+?)(?:\n|$|[.] )",
    re.IGNORECASE,
)

# Prefix noise to strip from each list item before taking it as a skill
_ITEM_NOISE_PREFIX = re.compile(
    r"^(?:and\s+|or\s+|also\s+)",
    re.IGNORECASE,
)

# High-importance prefix ON an individual list item
_ITEM_HIGH_PREFIX = re.compile(
    r"^(?:most\s+importantly\s+|importantly\s+|critically\s+|"
    r"primarily\s+|mainly\s+|especially\s+|particularly\s+|"
    r"specifically\s+|above\s+all\s+|most\s+critical(?:ly)?\s+)",
    re.IGNORECASE,
)

# Low-importance prefix ON an individual list item
_ITEM_LOW_PREFIX = re.compile(
    r"^(?:preferably\s+|ideally\s+|optionally\s+|bonus(?:\s+if)?\s+|"
    r"nice\s+to\s+have[:\s]+|preferred[:\s]+)",
    re.IGNORECASE,
)

# Boundary pattern: truncate a colon-list item at the first exp/edu qualifier
# so "python with 5+ years of experience and a bachelor degree" -> "python"
_LIST_ITEM_BOUNDARY = re.compile(
    r"\s+(?=\d+\+?\s*years?|years?\s+of|of\s+experience|"
    r"with\s+\d|and\s+a\s+(?:bachelor|master|phd|degree)|"
    r"(?:bachelor|master|phd|doctorate|degree|diploma)\s)"
    r"|\s+(?:with\s+(?:a\s+)?(?:minimum|at\s+least)|"
    r"(?:minimum|at\s+least)\s+\d)",
    re.IGNORECASE,
)

# Words that are clearly NOT skills even as single tokens (adverbs, qualifiers etc.)
# Used in the regex fallback which has no POS tagging.
# With spaCy installed these are handled by POS filtering and this list is not needed.
_ADVERB_ADJECTIVE_NOISE = {
    # Adverbs
    "importantly", "primarily", "mainly", "especially", "particularly",
    "specifically", "notably", "critically", "essentially", "additionally",
    "generally", "typically", "ideally", "preferably", "optionally",
    "currently", "previously", "recently", "highly", "strongly", "deeply",
    "broadly", "widely", "well", "fast", "quickly", "easily", "directly",
    "effectively", "efficiently", "successfully", "properly", "correctly",
    "accurately", "actively", "closely", "clearly", "fully", "mostly",
    # Adjectives
    "ideal", "comfortable", "familiar", "passionate", "motivated", "dedicated",
    "most", "least", "more", "less", "very", "quite", "rather", "fairly",
    "new", "old", "big", "small", "large", "high", "low", "long", "short",
    "full", "open", "free", "real", "true", "false", "best", "great",
    "good", "nice", "key", "core", "main", "top", "next", "last", "other",
    "own", "able", "due", "clear", "basic", "simple", "complex", "modern",
    "relevant", "related", "similar", "equivalent", "various", "multiple",
    "different", "specific", "general", "common", "standard", "custom",
    "strong", "excellent", "outstanding", "exceptional", "solid", "proven",
    "hands", "cross", "cross-functional", "cross-platform", "end-to-end",
    # Verbs that spaCy catches but regex misses
    "worked", "working", "work", "proven", "demonstrated", "demonstrated",
    "comfortable", "familiar", "experienced", "gained", "acquired",
    # Misc leakers
    "pipeline", "pipelines", "workflow", "workflows", "process", "processes",
    "practice", "practices", "methodology", "methodologies", "approach",
    "coach", "coaching", "strategy", "strategies", "candidate", "candidates",
}


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
            return s[len(art):]
    return s


def _core_skill_tokens(skill: str) -> list[str]:
    """
    Strip qualifier noise from a skill phrase to get the actual skill words.
    "good basketball player" → ["basketball"]
    "machine learning"       → ["machine", "learning"]
    "python"                 → ["python"]
    """
    tokens = _tokenize(skill)
    core = [t for t in tokens if t not in SKILL_QUALIFIER_NOISE and len(t) >= 3]
    return core if core else tokens


# ─────────────────────────────────────────────
# ALGORITHM 1 — TF-IDF cosine similarity
# Only reliable for substantial text (≥30 words in JD).
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
# Only reliable for substantial text (≥30 words in JD).
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
# ALGORITHM 3 — SEMANTIC SKILL MATCH
# Context-free. Any skill from any domain.
# Uses core-token matching so qualifier noise doesn't prevent matching.
# ─────────────────────────────────────────────
# Common aliases: if JD says key, CV may say any of the values (or vice versa)
_SKILL_ALIASES: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript", "es6", "es2015"],
    "typescript": ["ts"],
    "python": ["py"],
    "machine learning": ["ml", "deep learning", "ai"],
    "artificial intelligence": ["ai", "machine learning", "ml"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres", "psql"],
    "mongodb": ["mongo"],
    "elasticsearch": ["elastic", "elk"],
    "continuous integration": ["ci", "cicd", "ci/cd"],
    "continuous delivery": ["cd", "cicd", "ci/cd"],
    "object oriented": ["oop", "object-oriented"],
    "user interface": ["ui"],
    "user experience": ["ux"],
    "application programming interface": ["api"],
    "representational state transfer": ["rest", "restful"],
    "structured query language": ["sql"],
    "version control": ["git", "svn", "vcs"],
}
# Reverse map: alias -> canonical
_ALIAS_REVERSE: dict[str, str] = {}
for _canon, _aliases in _SKILL_ALIASES.items():
    for _a in _aliases:
        _ALIAS_REVERSE[_a] = _canon


def _skill_in_text(skill: str, text_lower: str, resume_stems: set) -> bool:
    """
    Check if a skill (or its alias/core) exists in the resume.
    Uses word-boundary matching to prevent false positives like
    'java' matching inside 'javascript'.

    Tries in order:
      1. Full phrase with word boundaries
      2. Core tokens (noise stripped) — word-boundary match for each core token
      3. Known aliases with word boundaries
    """
    sl = skill.lower()

    def _wb_match(term: str, text: str) -> bool:
        """Word-boundary regex match — term must appear as a whole word."""
        try:
            return bool(re.search("\\b" + re.escape(term) + "\\b", text))
        except re.error:
            return term in text

    # 1. Full phrase word-boundary match
    if _wb_match(sl, text_lower):
        return True

    # 2. Core tokens — each core token must appear as a whole word
    core_tok = _core_skill_tokens(skill)
    for ct in core_tok:
        if _wb_match(ct, text_lower):
            return True
        # Also try stem
        if _stem(ct) in resume_stems:
            # Verify the stem match is not a false positive (stem is long enough)
            if len(_stem(ct)) >= 4:
                return True

    # 3. Alias lookup
    aliases = _SKILL_ALIASES.get(sl, [])
    for alias in aliases:
        if _wb_match(alias, text_lower):
            return True

    # 4. Reverse alias
    canonical = _ALIAS_REVERSE.get(sl)
    if canonical and _wb_match(canonical, text_lower):
        return True

    return False


def _semantic_skill_score(
    resume_text: str,
    job_skill_dict: dict,
) -> tuple[float, list[str], list[str]]:
    """
    Returns (weighted_ratio, matched_skills, missing_skills).
    weighted_ratio accounts for per-skill weights, not just count.
    If no skills required → (1.0, [], []).
    If all skills missing → (0.0, [], all_skills).
    """
    if not job_skill_dict:
        return 1.0, [], []

    total_weight = sum(job_skill_dict.values()) or len(job_skill_dict)
    text_lower = resume_text.lower()
    resume_stems = {_stem(t) for t in _tokenize(resume_text)}

    nlp = _get_nlp()

    if nlp:
        resume_doc = nlp(resume_text.lower()[:50_000])
        resume_lemmas = {
            t.lemma_ for t in resume_doc
            if not t.is_punct and not t.is_space and not t.is_stop
        }

    matched, missing = [], []

    for skill in job_skill_dict:
        # Use unified _skill_in_text which handles exact, core-token, and alias matching
        if _skill_in_text(skill, text_lower, resume_stems):
            matched.append(skill)
            continue

        # spaCy lemma match (bonus pass when spaCy is available)
        if nlp:
            core_tok = _core_skill_tokens(skill)
            core_lemmas = set()
            for ct in core_tok:
                core_doc = nlp(ct)
                for token in core_doc:
                    if not token.is_punct and not token.is_space:
                        core_lemmas.add(token.lemma_)
            if core_lemmas and core_lemmas & resume_lemmas:
                matched.append(skill)
                continue

        missing.append(skill)

    # Weighted ratio: sum(weights of matched) / total_weight
    matched_weight = sum(job_skill_dict.get(s, 1) for s in matched)
    ratio = matched_weight / total_weight if total_weight else 1.0
    return ratio, matched, missing


# ─────────────────────────────────────────────
# JD ANALYSIS HELPERS
# ─────────────────────────────────────────────
def _jd_is_structured(jd_text: str) -> bool:
    has_section = bool(_SECTION_RE.search(jd_text))
    has_bullets = bool(_BULLET_RE.search(jd_text))
    has_list = jd_text.count(",") >= 3 and any(
        len(part.split()) <= 4 for part in jd_text.split(",")
    )
    return has_section or has_bullets or has_list


def _jd_word_count(jd_text: str) -> int:
    return len(jd_text.split())


def _text_similarity_is_reliable(jd_text: str) -> bool:
    """
    TF-IDF, BM25, and SBERT are active whenever JD text is available.
    They produce meaningful score gaps even for very short JDs (3-5 words)
    because matching CVs score clearly higher than non-matching ones.
    The 30-word threshold was an arbitrary restriction — removed.
    """
    return len(jd_text.strip()) > 0


# ─────────────────────────────────────────────
# SMART IMPORTANCE WEIGHTING
#
# Detects linguistic signals to assign higher weights to critical skills
# and lower weights to optional ones.
#
# "skills: java, sql, and most importantly python"
#   → python gets ~2x weight of java/sql
#
# "must have: react. Preferred: angular"
#   → react high weight, angular low weight
# ─────────────────────────────────────────────
def _assign_importance_weights(
    skill_names: list[str],
    jd_text: str,
    base_pct: int,
    colon_importance: dict[str, float] | None = None,
) -> dict[str, int]:
    """
    Given skill names and the JD text, assign integer weights summing to base_pct.
    If colon_importance is provided (from _extract_colon_list_skills), those
    multipliers are used directly instead of re-scanning the text.
    Position also matters: earlier = slightly more weight.
    """
    if not skill_names:
        return {}

    n = len(skill_names)
    text_lower = jd_text.lower()

    # Compute a raw importance score for each skill
    raw = {}
    for i, skill in enumerate(skill_names):
        score = 1.0

        # Position bonus: first skill gets +20%, last gets 0
        position_bonus = (n - i) / n * 0.2
        score += position_bonus

        if colon_importance and skill in colon_importance:
            # Use the multiplier captured directly from the list item
            score *= colon_importance[skill]
        else:
            # Find the skill's location in the text
            skill_lower = skill.lower()
            core_tok = _core_skill_tokens(skill)
            search_term = core_tok[0] if core_tok else skill_lower
            pos = text_lower.find(search_term)

            if pos >= 0:
                # Look in 80 chars BEFORE the skill for high-importance signals
                ctx_before = text_lower[max(0, pos - 80):pos]
                ctx_around = text_lower[max(0, pos - 40):min(len(text_lower), pos + 40)]

                if _HIGH_IMPORTANCE_SIGNALS.search(ctx_before):
                    score *= 2.0
                if _LOW_IMPORTANCE_SIGNALS.search(ctx_around):
                    score *= 0.5
                if any(kw in ctx_before for kw in ["must have", "required", "essential", "mandatory"]):
                    score *= 1.5
                if any(kw in ctx_around for kw in ["preferred", "bonus", "optional", "nice to have"]):
                    score *= 0.6

        raw[skill] = score

    # Normalize raw scores to sum to base_pct (integer weights)
    total_raw = sum(raw.values())
    if total_raw == 0:
        # Fallback: equal distribution
        per = base_pct // n
        remainder = base_pct - per * n
        return {s: per + (remainder if i == 0 else 0) for i, s in enumerate(skill_names)}

    # Convert to integer weights
    float_weights = {s: (raw[s] / total_raw) * base_pct for s in skill_names}
    # Floor all, then distribute remainder to highest fractional parts
    floored = {s: int(w) for s, w in float_weights.items()}
    remainder = base_pct - sum(floored.values())
    fractions = sorted(skill_names, key=lambda s: -(float_weights[s] - floored[s]))
    for s in fractions[:remainder]:
        floored[s] += 1

    # Ensure minimum weight of 1 for each skill
    for s in skill_names:
        if floored[s] < 1:
            floored[s] = 1

    return floored


# ─────────────────────────────────────────────
# JD SKILL EXTRACTION — CONTEXT-FREE
# ─────────────────────────────────────────────
def auto_extract_job_requirements(
    job_description: str,
    job_title: str = "",
) -> dict:
    """
    Extracts skills, experience, education, and weights from a JD.
    - No static keyword list — any domain works.
    - Skills get importance-weighted based on JD language signals.
    """
    # Use full text (title + JD) for experience/education/weight detection
    # but use JD body ONLY for skill extraction — title words like "software engineer"
    # would otherwise leak "software" into the skill list.
    text = (job_title + "\n" + job_description).strip()
    text_lower = text.lower()
    jd_body = job_description.strip()  # skill extraction source

    # ── Experience ───────────────────────────────────────────────────
    exp_patterns = [
        r"(\d+)\s*\+\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        r"(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)",
        r"(?:minimum|min)\s*(?:of\s*)?\s*(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        r"at\s*least\s*(\d+)\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
        r"(\d+)\s*[-\u2013]\s*\d+\s*(?:(?:year|years|yr|yrs)\s*)?(?:of\s*)?(?:experience|exp)?",
    ]
    seniority = {
        "principal": 7, "staff": 6, "senior": 5, "lead": 5,
        "mid-level": 3, "intermediate": 3, "junior": 1,
        "entry level": 0, "entry-level": 0, "graduate": 0,
    }
    min_years_exp = 0
    for pat in exp_patterns:
        m = re.search(pat, text_lower)
        if m:
            try:
                min_years_exp = int(m.group(1))
                break
            except Exception:
                pass
    if not min_years_exp:
        for kw, yrs in seniority.items():
            if kw in text_lower:
                min_years_exp = yrs
                break

    # ── Education ────────────────────────────────────────────────────
    edu_map = [
        ("phd", 4), ("doctorate", 4), ("master", 3), ("msc", 3), ("mba", 3),
        ("bachelor", 2), ("bsc", 2), ("undergraduate", 2), ("degree", 2),
        ("diploma", 1), ("high school", 1),
    ]
    min_edu, best = "none", 0
    for kw, lvl in edu_map:
        if kw in text_lower and lvl > best:
            min_edu = {
                "msc": "master", "mba": "master",
                "bsc": "bachelor", "undergraduate": "bachelor",
            }.get(kw, kw)
            best = lvl

    # ── Urgency weights ──────────────────────────────────────────────
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

    exp_mentioned = any(k in text_lower for k in
        ["experience", "years", "year", "exp", "senior", "junior", "mid-level", "lead"])
    edu_mentioned = any(k in text_lower for k in
        ["education", "degree", "bachelor", "master", "phd", "diploma", "university"])

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

    # ── Context-free skill extraction (from JD body only, not title) ──
    #
    # Priority order:
    # 1. Structured (bullets/sections) — most reliable for formatted JDs
    # 2. Colon-list inline ("skills: java, php, python") — for informal JDs
    # 3. Free-form NLP / regex — for everything else
    #
    structured = _jd_is_structured(jd_body)

    if structured:
        # Bullet/section JD — parse structure directly, ignore colon-list
        skill_names = _extract_structured_skills(jd_body)
        skill_names = _deduplicate_skills(skill_names)[:20]
        skill_dict = _assign_importance_weights(skill_names, jd_body, skills_pct)
    else:
        # Try colon-list inline pattern first ("skills : java, php, python")
        colon_skills, colon_importance = _extract_colon_list_skills(jd_body)
        if colon_skills:
            skill_names = _deduplicate_skills(colon_skills)[:20]
            skill_dict = _assign_importance_weights(
                skill_names, jd_body, skills_pct, colon_importance
            )
        else:
            # Free-form: use spaCy noun chunks (or regex fallback)
            skill_names = _extract_contextfree_skills(jd_body)
            skill_names = _deduplicate_skills(skill_names)[:20]
            skill_dict = _assign_importance_weights(skill_names, jd_body, skills_pct)

    return {
        "skills": skill_dict,
        "min_edu": min_edu,
        "min_years_exp": min_years_exp,
        "min_edu_weight": base_edu,
        "min_exp_weight": base_exp,
        "jd_structured": structured,
        "jd_word_count": _jd_word_count(job_description),
    }


def _extract_colon_list_skills(jd_text: str) -> tuple[list[str], dict[str, float]]:
    """
    Highest-priority extraction: detects patterns like
      'skills : java , php , and most importantly python'
      'requirements: react, node.js, typescript'
    Returns (skill_names, importance_multipliers) where importance_multipliers
    maps skill name -> float multiplier (2.0=high, 0.5=low, 1.0=normal).
    Returns ([], {}) if no colon-list pattern found.
    """
    skill_names = []
    importance_multipliers = {}
    seen = set()

    for m in _COLON_LIST_RE.finditer(jd_text):
        raw_list = m.group(1).strip()
        # Split on commas and semicolons
        raw_items = re.split(r"[,;]", raw_list)
        for item in raw_items:
            item = item.strip()
            if not item:
                continue
            # Strip leading conjunctions
            item = _ITEM_NOISE_PREFIX.sub("", item).strip()
            # Detect and strip importance prefix, record multiplier
            mult = 1.0
            if _ITEM_HIGH_PREFIX.match(item):
                mult = 2.0
                item = _ITEM_HIGH_PREFIX.sub("", item).strip()
            elif _ITEM_LOW_PREFIX.match(item):
                mult = 0.5
                item = _ITEM_LOW_PREFIX.sub("", item).strip()
            # Truncate at exp/edu boundary so "python with 5+ years..." -> "python"
            bm = _LIST_ITEM_BOUNDARY.search(item)
            if bm:
                item = item[:bm.start()].strip()
            item = item.lower().strip()
            item = re.sub(r"[^a-z0-9\s#+.\-]", "", item).strip()
            if not item or item in seen:
                continue
            if not _is_valid_skill(item):
                continue
            seen.add(item)
            skill_names.append(item)
            importance_multipliers[item] = mult

    return skill_names, importance_multipliers


def _extract_structured_skills(jd_text: str) -> list[str]:
    """Extract skills from a structured JD (has Requirements section or bullets)."""
    sections = []
    matches = list(_SECTION_RE.finditer(jd_text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else start + 800
        sections.append(jd_text[start:end])
    section_text = "\n".join(sections) if sections else jd_text

    items = []
    for line in section_text.splitlines():
        # Strip ALL bullet variants: •, -, *, numbers, letters, unicode bullets
        clean = _BULLET_RE.sub("", line).strip()
        # Also strip any remaining leading punctuation that BULLET_RE missed
        clean = re.sub(r"^[\-\*•\u2013\u2014:]+\s*", "", clean).strip()
        if not clean or len(clean) < 2:
            continue
        parts = re.split(r"[,;]", clean) if ("," in clean or ";" in clean) else [clean]
        for part in parts:
            part = _BOILERPLATE.sub("", part.strip()).strip()
            if not part:
                continue
            for atom in re.split(r"\s*/\s*|\s+or\s+|\s*&\s*", part):
                atom = atom.strip()
                # Strip any residual leading punctuation on atoms too
                atom = re.sub(r"^[\-\*•:]+\s*", "", atom).strip()
                atom = atom.rstrip(".,;:")
                if atom:
                    items.append(atom)

    skill_names = []
    seen = set()
    for item in items:
        clean = re.sub(r"\s+", " ", item.lower())
        clean = re.sub(r"[^a-z0-9\s#+.\-]", "", clean).strip()
        if not clean or clean in seen or clean in _NOISE_PHRASES:
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


def _extract_contextfree_skills(text: str) -> list[str]:
    """
    Context-free skill extraction for paragraph / short JDs.
    
    WITH spaCy: uses POS tagging — only NOUN/PROPN tokens pass.
    This eliminates adjectives (ideal, comfortable), verbs (worked, ensure),
    and adverbs (importantly) automatically, with zero static word lists.
    
    WITHOUT spaCy: stricter regex fallback with larger blocklists.
    Will still have some leakage for uncommon words — install spaCy to fix.
    """
    nlp = _get_nlp()

    if nlp:
        doc = nlp(text[:10_000])
        skill_candidates = []
        seen = set()

        # Pass 1: noun chunks — best for multi-word skills like "machine learning"
        for chunk in doc.noun_chunks:
            # Use the root and its children, skip determiner heads
            if chunk.root.pos_ not in ("NOUN", "PROPN"):
                continue
            phrase = chunk.text.lower().strip()
            phrase = re.sub(r"[^a-z0-9\s#+.\-]", "", phrase).strip()
            phrase = _strip_article(phrase)
            phrase = _BOILERPLATE.sub("", phrase).strip()
            if not phrase or phrase in seen or phrase in _NOISE_PHRASES:
                continue
            if not _is_valid_skill(phrase):
                continue
            # Build the core (noise stripped) — if core is non-empty, store phrase
            core = _core_skill_tokens(phrase)
            if core:
                seen.add(phrase)
                # Also mark core tokens as seen to avoid redundant single-token entries
                for ct in core:
                    seen.add(ct)
                skill_candidates.append(phrase)

        # Pass 2: individual NOUN/PROPN tokens not already covered by a chunk
        for token in doc:
            if token.is_stop or token.is_punct or token.is_space:
                continue
            # CRITICAL: POS filter — this is what makes spaCy context-free.
            # ADJ (ideal, comfortable), VERB (worked, ensure), ADV (importantly)
            # are all excluded here automatically, no lists needed.
            if token.pos_ not in ("NOUN", "PROPN"):
                continue
            w = token.lemma_.lower().strip()
            w = re.sub(r"[^a-z0-9#+.\-]", "", w).strip()
            if not w or len(w) < 2 or w in seen:
                continue
            if w in NOT_SKILL or w in SKILL_QUALIFIER_NOISE:
                continue
            if _is_valid_skill(w):
                seen.add(w)
                skill_candidates.append(w)

        return skill_candidates

    # ── Regex fallback (no spaCy) ─────────────────────────────────────────
    # Without POS tagging we rely on blocklists — install spaCy for best results.
    _KNOWN_SHORT = {"js","ts","py","go","ml","ai","ui","ux","qa","sql","css",
                    "aws","gcp","api","git","php","ios","sdk","oop","mvc","tdd",
                    "bdd","nlp","ocr","etl","erp","crm","cms","cdn","jwt","orm",
                    "xml","csv","pdf","ssh","ssl","tcp","jvm","ide","r","c"}
    text_lower = text.lower()
    tokens = re.findall(r"[a-z][a-z0-9#.+\-]{1,29}", text_lower)
    seen = set()
    result = []
    for raw_t in tokens:
        t = raw_t.rstrip(".,;:")          # strip trailing punctuation
        if not t or len(t) < 2:
            continue
        if (t in STOPWORDS or t in NOT_SKILL or t in seen
                or t in SKILL_QUALIFIER_NOISE or t in _ADVERB_ADJECTIVE_NOISE):
            seen.add(t)
            continue
        if len(t) == 2 and t not in _KNOWN_SHORT:
            continue
        if t.endswith(("ful","ous","ive","ble","ical","ment","ness",
                        "ward","wise","ably","ibly","edly")) and len(t) > 6:
            continue
        seen.add(t)
        result.append(t)
    return result


def _deduplicate_skills(skills: list[str]) -> list[str]:
    skills = list(dict.fromkeys(skills))
    stemmed = [frozenset(_stem(t) for t in _tokenize(s)) for s in skills]
    keep = []
    for i, (s, ss) in enumerate(zip(skills, stemmed)):
        dominated = any(ss < stemmed[j] for j in range(len(skills)) if j != i)
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

    Weight allocation:
    - Exp + Edu take their share (based on JD signals).
    - Remaining goes to skills + text similarity.
    - TF-IDF / BM25 / SBERT only get weight when JD has ≥30 words.
      For short/skills-only JDs they are unreliable and get W=0.
    - Skill match always gets the bulk of the remaining weight.
    - If ALL required skills are missing → 0%.
    """
    if not job_requirements:
        return 0.0

    jd_text = job_description_text or getattr(job_requirements, "job_description", "")

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
        jd_word_count = auto.get("jd_word_count", _jd_word_count(jd_text))
    else:
        jd_word_count = 0

    if not jd_text:
        jd_text = " ".join((job_requirements.skillname_skillweight_dict or {}).keys())

    has_text = bool(resume_text and jd_text)
    text_reliable = _text_similarity_is_reliable(jd_text)  # ≥30 words
    sbert_available = has_text and _get_sbert_model() is not None

    job_skills = job_requirements.skillname_skillweight_dict or {}

    # ── Skill matching ───────────────────────────────────────────────
    if job_skills:
        sem_ratio, matched, missing = _semantic_skill_score(
            resume_text if resume_text else " ".join(extracted_skills),
            job_skills,
        )
        # NOTE: we no longer force 0% when skills are missing.
        # Education and experience still contribute their weighted share.
        # A CV with no matching skills but correct education/experience
        # will score low but not zero — which is fairer.
    else:
        sem_ratio = 1.0

    # ── Weight allocation ────────────────────────────────────────────
    #
    # Rule: TF-IDF / BM25 / SBERT only get weight when JD ≥ 30 words.
    # For short JDs (skills only, no context), semantic skill match is
    # the only reliable signal and gets all non-exp/edu weight.
    #
    # This ensures: JD="basketball player", CV has "Basketball" → 100%.
    #
    exp_w = job_requirements.min_exp_weight or 0
    edu_w = job_requirements.min_edu_weight or 0

    # Actual weights used in scoring (must sum to 1.0)
    if text_reliable and has_text:
        if sbert_available:
            W_SBERT = 0.10; W_TFIDF = 0.08; W_BM25 = 0.12
        else:
            W_SBERT = 0.0;  W_TFIDF = 0.12; W_BM25 = 0.18
        text_total = W_SBERT + W_TFIDF + W_BM25   # 0.30 with SBERT, 0.30 without
        # Remaining budget split between semantic and exp/edu
        budget = 1.0 - text_total                   # 0.70
        struct_share = min(0.35, (exp_w + edu_w) / 100.0) if (exp_w + edu_w) > 0 else 0.0
        W_EXP = struct_share * (exp_w / (exp_w + edu_w)) if exp_w else 0.0
        W_EDU = struct_share * (edu_w / (exp_w + edu_w)) if edu_w else 0.0
        W_SEMANTIC = budget - struct_share          # gets everything not taken by exp/edu
    else:
        # Short JD or no full text: semantic is the ONLY signal
        W_SBERT = 0.0; W_TFIDF = 0.0; W_BM25 = 0.0
        struct_total = exp_w + edu_w
        if struct_total > 0:
            struct_share = min(0.40, struct_total / 100.0)
            W_EXP = struct_share * (exp_w / struct_total) if exp_w else 0.0
            W_EDU = struct_share * (edu_w / struct_total) if edu_w else 0.0
        else:
            W_EXP = 0.0; W_EDU = 0.0
        W_SEMANTIC = 1.0 - W_EXP - W_EDU

    # ── Compute components ───────────────────────────────────────────
    total = 0.0

    total += sem_ratio * W_SEMANTIC

    if text_reliable and has_text:
        total += _tfidf_cosine(resume_text, jd_text) * W_TFIDF
        total += _bm25(jd_text, resume_text) * W_BM25
        if sbert_available:
            total += _sbert_cosine(resume_text, jd_text) * W_SBERT

    # Experience
    if W_EXP > 0 and exp_w > 0:
        min_exp = job_requirements.min_years_exp or 0
        if min_exp <= 0:
            e = 1.0
        elif extracted_experience >= min_exp:
            e = min(1.0, 0.9 + (extracted_experience - min_exp) * 0.02)
        else:
            e = extracted_experience / min_exp
        total += e * W_EXP

    # Education
    if W_EDU > 0 and edu_w > 0:
        c_edu = EDUCATION_LEVELS.get(extracted_education.lower().strip(), 0)
        r_edu = EDUCATION_LEVELS.get(
            (job_requirements.min_edu or "none").lower().strip(), 0
        )
        edu_s = min(1.0, c_edu / r_edu) if r_edu > 0 else 1.0
        total += edu_s * W_EDU

    return round(min(100.0, max(0.0, total * 100.0)), 1)


def get_skill_breakdown(
    resume_text: str,
    job_skill_dict: dict,
) -> tuple[list[str], list[str]]:
    _, matched, missing = _semantic_skill_score(resume_text, job_skill_dict)
    return matched, missing
