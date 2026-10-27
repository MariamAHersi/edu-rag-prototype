#%%
#import neccassary packages 
from pydantic import BaseModel, Field, field_validator
from datetime import date

#%%
class GradeBand(BaseModel):
    band_name: str | None = Field(
        default=None,
        description="The band heading exactly as written, e.g. 'Excellent', 'Very Good', 'Limited/No Evidence'."
    )
    descriptor: str | None = Field(
        default=None,
        description="The text in this band's cell for this criterion, as written in the brief. Null if the cell is empty."
    )


class Criterion(BaseModel):
    name: str | None = Field(
        default=None,
        description="Name of the marking criterion (the row heading), as written in the brief."
    )
    description: str | None = Field(
        default=None,
        description="A general description of what the criterion assesses, only if the brief gives one separately from the grade band descriptors. Null otherwise."
    )
    weighting_percent: float | None = Field(
        default=None,
        description="Weighting of this criterion as a number only, e.g. 30 for '30%'. Null if not stated."
    )
    grade_bands: list[GradeBand] = Field(
        default_factory=list,
        description="One entry per grade band for this criterion. Empty list if the brief gives no band descriptors."
    )


class AssessmentBrief(BaseModel):
    programme: str | None = Field(
        default=None,
        description="Name of the programme or course the module belongs to. Null if not stated."
    )
    module_code: str | None = Field(
        default=None,
        description="Module code exactly as written, e.g. 'CS4001'."
    )
    module_title: str | None = Field(
        default=None,
        description="Full title of the module."
    )
    module_level: int | None = Field(
        default=None,
        description="Academic level of the module as a number, e.g. 4, 5, 6 or 7. Null if not stated."
    )
    assessment_type: str | None = Field(
        default=None,
        description="Type of assessment as written, e.g. 'Essay', 'Report', 'Presentation', 'Exam'."
    )
    weighting_percent: float | None = Field(
        default=None,
        description="How much this assessment contributes to the module mark, as a number only, e.g. 100 for '100%'. Null if not stated."
    )
    word_count: int | None = Field(
        default=None,
        description="Maximum word count as a number only. Null if the assessment is not word-limited."
    )
    duration_minutes: int | None = Field(
        default=None,
        description="Duration in minutes for timed assessments such as exams or presentations. Null if not timed."
    )
    deadline: date | None = Field(
        default=None,
        description="Submission deadline as an ISO date (YYYY-MM-DD). Null if only a week number or vague wording is given."
    )
    deadline_raw: str | None = Field(
        default=None,
        description="The submission deadline exactly as written in the document, e.g. 'Week 10, Monday 12pm'."
    )
    feedback_date: date | None = Field(
        default=None,
        description="Date feedback is returned to students as an ISO date (YYYY-MM-DD). Null if not a specific date."
    )
    feedback_date_raw: str | None = Field(
        default=None,
        description="The feedback return date exactly as written in the document."
    )
    submission_format: str | None = Field(
        default=None,
        description="How and in what format the work is submitted, e.g. 'PDF via Turnitin'. Null if not stated."
    )
    learning_outcomes: list[str] = Field(
        default_factory=list,
        description="Each learning outcome assessed, as a separate string. Empty list if none are stated."
    )
    marking_criteria: list[Criterion] = Field(
        default_factory=list,
        description="Each marking criterion with its grade band descriptors. Empty list if none are stated."
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Explicit requirements the submission must meet, e.g. referencing style or sections that must be included. One per string."
    )
    success_guidance: str | None = Field(
        default=None,
        description=(
            "The brief's guidance on how to do well or succeed in this assessment, "
            "copied as written. Do not summarise. Null if there is no such section."
        ),
    )
    layout_style_guidance: str | None = Field(
        default=None,
        description=(
            "Guidance on layout, structure, formatting, tone or writing style "
            "(e.g. headings, fonts, line spacing, report structure), copied as written. Null if not stated."
        ),
    )
    referencing: str | None = Field(
        default=None,
        description=(
            "Referencing and citation requirements, e.g. the referencing style to use "
            "and any rules about sources, copied as written. Null if not stated."
        ),
    )
    employability_professional_skills: str | None = Field(
        default=None,
        description=(
            "Any section describing employability, professional or transferable skills "
            "this assessment develops, copied as written. Null if not stated."
        ),
    )
    ai_use: str | None = Field(
        default=None,
        description=(
            "The brief's rules or guidance on the use of generative AI, "
            "copied exactly as written. Null if not stated."
        ),
    )
    ethical_requirements: str | None = Field(
        default=None,
        description=(
            "Ethical requirements or approvals relevant to the assessment "
            "(e.g. consent, data protection, research ethics), copied as written. Null if not stated."
        ),
    )
    submission_checklist: list[str] | None = Field(
        default=None,
        description=(
            "The submission checklist or final-check list, copied as written, "
            "keeping each item on its own line. Null if not stated."
        ),
    )
    task_description: str | None = Field(
        default=None,
        description=(
            "The full text of the assessment task, i.e. what students are asked to do, "
            "copied exactly as written in the brief. Do not summarise or reword. "
            "Include any bullet points or numbered parts. Do not include the marking "
            "criteria, learning outcomes or deadlines. Null if not stated."
        ),
    )
    @field_validator("word_count", "duration_minutes")
    @classmethod
    def must_be_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Value must be positive")
        return value