from app.tools import find_project, search_documents


def test_find_project_by_partial_name():
    matches = find_project("riverside")
    assert [m["code"] for m in matches] == ["RVS-2041"]


def test_find_project_returns_empty_when_unknown():
    assert find_project("airport") == []


def test_search_finds_the_culvert_meeting():
    riverside = find_project("riverside")[0]
    results = search_documents(riverside["id"], "culvert")
    assert results[0]["title"] == "Riverside internal design meeting"


def test_search_stays_within_one_project():
    oak = find_project("oak street")[0]
    assert search_documents(oak["id"], "culvert") == []