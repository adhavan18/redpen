"""llm-facing output schemas.

gemini's structured output rejects default values, so these models have none.
storage uses plain dicts built from these.
"""

from typing import Literal

from pydantic import BaseModel


# ---------- research ----------

class ResearchPlan(BaseModel):
    objective_parts: list[str]  # the objective split into separately assessable skills
    key_terms: list[str]
    web_queries: list[str]
    primary_source_queries: list[str]  # specs, official docs, standards
    misconception_queries: list[str]  # short queries for stack overflow
    book_queries: list[str]
    video_queries: list[str]


# ---------- generation ----------

class DraftSection(BaseModel):
    kind: Literal["hook", "concept", "example", "misconceptions", "activity", "recap"]
    title: str
    minutes: int
    body_md: str


class DraftQuestion(BaseModel):
    question: str
    options: list[str]
    answer_index: int
    explanation: str
    objective_part: str
    distractor_rationale: list[str]  # why each wrong option is tempting (which misconception)


class DraftVideo(BaseModel):
    video_id: str
    segment_index: int  # index into the candidate's segment list, -1 for whole video
    why: str
    in_lesson: bool
    after_section: int


class LessonDraft(BaseModel):
    objective_parts: list[str]
    sections: list[DraftSection]
    quiz: list[DraftQuestion]
    quiz_minutes: int
    videos: list[DraftVideo]
    evidence_gaps: list[str]


# ---------- qc 1: factual ----------

class ExtractedClaim(BaseModel):
    section_index: int
    sentence: str  # copied verbatim from the lesson
    claim: str  # the atomic factual claim, standalone
    cited: list[str]
    testable: bool  # can be checked by running code or sending an http request


class ClaimList(BaseModel):
    claims: list[ExtractedClaim]


class ClaimVerdict(BaseModel):
    claim_index: int
    verdict: Literal["supported", "partial", "unsupported", "contradicted"]
    evidence_id: str  # chunk id like c12, or "" if none
    quote: str  # verbatim quote from that chunk, or ""
    reasoning: str
    fix: str


class VerdictList(BaseModel):
    verdicts: list[ClaimVerdict]


class HttpProbe(BaseModel):
    claim_index: int
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
    url: str
    body_json: str  # json string, or "" for no body
    expect_status_min: int
    expect_status_max: int
    rationale: str


class ProbePlan(BaseModel):
    probes: list[HttpProbe]


class ReviewIssue(BaseModel):
    severity: Literal["high", "medium", "low"]
    category: str
    section_index: int  # -1 = whole lesson, -2 = quiz
    description: str
    evidence: str
    suggestion: str


class IssueList(BaseModel):
    issues: list[ReviewIssue]


# ---------- qc 2: instructional ----------

class StudentProfile(BaseModel):
    name: str
    level: Literal["novice", "struggling", "average", "strong"]
    background: str
    habits: str  # how they read and where they slip


class StudentAnswer(BaseModel):
    question_index: int
    chosen_index: int
    confidence: int  # 1-5
    lesson_quote: str  # the lesson line they relied on, "" if guessing


class Confusion(BaseModel):
    section_index: int
    quote: str
    why: str


class StudentRun(BaseModel):
    answers: list[StudentAnswer]
    confusions: list[Confusion]


class AlignmentRow(BaseModel):
    objective_part: str
    taught_in: list[int]
    practised_in: list[int]
    assessed_by: list[int]
    coverage: Literal["full", "partial", "missing"]
    note: str


class RubricScore(BaseModel):
    criterion: Literal["objective_alignment", "clarity", "structure", "examples", "practical_application",
                       "assessment_quality", "pacing", "engagement"]
    score: int  # 1-5
    justification: str


class InstructionalReview(BaseModel):
    alignment: list[AlignmentRow]
    rubric: list[RubricScore]
    issues: list[ReviewIssue]


# ---------- fixes ----------

class SectionRewrite(BaseModel):
    body_md: str
    change_summary: str


class QuizRewrite(BaseModel):
    quiz: list[DraftQuestion]
    change_summary: str
