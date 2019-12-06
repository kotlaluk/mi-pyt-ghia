"""
.. module:: cli

Module cli defines functionality for the CLI part of the ghia package. The CLI
interface is able to process issues for a GitHub repository in batches.
"""

import click
import requests
import sys

from .validators import validate_auth, validate_reposlug, validate_rules
from .github import GhiaError, create_issue, process_issue, prepare_session,\
                    update_github


GITHUB_URL = "https://api.github.com/repos/"


def process_repository(reposlug, strategy, session, rules, dry_run):
    """Process the whole GitHub repository.

    This function is called from CLI after all validations are made to process
    the specified repository. It performs all the operations: reads the issues
    from the repository, matches the issues towards the provided rules, applies
    the chosen strategy, and performs necessary updates of issues in GitHub.
    It uses functionality of the :py:mod:`ghia.github` module.

    Args:
        reposlug (str): GitHub reposlug in owner/repository format
        strategy (str): strategy to apply: append, set, or change
        session (:py:class:`requests.Session`): an initialized and prepared
                                                session object to use
        rules (dict): rules to match against the repository issues
        dry_run (bool): allows to run without making any changes (only prints
                        output)

    Raises:
        GhiaError: if there is an permission or connection error in the
                   communication with the GitHub repository
    """

    issues_url = f"{GITHUB_URL}{reposlug}/issues"

    # Loop through pages with issues
    try:
        while issues_url:
            response = session.get(issues_url)
            response.raise_for_status()

            # Extract issues from the page
            for i in response.json():
                issue = create_issue(i)

                # Process the issue
                try:
                    echo_name = click.style(f"{reposlug}#{issue.number}",
                                            bold=True)
                    click.echo(f"-> {echo_name} ({issue.html_url})")
                    try:
                        # Process the issue
                        echoes = process_issue(issue, strategy, rules)
                        # Update GitHub
                        if not dry_run and (issue.update_assignees
                                            or issue.update_labels):
                            update_github(issue, session)
                        # Print output
                        for echo in echoes:
                            click.echo(echo)
                    except requests.HTTPError:
                        raise GhiaError(f"Could not update issue "
                                        f"{reposlug}#{issue.number}")
                except GhiaError as e:
                    error = click.style("ERROR", fg="red", bold=True)
                    click.echo(f"   {error}: {e}", err=True)

            # Go to the next page
            try:
                issues_url = response.links['next']['url']
            except KeyError:
                issues_url = None
    except requests.HTTPError:
        raise GhiaError(f"Could not list issues for repository {reposlug}")


@click.command()
@click.argument("reposlug", metavar="REPOSLUG", required=True,
                callback=validate_reposlug)
@click.option("-s", "--strategy", help="How to handle assignment collisions.",
              type=click.Choice(["append", "set", "change"],
              case_sensitive=False), default="append", show_default=True)
@click.option("-d", "--dry-run", help="Run without making any changes.",
              is_flag=True)
@click.option("-a", "--config-auth",
              help="File with authorization configuration.", metavar="FILENAME",
              required=True, type=click.Path(exists=True),
              callback=validate_auth)
@click.option("-r", "--config-rules",
              help="File with assignment rules configuration.",
              metavar="FILENAME", required=True, type=click.Path(exists=True),
              callback=validate_rules)
def cli(reposlug, strategy, config_auth, config_rules, dry_run):
    """CLI interface for automatic assigning of GitHub issues.

    This function is the entrypoint when *ghia* is executed from command line.

    Args:
        reposlug (str): GitHub reposlug in owner/repository format
        strategy (str): strategy to apply: append, set, or change
        config_auth (file): a file with authorization configuration
        config_rules (file): a file with assignment rules configuration
        dry_run (bool): allows to run without making any changes (only prints
                        output)
    """

    try:
        token = config_auth["token"]
        session = prepare_session(token)
        process_repository(reposlug, strategy, session, config_rules, dry_run)
    except GhiaError as e:
        error = click.style("ERROR", fg="red", bold=True)
        click.echo(f"{error}: {e}", err=True)
        sys.exit(10)
