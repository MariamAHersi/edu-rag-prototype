#%%
# import neccesary files
from pydantic import BaseModel, Field, field_validator
from datetime import date

class AssessmentBrief(BaseModel):
    programme: str | None = None
    module_code: str | None = None
    module_title: str | None = None
    module_level: int | None = None

    assessment_type: str | None = None
    weighting_percent: float | None = None

    word_count: int | None = None
    duration_minutes: int | None = None

    deadline: date | None = None
    deadline_raw: str | None = None
    feedback_date: date | None = None
    feedback_date_raw: str | None = None

    submission_format: str | None = None  # was format_location

    @field_validator("word_count", "duration_minutes")
    @classmethod
    def must_be_positive(cls, value):
        if value is not None and value <= 0:
            raise ValueError("Value must be positive")
        return value

    