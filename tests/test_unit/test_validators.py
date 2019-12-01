import pytest
import re
from pathlib import Path
from click import BadParameter

from unit_helpers import make_path

from ghia.validators import validate_reposlug, validate_auth, validate_rules,\
                            validate_signature


ctx = None
param = None


def test_reposlug():
    assert validate_reposlug(ctx, param, "owner/repo") == "owner/repo"


@pytest.mark.parametrize("reposlug", ("some_text", "owner/repo/something",
                                      "invalid/char;acter"))
def test_invalid_reposlug(reposlug):
    with pytest.raises(BadParameter) as e:
        validate_reposlug(ctx, param, reposlug)
    assert str(e.value) == "not in owner/repository format"


def test_auth_basic():
    auth = validate_auth(ctx, param, make_path("auth.basic.cfg"))
    assert auth["token"] == "ffffffffffffffffffffffffffffffffffffffff"


def test_auth_with_secret():
    auth = validate_auth(ctx, param, make_path("auth.secret.cfg"))
    assert auth["token"] == "ffffffffffffffffffffffffffffffffffffffff"
    assert auth["secret"] == "tajneheslo"


@pytest.mark.parametrize("file", ("empty_file.cfg", "auth.githu.cfg",
                                  "auth.no_token.cfg"))
def test_invalid_auth(file):
    with pytest.raises(BadParameter) as e:
        validate_auth(ctx, param, make_path(file))
    assert str(e.value) == "incorrect configuration format"


def test_rules_empty():
    d = validate_rules(ctx, param, make_path("rules.empty.cfg"))
    assert type(d) == dict
    assert len(d) == 0


def test_rules_valid():
    d = validate_rules(ctx, param, make_path("rules.valid.cfg"))
    assert "fallback" in d.keys()
    assert "title" in d["ghia-anna"].keys()
    assert re.match(d["ghia-john"]["label"][0], "assign-john")
    assert len(d["ghia-peter"]["any"]) == 2


def test_rules_with_fallback():
    d = validate_rules(ctx, param, make_path("rules.fallback.cfg"))
    assert d["fallback"] == "Need assignment"
    assert len(d) == 1


@pytest.mark.parametrize("file", ("empty_file.cfg", "rules.fallback_only.cfg",
                                  "rules.invalid_regex.cfg",
                                  "rules.invalid_fallback.cfg"))
def test_invalid_rules(file):
    with pytest.raises(BadParameter) as e:
        validate_rules(ctx, param, make_path(file))
    assert str(e.value) == "incorrect configuration format"


def test_signature():
    assert validate_signature("secret", "qwertyuiop".encode("ascii"),
                              "sha1=6793e2cc70039317a633a5ce17038afc4cd5964d")
    assert not validate_signature("secret", "qwertyuiop".encode("ascii"),
                                  "sha1=6793e2cc70039317a633a5ce17038afc4cd5964e")
