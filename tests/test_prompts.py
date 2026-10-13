from app.prompts import EXTRACTION_PROMPT, RECONCILE_PROMPT, STATUS_PROMPT


def test_extraction_prompt_fills_cleanly():
    text = EXTRACTION_PROMPT.format(projects="p", received="r", filed_under="f", title="t", text="x")
    assert "{" not in text


def test_reconcile_prompt_fills_cleanly():
    text = RECONCILE_PROMPT.format(project="p", tasks="t", received="r", items="i", document="d")
    assert "{" not in text
    assert "STATUS_PROMPT" not in text  # catches a missing closing quote


def test_status_prompt_fills_cleanly():
    text = STATUS_PROMPT.format(project="p", client="c", today="d", facts="f")
    assert "{" not in text