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


def extract_items(title: str, text: str, received: date, projects: list[dict]):
    """Return (kept, dropped): items whose quote checks out, and items that failed the check."""
    prompt = EXTRACTION_PROMPT.format(
        projects="\n".join(
            f"- {p['code']}: {p['name']} (client: {p['client_name']}, {p['client_email']})"
            for p in projects
        ),
        received=received.strftime("%A, %B %d, %Y"),
        title=title,
        text=text,
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
        (kept if quote_found(item.source_quote, text) else dropped).append(item)
    return kept, dropped