import pytest
import betamax
import os
from click.testing import CliRunner

from unit_helpers import make_path, mock_session

from ghia.github import GhiaError
from ghia.validators import validate_auth, validate_rules
from ghia.cli import cli, process_repository


with betamax.Betamax.configure() as config:
    # Read auth from GHIA_CONFIG
    try:
        BETAMAX_RECORD = os.environ["BETAMAX_RECORD"]
        if BETAMAX_RECORD == "1":
            TOKEN = os.environ["GITHUB_TOKEN"]
            config.default_cassette_options["record_mode"] = "all"
        else:
            raise KeyError
    except Exception:
        TOKEN = "false_token"
        # Do not attempt to record sessions with bad fake token
        config.default_cassette_options["record_mode"] = "none"

    # Hide the token in the cassettes
    config.define_cassette_placeholder("<TOKEN>", TOKEN)
    config.cassette_library_dir = make_path("cassettes")


@pytest.fixture
def prepare_session(betamax_session):
    betamax_session.headers.update({'Accept-Encoding': 'identity'})
    betamax_session.headers.update({'Authorization': 'token ' + TOKEN})
    return betamax_session


def test_no_reposlug():
    runner = CliRunner()
    result = runner.invoke(cli, ['-r', f'{make_path("rules.empty.cfg")}', '-a',
                           f'{make_path("auth.basic.cfg")}'])
    assert result.exit_code != 0
    assert 'Error: Missing argument "REPOSLUG".' in result.output


@pytest.mark.parametrize("mock_session", [500], indirect=["mock_session"])
def test_cli_error(mock_session):
    runner = CliRunner()
    result = runner.invoke(cli, ['-r', f'{make_path("rules.empty.cfg")}', '-a',
                           f'{make_path("auth.basic.cfg")}', "user/repo"])
    assert result.exit_code == 10
    assert "Could not list issues for repository" in result.output

# Other CLI interface errors are tested in
# test_original/test_behavior/test_errors.py


def test_reading_issues(prepare_session, capsys):
    """Tests that all issue pages are read"""

    rules = validate_rules(None, None, make_path("rules.empty.cfg"))
    process_repository("mi-pyt-ghia/kotlaluk", "append", prepare_session,
                       rules, False)
    out, err = capsys.readouterr()
    assert len(err) == 0
    assert "-> mi-pyt-ghia/kotlaluk#1 (https://github.com/mi-pyt-ghia/kotlaluk/issues/1)" in out
    assert "-> mi-pyt-ghia/kotlaluk#120 (https://github.com/mi-pyt-ghia/kotlaluk/issues/120)" in out


def test_reading_issues_error(prepare_session):
    rules = validate_rules(None, None, make_path("rules.empty.cfg"))
    with pytest.raises(GhiaError) as e:
        process_repository("mi-pyt-ghia/kotlalu", "append", prepare_session,
                           rules, False)
    assert str(e.value) == "Could not list issues for repository mi-pyt-ghia/kotlalu"


def test_single_issue_error(prepare_session, capsys):
    rules = validate_rules(None, None, make_path("rules.valid.cfg"))
    process_repository("ghia-anna/awesome", "append", prepare_session,
                       rules, False)
    out, err = capsys.readouterr()
    assert "-> ghia-anna/awesome#1 (https://github.com/ghia-anna/awesome/issues/1)" in out
    assert "   ERROR: Could not update issue ghia-anna/awesome#1" in err


def test_reset_rules(prepare_session, capsys):
    rules = validate_rules(None, None, make_path("rules.reset.cfg"))
    process_repository("mi-pyt-ghia/kotlaluk", "change", prepare_session,
                       rules, False)
    out, err = capsys.readouterr()
    assert len(err) == 0


def test_apply_rules(prepare_session, capsys):
    rules = validate_rules(None, None, make_path("rules.valid.cfg"))
    process_repository("mi-pyt-ghia/kotlaluk", "append", prepare_session,
                       rules, False)
    out, err = capsys.readouterr()

    assert len(err) == 0
    assert '-> mi-pyt-ghia/kotlaluk#5 (https://github.com/mi-pyt-ghia/kotlaluk/issues/5)\n' \
           '   = ghia-anna\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#7 (https://github.com/mi-pyt-ghia/kotlaluk/issues/7)\n' \
           '   = ghia-anna\n' \
           '   = ghia-john\n' \
           '   + ghia-peter\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#8 (https://github.com/mi-pyt-ghia/kotlaluk/issues/8)\n' \
           '   = ghia-anna\n' \
           '   = ghia-peter\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#24 (https://github.com/mi-pyt-ghia/kotlaluk/issues/24)\n' \
           '   = ghia-anna\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#27 (https://github.com/mi-pyt-ghia/kotlaluk/issues/27)\n' \
           '   + ghia-peter\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#117 (https://github.com/mi-pyt-ghia/kotlaluk/issues/117)\n' \
           '   = ghia-anna\n' in out
    assert '-> mi-pyt-ghia/kotlaluk#118 (https://github.com/mi-pyt-ghia/kotlaluk/issues/118)\n' \
           '   = ghia-peter\n' in out
    assert '   FALLBACK:' in out
