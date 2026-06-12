"""Interview Prep Coach skill (Phase 3, Chapters 5 & 6)."""

from job_hunt_assistant.interview.answers import (
    Answer,
    AnswerSet,
    lint_answer,
)
from job_hunt_assistant.interview.coaching import (
    CLOSING_QUESTIONS,
    INSTANT_REJECTIONS,
    CoachingPoint,
    closing_questions,
    coaching_points,
    instant_rejections,
)
from job_hunt_assistant.interview.generator import (
    AnswerCoach,
    QuestionGenerator,
    build_answer_prompt,
    build_question_prompt,
)
from job_hunt_assistant.interview.log import (
    AnsweredQuestion,
    InterviewLog,
)
from job_hunt_assistant.interview.questions import (
    CANONICAL_QUESTIONS,
    TARGET_QUESTION_COUNT,
    InterviewQuestion,
    PracticePlan,
    QuestionBank,
    QuestionCategory,
    canonical_questions,
    practice_plan,
)

__all__ = [
    # Questions + practice math
    "InterviewQuestion",
    "QuestionCategory",
    "QuestionBank",
    "CANONICAL_QUESTIONS",
    "TARGET_QUESTION_COUNT",
    "canonical_questions",
    "PracticePlan",
    "practice_plan",
    # Answers
    "Answer",
    "AnswerSet",
    "lint_answer",
    # Post-interview log
    "InterviewLog",
    "AnsweredQuestion",
    # Coaching (Ch. 5)
    "CoachingPoint",
    "coaching_points",
    "closing_questions",
    "instant_rejections",
    "CLOSING_QUESTIONS",
    "INSTANT_REJECTIONS",
    # LLM generators
    "QuestionGenerator",
    "AnswerCoach",
    "build_question_prompt",
    "build_answer_prompt",
]
