import pytest
from click.testing import CliRunner

from unit_helpers import make_path, mock_session

from ghia.cli import cli


def test_no_reposlug():
    runner = CliRunner()
    result = runner.invoke(cli, ['-r', f'{make_path("rules.empty.cfg")}', '-a',
                           f'{make_path("auth.basic.cfg")}'])
    assert result.exit_code != 0
    assert 'Error: Missing argument "REPOSLUG".' in result.output

# Other CLI interface errors are tested in
# test_original/test_behavior/test_errors.py


@pytest.mark.parametrize("mock_session", [500], indirect=["mock_session"])
def test_deep_error(mock_session):
    runner = CliRunner()
    result = runner.invoke(cli, ['-r', f'{make_path("rules.empty.cfg")}', '-a',
                           f'{make_path("auth.basic.cfg")}', "user/repo"])
    assert result.exit_code == 10
    assert "Could not list issues for repository" in result.output
