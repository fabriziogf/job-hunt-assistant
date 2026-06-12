"""Playbook loader — serves the relevant *Apply Within* principles to each skill.

The source PDF (Laszlo Bock's *Apply Within*) is copyrighted and is **not**
shipped with this repo. What lives here instead is a distilled, paraphrased set
of the actionable rules from each chapter — the structured guidance a skill
injects into its prompts so its advice stays grounded in the playbook and can
cite the chapter it came from, rather than relying on generic LLM intuition.

Usage::

    from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill

    PLAYBOOK.chapter(2).core_principle
    PLAYBOOK.for_skill(AgentSkill.RESUME_BUILDER)      # -> list[ChapterPrinciples]
    print(PLAYBOOK.as_prompt(AgentSkill.RESUME_BUILDER))  # -> text block for a prompt
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AgentSkill(str, Enum):
    """The agent's skills. Each maps to one or more playbook chapters."""

    RESUME_BUILDER = "resume_builder"
    ATS_OPTIMIZER = "ats_optimizer"
    COVER_LETTER = "cover_letter"
    NETWORKING = "networking"
    INTERVIEW_PREP = "interview_prep"
    PIPELINE_TRACKER = "pipeline_tracker"
    NEGOTIATION = "negotiation"


class ChapterPrinciples(BaseModel):
    """The distilled, paraphrased guidance for one chapter."""

    number: int
    title: str
    core_principle: str
    rules: list[str] = Field(default_factory=list)
    # Memorable formulas / templates (e.g. the X/Y/Z resume formula).
    formulas: list[str] = Field(default_factory=list)
    # Stats worth grounding advice in (e.g. "referrals get hired 5-10x more").
    stats: list[str] = Field(default_factory=list)

    def as_prompt(self) -> str:
        """Render this chapter as a text block suitable for a system prompt."""
        lines = [f"## Chapter {self.number}: {self.title}", self.core_principle, ""]
        if self.formulas:
            lines.append("Key formulas / templates:")
            lines += [f"- {f}" for f in self.formulas]
            lines.append("")
        if self.rules:
            lines.append("Rules:")
            lines += [f"- {r}" for r in self.rules]
            lines.append("")
        if self.stats:
            lines.append("Grounding stats:")
            lines += [f"- {s}" for s in self.stats]
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


# --- The distilled playbook (paraphrased from Apply Within) -------------------

