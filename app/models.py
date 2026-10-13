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

class TaskMatch(BaseModel):
    item_index: int
    action: Literal["create_task", "update_task", "no_change"]
    task_id: int | None = Field(
        default=None, description="Id of the existing task this item is about. Required for update_task."
    )
    new_title: str | None = Field(
        default=None, description="For create_task: a short title in the same style as existing tasks."
    )
    new_due_date: date | None = Field(default=None, description="Only if the item states a date.")
    new_owner: str | None = Field(default=None, description="Only if the item names an owner.")
    new_status: Literal["open", "blocked"] | None = Field(
        default=None, description="Set 'open' if the item unblocks a blocked task."
    )
    note: str | None = Field(
        default=None, description="Short note for decisions or extra requirements that don't fit a field."
    )
    reason: str = Field(description="One sentence explaining the choice.")


class Reconciliation(BaseModel):
    matches: list[TaskMatch]

class CitedParagraph(BaseModel):
    text: str
    citations: list[str] = Field(
        description="Ids of the facts this paragraph is based on, e.g. ['T5', 'I12']."
    )


class StatusDraft(BaseModel):
    outstanding: list[CitedParagraph] = Field(
        description="Internal answer for the PM: what is open, blocked (and why), and recently requested."
    )
    email_subject: str
    email_paragraphs: list[CitedParagraph] = Field(
        description="Body of the client update, without greeting or sign-off."
    )
    questions_for_client: list[str] = Field(
        description="Information or decisions only the client can provide. Empty if none."
    )