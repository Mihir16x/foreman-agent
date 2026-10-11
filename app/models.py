from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ExtractedItem(BaseModel):
    type: Literal["request", "action_item", "deadline", "decision"]
    project_code: str | None = Field(
        default=None,
        description="Code of the project this item belongs to, from the list provided. Null if unclear.",
    )
    summary: str = Field(description="The item in plain words, one short sentence.")
    due_date: date | None = Field(
        default=None,
        description="Only if the document states or clearly implies a specific date.",
    )
    owner: str | None = Field(
        default=None,
        description="Only if the document names who will do it.",
    )
    source_quote: str = Field(
        description="Words copied exactly from the document that support this item."
    )
    confidence: Literal["high", "medium", "low"]


class Extraction(BaseModel):
    items: list[ExtractedItem]