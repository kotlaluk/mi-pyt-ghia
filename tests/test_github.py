import pytest
import re
import requests

from unit_helpers import load_example, contains_exactly, mock_session

from ghia.github import Issue, match_rule, apply_strategy, create_issue,\
                        process_issue, update_github


def test_create_issue():
    i = create_issue(load_example("issues_example.json")["issue"])
    assert isinstance(i, Issue)
    assert i.number == 1
    assert i.title == "Spelling error in the README file"
    assert i.url == "https://api.github.com/repos/Codertocat/Hello-World/issues/1"
    assert i.html_url == "https://github.com/Codertocat/Hello-World/issues/1"
    assert i.body == "It looks like you accidently spelled 'commit' with two 't's."
    assert contains_exactly(i.labels, ("bug", ))
    assert contains_exactly(i.assignees, ("Codertocat", ))

    i.add_assignees(("Assignee", ))
    i.update_assignees = True
    i.update_labels = True
    d = i.serialize()
    assert contains_exactly(d["labels"],  ("bug", ))
    assert contains_exactly(d["assignees"], ("Codertocat", "Assignee"))


def test_match_rule():
    i = create_issue(load_example("issues_example.json")["issue"])
    rule = dict()
    rule["text"] = list()
    rule["label"] = list()
    rule["any"] = list()
    rule["title"] = list()
    assert not match_rule(i, rule)

    rule["text"].append(re.compile("commit"))
    assert match_rule(i, rule)


@pytest.mark.parametrize("strategy", ("append", "set", "change"))
def test_strategy(strategy):
    i = create_issue(load_example("issues_example.json")["issue"])
    users = ("Assignee1", "Assignee2")
    echoes = apply_strategy(strategy, i, users)
    if strategy == "append":
        assert contains_exactly(i.assignees, ("Codertocat", "Assignee1",
                                              "Assignee2"))
        assert len(echoes) == 3
    elif strategy == "set":
        assert contains_exactly(i.assignees, ("Codertocat", ))
        assert len(echoes) == 1
    else:
        assert contains_exactly(i.assignees, users)
        assert len(echoes) == 3


@pytest.mark.parametrize("strategy", ("append", "set", "change"))
def test_process_issue(strategy):
    i = create_issue(load_example("issues_example.json")["issue"])
    rules = dict()
    rule = dict()
    rule["text"] = list()
    rule["label"] = list()
    rule["any"] = list()
    rule["title"] = list()
    rule["text"].append(re.compile("commit"))
    rules["Assignee1"] = rule

    echoes = process_issue(i, strategy, rules)
    if strategy == "append":
        assert i.update_assignees
        assert contains_exactly(i.assignees, ["Codertocat", "Assignee1"])
        assert len(echoes) == 2
    elif strategy == "set":
        assert not i.update_assignees
        assert contains_exactly(i.assignees, ["Codertocat"])
        assert len(echoes) == 1
    else:
        assert i.update_assignees
        assert contains_exactly(i.assignees, ["Assignee1"])
        assert len(echoes) == 2


@pytest.mark.parametrize("mock_session", [500], indirect=["mock_session"])
def test_update_github(mock_session):
    i = create_issue(load_example("issues_example.json")["issue"])
    session = requests.Session()
    update_github(i, session)
    i.update_assignees = True
    with pytest.raises(requests.HTTPError):
        update_github(i, session)
    i.update_assignees = False
    i.update_labels = True
    with pytest.raises(requests.HTTPError):
        update_github(i, session)
