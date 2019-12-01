import pytest
import re
import requests
from pathlib import Path

from unit_helpers import make_path, env, load_example, mock_session

from ghia.github import GhiaError
from ghia.web import read_config, process_post_issues


@pytest.fixture
def testapp():
    from ghia import app
    app.config["TESTING"] = True
    return app.test_client()


def test_user_error():
    with pytest.raises(GhiaError) as e:
        with env(GITHUB_USER=""):
            read_config()
    assert str(e.value) == "No GitHub user specified"


def test_no_config_error():
    with pytest.raises(GhiaError) as e:
        with env(GITHUB_USER="user"):
            read_config()
    assert str(e.value) == "No configuration files found"


@pytest.mark.parametrize(("file1", "file2"),
                         (("empty_file.cfg", "auth.githu.cfg"),
                          ("auth.githu.cfg", "rules.fallback.cfg"),
                          ("auth.no_token.cfg", "rules.invalid_regex.cfg")))
def test_config_errors(file1, file2):
    with pytest.raises(GhiaError) as e:
        with env(GITHUB_USER="user"),\
             env(GHIA_CONFIG=f"{make_path(file1)}:{make_path(file2)}"):
            read_config()
    assert "Invalid format of configuration file" in str(e.value)


def test_read_config():
    with env(GITHUB_USER="user"),\
         env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                          f'{make_path("rules.fallback.cfg")}:'
                          f'{make_path("rules.no_fallback.cfg")}')):
        d = read_config()
    assert "fallback" in d["rules"].keys()
    assert d["auth"]["user"] == "user"
    assert d["auth"]["token"] == "ffffffffffffffffffffffffffffffffffffffff"
    assert d["auth"]["secret"] == "tajneheslo"
    assert re.match(d["rules"]["ghia-anna"]["text"][0], "requests library")
    assert len(d["rules"]["ghia-jane"]["text"]) == 3


def test_app_get(testapp):
    with env(GITHUB_USER="user"),\
         env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                          f'{make_path("rules.fallback.cfg")}:'
                          f'{make_path("rules.no_fallback.cfg")}')):
        assert "user" in testapp.get("/").get_data(as_text=True)
        assert "tajneheslo" not in testapp.get("/").get_data(as_text=True)
        assert "Need assignment" in testapp.get("/").get_data(as_text=True)
        assert "ghia-anna" in testapp.get("/").get_data(as_text=True)


def test_app_post_ping(testapp):
    with env(GITHUB_USER="user"),\
         env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                          f'{make_path("rules.fallback.cfg")}:'
                          f'{make_path("rules.no_fallback.cfg")}')):
        assert "Ping successful" == testapp.post("/",
                                        json=load_example("ping_example.json"),
                                        headers={
            'X-Hub-Signature': 'sha1=d00e131ec9215b2a349ea1541e01e1a84ac38d8e',
            'X-GitHub-Event': 'ping'}).get_data(as_text=True)


@pytest.mark.parametrize("mock_session", [200], indirect=["mock_session"])
def test_process_post_issues(mock_session):
    with env(GITHUB_USER="user"),\
         env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                          f'{make_path("rules.fallback.cfg")}:'
                          f'{make_path("rules.no_fallback.cfg")}')):
        config = read_config()
    session = requests.Session()
    response = process_post_issues(load_example("issues_example.json"),
                                   config, session)
    assert "was successfully updated" in response


@pytest.mark.parametrize("mock_session", [400], indirect=["mock_session"])
def test_post_issues_connection_error(mock_session):
    with pytest.raises(requests.HTTPError):
        with env(GITHUB_USER="user"),\
            env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                             f'{make_path("rules.fallback.cfg")}:'
                             f'{make_path("rules.no_fallback.cfg")}')):
            config = read_config()
            session = requests.Session()
            process_post_issues(load_example("issues_example.json"),
                                config, session)


def test_app_post_errors(testapp):
    with env(GITHUB_USER="user"),\
         env(GHIA_CONFIG=(f'{make_path("auth.secret.cfg")}:'
                          f'{make_path("rules.fallback.cfg")}:'
                          f'{make_path("rules.no_fallback.cfg")}')):
        response = testapp.post("/",
                        json=load_example("ping_example.json"),
                        headers={
        'X-Hub-Signature': 'sha1=d00e131ec9215b2a349ea1541e01e1a84ac38d8d',
        'X-GitHub-Event': 'ping'})
        assert "401 Unauthorized" in response.get_data(as_text=True)
        assert response.status_code == 401

        response = testapp.post("/",
                        json=load_example("ping_example.json"),
                        headers={
        'X-Hub-Signature': 'sha1=d00e131ec9215b2a349ea1541e01e1a84ac38d8e',
        'X-GitHub-Event': 'pong'})
        assert response.status_code == 501

        response = testapp.post("/",
                        json=load_example("issues_wrong_action.json"),
                        headers={'X-GitHub-Event': 'issues'})
        assert response.status_code == 501