_CHAPTERS: dict[int, ChapterPrinciples] = {
    1: ChapterPrinciples(
        number=1,
        title="Hiring is rigged",
        core_principle=(
            "Hiring isn't about finding the best person; it's a tired manager "
            "picking someone who feels familiar, fast. You don't need to be the "
            "best — you need to know how the game is played."
        ),
        rules=[
            "Most interview decisions are made in the first ~4 minutes, then "
            "justified afterward.",
            "The real question an interviewer answers is 'Did I like them?', not "
            "'Are they the most qualified?'.",
        ],
        stats=[
            "30M+ resumes sifted and 100K+ applicants reviewed inform this advice.",
        ],
    ),
    2: ChapterPrinciples(
        number=2,
        title="Your resume in one formula",
        core_principle=(
            "Resumes fail because they list duties, not results. A recruiter "
            "spends ~6 seconds per resume; numbers communicate, vague duties "
            "don't."
        ),
        formulas=[
            "Accomplished [X] as measured by [Y] by doing [Z] — X = what you "
            "achieved, Y = how it's measured (numbers, %, $, time), Z = how you "
            "did it.",
        ],
        rules=[
            "Save as PDF (other formats get mangled by recruiting software).",
            "11pt minimum font size.",
            "1/2-inch margins.",
            "No tables or columns (ATS software breaks them).",
            "Contact info on every page.",
            "Length: one page per decade of experience (<10 yrs -> 1 page).",
            "Find typos by reading bottom-up, then have a friend do the same.",
            "Name-drop recognizable brands — recruiters search databases by "
            "company name.",
            "Include a GPA only if 3.5+ or top 10%; it's OK to slice ('3.7 in my "
            "major') if you disclose it. Below 3.5, leave it off.",
            "Describe what awards were for; a bare trophy name doesn't help.",
            "Hardship rule: hardships help college admission but hurt job "
            "applications. Exceptions worth noting: self-financed 1/3+ of "
            "education, worked during school, first in family to attend.",
            "Never lie or stretch — people get fired for resume lies.",
        ],
        stats=[
            "58% of resumes have typos; recruiters use them as a fast reject "
            "filter (250+ applications per role).",
        ],
    ),
    3: ChapterPrinciples(
        number=3,
        title="The cover letter trap",
        core_principle=(
            "You can't win a job with a cover letter, but you can lose one. Its "
            "job is defense: first, do no harm. Your outbound prospecting email "
            "is the modern cover letter — the same principles apply."
        ),
        formulas=[
            "Four paragraphs: (1) introduce yourself in one sentence + any "
            "connection/referral; (2) expand, 3 sentences max, don't repeat the "
            "resume; (3) why you, specifically — reference something specific to "
            "this company (recent product, statement, news); (4) promise to "
            "follow up.",
        ],
        rules=[
            "Use the real hiring manager's name; 'Dear Hiring Manager' is ~30% "
            "more likely to be rejected.",
            "Triple-check the company name — never copy-paste the wrong one.",
            "Customize every time; paragraph 3 is the only one that proves you "
            "researched the company.",
            "If you have a referral, name them in sentence one.",
            "Read it once out loud before sending to catch typos and AI "
            "hallucinations.",
            "Spend no more than 30 minutes; put the saved time into the resume, "
            "network, and interview practice.",
        ],
    ),
    4: ChapterPrinciples(
        number=4,
        title="Networking without a network",
        core_principle=(
            "You don't need a connection — you need a connection to a connection. "
            "Ask for advice, not a job: the moment you ask for a job you become a "
            "problem to solve and people step away."
        ),
        formulas=[
            "Five advice questions: (1) How did you get your job? (2) What advice "
            "for someone trying to get into your field/company? (3) What parts of "
            "your company are hiring? (4) Could you refer me to the recruiter? "
            "(5) Who else could give me advice?",
            "Outreach: open with a genuine 'coincidence' ('I noticed...'), say "
            "you're exploring a move into their field, ask for a 15-minute call "
            "for advice.",
        ],
        rules=[
            "'I noticed...' beats 'You don't know me, but...' every time.",
            "Meeting etiquette: show up prepared, end on time (15 min -> end at "
            "14), ask 2 specific questions, send a thank-you within 24h, follow "
            "up a month later with what you did with their advice.",
            "Build your list early but don't reach out until your resume and "
            "interview prep are ready.",
        ],
        stats=["Referred candidates get hired 5-10x more often than cold applicants."],
    ),
    5: ChapterPrinciples(
        number=5,
        title="The interview secret",
        core_principle=(
            "Your goal isn't to prove you can do the job — it's to get them to "
            "love you. People hire people they like; qualifications are a distant "
            "second."
        ),
        rules=[
            "Everyone you meet is your interviewer — be your kindest self with "
            "receptionists, admins, everyone.",
            "Small talk is the best talk; stay pleasantly off-topic as long as "
            "you politely can.",
            "Don't fake missing experience — reframe it (e.g. 'you need someone "
            "to build something new, not duplicate what exists').",
            "Dress so nobody notices your clothes; scout the office dress code "
            "and dress slightly better. For video: eye-level camera, ring light, "
            "clean/blurred background.",
            "Treat AI interviewers like real ones: speak clearly, use structure "
            "(AI scoring rewards organized answers).",
            "Always have 3 strong questions for 'do you have questions for me?' "
            "(e.g. 'what does success look like at 6 months?').",
            "Send a thank-you within 24h to every interviewer and the recruiter; "
            "draft it beforehand, reference one specific thing each said.",
            "Instant rejections: trash-talking a past employer, lying about a "
            "skill, showing up late, asking about salary first, no questions at "
            "the end.",
            "If they like you but pass, they'll remember you for the next role — "
            "every interview is a relationship.",
        ],
        stats=["Most interview decisions are made in the first ~4 minutes."],
    ),
    6: ChapterPrinciples(
        number=6,
        title="Practice or perish",
        core_principle=(
            "Interviews are nearly identical — most interviewers ask the same "
            "questions. If you can predict them, you can prepare. The work is "
            "just arithmetic, and most people skip it."
        ),
        formulas=[
            "Answer structure: (1) restate the question (buys 3 seconds), "
            "(2) preview what you'll say, (3) tell a specific story with numbers, "
            "(4) summarize the point. 'Tell them what you'll say. Say it. Tell "
            "them what you said.'",
            "The math: 30 questions x 2 answers each x 3 reps out loud = 180 "
            "reps ~= 13.5 hours, spread over a week.",
        ],
        rules=[
            "Brainstorm ~30 likely questions; start from the 12 near-certain ones "
            "(tell me about yourself, why this role/company, strength, weakness, "
            "led a team, failed, difficult coworker, why leaving, 5-year plan, "
            "salary expectations, your questions).",
            "Write 2 answers per question so a second interviewer asking a "
            "repeat gets your fresh answer.",
            "Practice out loud on real humans, not in your head.",
            "You won't sound over-rehearsed — interviews are stressful enough.",
            "Start practicing the moment you start applying, not when an "
            "interview is booked (usually only 3-7 days out).",
            "Within 30 min of every interview: log every question, score "
            "yourself out of 10, add new questions, rewrite weak answers.",
        ],
    ),
    7: ChapterPrinciples(
        number=7,
        title="Land the interview, last",
        core_principle=(
            "Applying is the finish line, not the start — do it after the prep "
            "work. Practice in the minor leagues first so you don't get "
            "blindsided at your dream company."
        ),
        formulas=[
            "6-column tracker: Company | Role | Contact | Date applied | Status | "
            "Last touch.",
            "Volume math: ~100 applications -> ~5 first rounds -> ~1-2 final "
            "rounds -> ~1 offer.",
        ],
        rules=[
            "Start with B-tier companies, not dream or easy-lateral ones; an "
            "offer there is leverage with A-tier companies.",
            "Now (not earlier) contact your network for introductions.",
            "Apply directly on the company site; always submit a PDF, never a "
            "Word doc.",
            "Apply to multiple roles at the same company; different recruiters "
            "screen different roles.",
            "If silent after 3 months, refresh the resume and reapply.",
            "Follow up every 2 weeks for 6 weeks; you earned the right in the "
            "cover letter.",
            "Expect silence and rejection — it's impersonal; 3-6 months is a "
            "normal search.",
        ],
    ),
    8: ChapterPrinciples(
        number=8,
        title="Negotiate or lose",
        core_principle=(
            "Always negotiate — as long as you're polite, there's no risk. Your "
            "maximum leverage is the single moment of the offer; after you sign, "
            "it's gone."
        ),
        formulas=[
            "Know four numbers before negotiating: market range, ranges by "
            "component (base/bonus/equity), your walk-away number (never reveal), "
            "and your ask (10-20% above the offer).",
            "Deflect 'what are your salary expectations?': 'What's the budget for "
            "this role?' / 'I'd love to hear what you've allocated.' / 'I'm "
            "flexible — what's the range?'",
        ],
        rules=[
            "Don't seem greedy — they've already chosen you (exception: sales "
            "roles, where hard negotiation can be a positive signal).",
            "Best tactic: get two offers and weigh them sincerely (why Ch. 7 says "
            "start B-tier).",
            "Frame it as a shared decision ('my partner and I...') and use real, "
            "sympathetic obligations (relocation cost, student debt) — but never "
            "lie.",
            "Let them name a number first; if you go first, that's your ceiling.",
            "If they say no on base, ask for another lever: sign-on bonus, "
            "equity, extra vacation, remote/flex, earlier review, relocation.",
            "Get it in writing — verbal offers aren't offers; keep interviewing "
            "until signed.",
        ],
        stats=[
            "A $5,000 raise at 25, compounded over a career, is worth $1M+ — "
            "skipping the ask is the cost of silence.",
        ],
    ),
}


