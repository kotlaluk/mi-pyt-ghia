"""
.. module:: cli

Module cli defines functionality for the CLI part of the ghia package. The CLI
interface is able to process issues for a GitHub repository in batches.
"""

import aiohttp
import asyncio
import click
import requests
import sys

from .validators import validate_auth, validate_reposlug, validate_rules
from .github import GhiaError, create_issue, process_issue, prepare_session,\
                    update_github


GITHUB_URL = "https://api.github.com/repos/"


async def async_fetch(session, url, links_only=False):
    if links_only:
        async with session.head(url) as response:
            response.raise_for_status()
            return response.links
    else:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


async def async_process_issue(session, issue, reposlug, strategy, rules,
                              dry_run, token):
    try:
        echo_name = click.style(f"{reposlug}#{issue.number}", bold=True)
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


async def async_process_issue_page(session, async_session, page_url, reposlug,
                                   strategy, rules, dry_run, token):
    page = await async_fetch(async_session, page_url)
    issues = list()
    for item in page:
        issues.append(create_issue(item))
    await asyncio.gather(*[async_process_issue(session, issue, reposlug,
                           strategy, rules, dry_run, token)
                           for issue in issues])


async def async_process_repository(reposlug, strategy, session, token, rules,
                                   dry_run):
    issues_url = f"{GITHUB_URL}{reposlug}/issues"

    headers = dict()
    headers["Accept"] = "application/vnd.github.v3+json"
    headers["Authorization"] = f"token {token}"
    async_session = aiohttp.ClientSession(headers=headers)

    async with async_session:
        try:
            links = await async_fetch(async_session, issues_url, links_only=True)
            last_url = str(links["last"]["url"])
            issue_page_urls = [last_url[:-1] + str(x)\
                               for x in range(1, int(last_url[-1]) + 1)]
            await asyncio.gather(*[async_process_issue_page(session, async_session,
                                   url, reposlug, strategy, rules, dry_run, token)
                                   for url in issue_page_urls])

        except aiohttp.ClientResponseError:
            error = click.style("ERROR", fg="red", bold=True)
            click.echo(f"{error}: Could not list issues for repository {reposlug}",
                    err=True)


async def async_process_repositories(reposlugs, strategy, session, token, rules,
                                     dry_run):
    await asyncio.gather(*[async_process_repository(reposlug, strategy, session,
                           token, rules, dry_run) for reposlug in reposlugs])


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
@click.argument("reposlugs", metavar="REPOSLUGS", required=True, nargs=-1,
                callback=validate_reposlug)
@click.option("-s", "--strategy", help="How to handle assignment collisions.",
              type=click.Choice(["append", "set", "change"], case_sensitive=False),
              default="append", show_default=True)
@click.option("-d", "--dry-run", help="Run without making any changes.",
              is_flag=True)
@click.option("-a", "--config-auth", metavar="FILENAME", callback=validate_auth,
              help="File with authorization configuration.", required=True,
              type=click.Path(exists=True))
@click.option("-r", "--config-rules", callback=validate_rules,
              help="File with assignment rules configuration.",
              metavar="FILENAME", required=True, type=click.Path(exists=True))
@click.option("-x", "--async", "asynchronous", is_flag=True,
              help="Process multiple repositories asynchronously.")
def cli(reposlugs, strategy, config_auth, config_rules, dry_run, asynchronous):
    """CLI tool for automatic issue assigning of GitHub issues"""

    try:
        token = config_auth["token"]
        session = prepare_session(token)
        if asynchronous:
            asyncio.run(async_process_repositories(reposlugs, strategy, session,
                                                   token, config_rules, dry_run))
        else:
            for reposlug in reposlugs:
                process_repository(reposlug, strategy, session, config_rules,
                                   dry_run)
    except GhiaError as e:
        error = click.style("ERROR", fg="red", bold=True)
        click.echo(f"{error}: {e}", err=True)
        sys.exit(10)
