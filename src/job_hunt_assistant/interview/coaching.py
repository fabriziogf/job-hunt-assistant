"""The interview secret — "get them to love you" coaching (Chapter 5).

Chapter 5's claim: your goal isn't to prove you can do the job, it's to get the
interviewer to like you — people hire people they like, and most decisions are
made in the first ~4 minutes. This module exposes that chapter's concrete,
deterministic guidance as structured data: the behaviors that win, the strong
closing questions, and the things that instantly sink you.
"""

from __future__ import annotations

from pydantic import BaseModel


class CoachingPoint(BaseModel):
    title: str
    detail: str


# The "get them to love you" behaviors (Chapter 5).
COACHING_POINTS: list[CoachingPoint] = [
    CoachingPoint(
        title="Everyone you meet is your interviewer",
        detail="Be your kindest self with receptionists, admins, and anyone in "
        "the elevator — hiring managers ask them what you were like.",
    ),
    CoachingPoint(
        title="Small talk is the best talk",
        detail="Stay pleasantly off-topic as long as you politely can; the "
        "interviewer makes a friend with you, not the next ten candidates.",
    ),
    CoachingPoint(
        title="Reframe missing experience, don't fake it",
        detail="If you lack the exact experience, position it: they don't need "
        "someone to duplicate what exists, they need someone to build what's next.",
    ),
    CoachingPoint(
        title="Dress so nobody notices your clothes",
        detail="Scout the office dress code and dress slightly better. For video: "
        "eye-level camera, ring light, clean or blurred background.",
    ),
    CoachingPoint(
        title="Treat an AI interviewer like a real one",
        detail="Speak clearly at a normal pace and use clear structure — AI "
        "scoring rewards organized answers.",
    ),
    CoachingPoint(
        title="Send a thank-you within 24 hours",
        detail="Draft it beforehand; reference one specific thing each person "
        "said. Send one to every interviewer and to the recruiter.",
    ),
    CoachingPoint(
        title="A near-miss is a relationship",
        detail="If they like you but pass, they'll remember you for the next "
        "opening. Every interview is a relationship, not a transaction.",
    ),
]

# Strong answers to "Do you have any questions for me?" (Chapter 5).
CLOSING_QUESTIONS: list[str] = [
    "What does success look like in this role at the 6-month mark?",
    "What's the biggest challenge the person in this role will face?",
    "What didn't I ask that I should have?",
]

# Things that instantly slash your odds (Chapter 5).
INSTANT_REJECTIONS: list[str] = [
    "Trash-talking your last employer — even if they deserve it.",
    "Lying about a skill or experience — it comes out in week 1.",
    "Showing up late — always be there 15 minutes early.",
    "Asking about salary first — wait until they bring it up.",
    "Having no questions at the end — always have 3 ready.",
]


def coaching_points() -> list[CoachingPoint]:
    return [p.model_copy() for p in COACHING_POINTS]


def closing_questions() -> list[str]:
    return list(CLOSING_QUESTIONS)


def instant_rejections() -> list[str]:
    return list(INSTANT_REJECTIONS)
