"""ATS Optimizer (Chapter 2: "Beat the robot").

97% of Fortune 500 companies screen resumes with software before a human sees
them. The playbook's three moves:

1. Mirror the job description's exact phrases in real bullets.
2. Spell out each acronym once — e.g. "Search Engine Optimization (SEO)".
3. Score the keyword match and aim for 75%+.

This module is deterministic — no LLM. It extracts the meaningful keywords and
phrases from a job description, checks which appear in the resume text, computes
a match score, and lists the highest-priority gaps and the acronyms to spell
out. It never edits the resume: it reports, and the honest fix (only add a
keyword where it truthfully describes your experience) stays with the candidate.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# Chapter 2: aim for a 75%+ keyword match.
TARGET_MATCH = 75.0

# Function words and resume/JD boilerplate that carry no matching signal.
_STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or but if then else for to of in on at by with from as is are was
    were be been being am do does did have has had having will would shall should
    can could may might must this that these those it its it's we you they he she
    i me my our your their them us who whom which what when where why how all any
    both each few more most other some such no nor not only own same so than too
    very s t just don now into out up down over under again further once about
    your you'll we're our ll re ve
    job role position candidate company team work working experience experiences
    years year ability able strong excellent good great help required requirements
    responsibilities responsible plus preferred nice qualifications skills skill
    including include includes etc using use used across within per via able
    looking seeking ideal opportunity opportunities new
    """.split()
)

# Token that allows tech-flavored names: c++, c#, node.js, ci/cd, a/b.
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-/]*")


class ATSReport(BaseModel):
    """The result of scoring a resume against a job description."""

    score: float = Field(..., description="Keyword match percentage, 0-100.")
    target: float = TARGET_MATCH
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(
        default_factory=list, description="JD keywords absent from the resume, "
        "highest-priority first."
    )
    acronyms_to_expand: list[str] = Field(
        default_factory=list, description="Acronyms in the JD to spell out once."
    )

    @property
    def target_met(self) -> bool:
        return self.score >= self.target

    @property
    def keyword_count(self) -> int:
        return len(self.matched) + len(self.missing)

    def to_markdown(self) -> str:
        status = "PASS" if self.target_met else "BELOW TARGET"
        lines = [
            "## ATS keyword match",
            f"**{self.score:.0f}% match** "
            f"({len(self.matched)}/{self.keyword_count} keywords) — "
            f"target {self.target:.0f}% — **{status}**",
        ]
        if self.missing:
            lines.append("\n**Top missing keywords** (add only where truthful):")
            lines += [f"- {kw}" for kw in self.missing[:15]]
        if self.acronyms_to_expand:
            lines.append("\n**Spell these acronyms out once** (e.g. \"… (ABC)\"):")
            lines.append(", ".join(self.acronyms_to_expand))
        return "\n".join(lines) + "\n"


def _tokenize(text: str) -> list[str]:
    # Strip surrounding ./-/ punctuation (e.g. "kubernetes." -> "kubernetes")
    # while preserving internal ones ("node.js", "ci/cd") and trailing #/+
    # ("c#", "c++").
    cleaned = (tok.strip("./-") for tok in _WORD_RE.findall(text))
    return [tok for tok in cleaned if tok]


def _is_content(token: str) -> bool:
    return len(token) >= 2 and token.lower() not in _STOPWORDS


def extract_keywords(text: str) -> dict[str, int]:
    """Extract content unigrams and bigrams with their JD frequency.

    Returns a mapping of lowercased keyword -> count. Bigrams are adjacent
    content words (stopwords break a bigram), which is how multi-word phrases
    like "stakeholder management" or "machine learning" get captured.
    """
    tokens = _tokenize(text)
    counts: dict[str, int] = {}

    # Unigrams.
    for tok in tokens:
        if _is_content(tok):
            key = tok.lower()
            counts[key] = counts.get(key, 0) + 1

    # Bigrams of adjacent content words.
    for a, b in zip(tokens, tokens[1:]):
        if _is_content(a) and _is_content(b):
            key = f"{a.lower()} {b.lower()}"
            counts[key] = counts.get(key, 0) + 1

    return counts


def extract_acronyms(text: str) -> list[str]:
    """All-caps tokens of 2-5 letters (SEO, ATS, ML, SQL, API), de-duplicated."""
    seen: dict[str, None] = {}
    for tok in _tokenize(text):
        if 2 <= len(tok) <= 5 and tok.isupper() and tok.isalpha():
            seen.setdefault(tok, None)
    return list(seen)


def _contains(haystack_lower: str, term_lower: str) -> bool:
    """Whole-word/phrase containment, with a substring fallback for terms that
    include non-word characters (e.g. 'c++', 'ci/cd')."""
    if re.search(r"[^\w ]", term_lower):
        return term_lower in haystack_lower
    return re.search(rf"\b{re.escape(term_lower)}\b", haystack_lower) is not None


def score_text(resume_text: str, job_description: str) -> ATSReport:
    """Score how well a resume's text matches a job description's keywords."""
    keywords = extract_keywords(job_description)
    resume_lower = resume_text.lower()

    matched: list[str] = []
    missing: list[str] = []
    for kw, count in sorted(keywords.items(), key=lambda kv: (-kv[1], kv[0])):
        (matched if _contains(resume_lower, kw) else missing).append(kw)

    total = len(keywords)
    score = 100.0 * len(matched) / total if total else 100.0

    acronyms_to_expand = [
        a for a in extract_acronyms(job_description) if f"({a})" not in resume_text
    ]

    return ATSReport(
        score=round(score, 1),
        matched=matched,
        missing=missing,
        acronyms_to_expand=acronyms_to_expand,
    )


def score_resume(resume, job_description: str) -> ATSReport:
    """Score a structured :class:`Resume` against a job description.

    Accepts the ``Resume`` object from the assembler; renders it to text first.
    """
    return score_text(resume.to_markdown(), job_description)