# Which chapters ground each skill.
_SKILL_CHAPTERS: dict[AgentSkill, tuple[int, ...]] = {
    AgentSkill.RESUME_BUILDER: (1, 2),
    AgentSkill.ATS_OPTIMIZER: (2,),
    AgentSkill.COVER_LETTER: (3,),
    AgentSkill.NETWORKING: (4,),
    AgentSkill.INTERVIEW_PREP: (5, 6),
    AgentSkill.PIPELINE_TRACKER: (7,),
    AgentSkill.NEGOTIATION: (8,),
}


class Playbook:
    """Read-only access to the distilled playbook principles."""

    def __init__(
        self,
        chapters: dict[int, ChapterPrinciples],
        skill_chapters: dict[AgentSkill, tuple[int, ...]],
    ) -> None:
        self._chapters = chapters
        self._skill_chapters = skill_chapters

    def chapter(self, number: int) -> ChapterPrinciples:
        try:
            return self._chapters[number]
        except KeyError:
            raise KeyError(f"No chapter {number}; chapters are 1-8.") from None

    def all_chapters(self) -> list[ChapterPrinciples]:
        return [self._chapters[n] for n in sorted(self._chapters)]

    def chapters_for_skill(self, skill: AgentSkill) -> tuple[int, ...]:
        return self._skill_chapters[skill]

    def for_skill(self, skill: AgentSkill) -> list[ChapterPrinciples]:
        """The chapter principles that ground a given skill."""
        return [self.chapter(n) for n in self._skill_chapters[skill]]

    def as_prompt(self, skill: AgentSkill) -> str:
        """A ready-to-inject prompt block of the principles behind a skill."""
        header = (
            f"You are grounding your advice in Laszlo Bock's *Apply Within* "
            f"playbook. Apply these principles for the {skill.value} skill:\n"
        )
        body = "\n".join(c.as_prompt() for c in self.for_skill(skill))
        return f"{header}\n{body}"


# The singleton other modules import.
PLAYBOOK = Playbook(_CHAPTERS, _SKILL_CHAPTERS)
