import os
import re
from datetime import date

from langchain.chat_models import init_chat_model

from app.models import Extraction, ExtractedItem
from app.prompts import EXTRACTION_PROMPT


class ExtractionFailed(Exception):
    """The model could not produce valid output, even after a retry."""


def get_llm():
    return init_chat_model(os.environ["LLM_MODEL"], model_provider=os.environ["LLM_PROVIDER"])


def normalize(text: str) -> str:
    """Lowercase and collapse whitespace, so line breaks don't break the quote check."""
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_found(quote: str, document: str) -> bool:
    return normalize(quote) in normalize(document)


def extract_items(title: str, text: str, received: date, projects: list[dict],
                  filed_under: str | None = None):
    """Return (kept, dropped): items whose quote checks out, and items that failed the check."""
    prompt = EXTRACTION_PROMPT.format(
        projects="\n".join(
            f"- {p['code']}: {p['name']} (client: {p['client_name']}, {p['client_email']})"
            for p in projects
        ),
        received=received.strftime("%A, %B %d, %Y"),
        title=title,
        text=text,
        filed_under=(
            f"This document was filed under project {filed_under}. Assign items to it "
            f"unless the text is clearly about a different project."
            if filed_under else "This document has not been filed under a project yet."
        ),
    )
    model = get_llm().with_structured_output(Extraction)

    # Try twice: models occasionally return malformed output.
    for attempt in range(2):
        try:
            result = model.invoke(prompt)
            if result is not None:
                break
        except Exception as error:
            last_error = error
    else:
        raise ExtractionFailed(f"No valid output after 2 attempts: {last_error!r}")

    kept: list[ExtractedItem] = []
    dropped: list[ExtractedItem] = []
    for item in result.items:
        if not quote_found(item.source_quote, text):
            dropped.append(item)
            continue
        # The owner's name must appear in the quoted evidence; a greeting doesn't count.
        if item.owner and item.owner.split()[0].lower() not in normalize(item.source_quote):
            item.owner = None
        kept.append(item)
    return kept, dropped