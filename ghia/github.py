"""
.. module:: github

Module github covers functionality for processing and manipulating GitHub
issues.
"""

import click
import requests


class GhiaError(Exception):
    """General exception used to signalize errors in ghia package."""
    pass


class Issue:
    """Class encompassing a single GitHub issue."""

    def __init__(self, number, url, html_url, title, body, labels, assignees):
        """
        Args:
            number (int): GitHub issue number
            url (str): GitHub issue url
            html_url (str): GitHub issue html_url
            title (str): GitHub issue title
            body (str): GitHub issue body
            labels (list): list of labels (names)
            assignees (list): list of assignees (logins)
        """

        self.number = number
        self.url = url
        self.html_url = html_url
        self.title = title
        self.body = body
        self.labels = labels
        self.assignees = set(assignees)
        self.update_labels = False
        self.update_assignees = False

    def add_assignees(self, assignees):
        """Add assignees to the issue.

        Args:
            assignees (list): assignees (their logins) to be added to the issue
        """

        for a in assignees:
            self.assignees.add(a)

    def serialize(self):
        """Serialize issue to a dictionary.

        Creates a dictionary containing labels and assignees of a GitHub issue.
        This dictionary can be used as a payload for issue update.

        Returns:
            dict: serialized issue
        """

        output = dict()
        if self.update_labels:
            output["labels"] = self.labels
        if self.update_assignees:
            output["assignees"] = list(self.assignees)
        return output


def prepare_session(token):
    """Prepare requests session for communicating with GitHub.

    Creates a new :py:class:`requests.Session` object and sets "Authorization"
    and "Accept" headers of the session. The provided token is used in the
    "Authorization" header.

    Args:
        token (str): valid GitHub authorization token

    Returns:
        :py:class:`requests.Session`: the newly created session
    """

    session = requests.Session()
    session.headers["Authorization"] = f"token {token}"
    session.headers["Accept"] = "application/vnd.github.v3+json"
    return session


def match_rule(issue, rule):
    """Check whether a rule matches an issue.

    Verifies whether the provided assignment rule matches the provided issue.
    The *rule* should be a dictionary containing keys "title", "text", "label",
    or "any".

    Args:
        issue (Issue): Issue object representing a single GitHub
                                   issue
        rule (dict): a single rule as a dictionary

    Returns:
        bool: True if the rule matches the issue, False otherwise
    """

    for regex in rule["title"]:
        if regex.search(issue.title):
            return True
    for regex in rule["text"]:
        if regex.search(issue.body):
            return True
    for regex in rule["label"]:
        for label in issue.labels:
            if regex.search(label):
                return True
    for regex in rule["any"]:
        if regex.search(issue.title) or regex.search(issue.body):
            return True
        for label in issue.labels:
            if regex.search(label):
                return True
    return False


def apply_strategy(strategy, issue, users):
    """Apply the specified strategy onto an issue.

    Provided by list of users that match the issue, this function applies the
    specified strategy and modifies the assignees of the issue. As a side-effect,
    it creates a list of click messages that could be printed to terminal if
    used from CLI.

    Args:
        strategy (str): strategy to apply: append, set, or change
        issue (Issue): Issue object representing a single GitHub
                                   issue
        users (list): users (their logins) to be added to the issue

    Returns:
        list: list of click messages that can be printed to terminal
    """

    # Perform changes
    old_assignees = set(issue.assignees)
    if strategy == "append":
        issue.add_assignees(users)
    elif strategy == "set":
        if len(issue.assignees) == 0:
            issue.add_assignees(users)
    else:
        issue.update_assignees = True
        issue.assignees = set(users)
    new_assignees = issue.assignees
    all_assignees = old_assignees.union(new_assignees)

    # Prepare output
    echoes = list()
    for user in sorted(all_assignees, key=lambda s: s.casefold()):
        if user in new_assignees:
            if user in old_assignees:
                symbol = click.style("=", fg="blue", bold=True)
            else:
                issue.update_assignees = True
                symbol = click.style("+", fg="green", bold=True)
        else:
            issue.update_assignees = True
            symbol = click.style("-", fg="red", bold=True)
        echoes.append(f"   {symbol} {user}")

    return echoes


def create_issue(payload):
    """Create an issue from a payload from GitHub.

    The function reads necessary data from the JSON message representing an
    issue, received from GitHub, and creates Issue object containing this data.

    Args:
        payload (dict): dictionary representing JSON format of the payload

    Returns:
        Issue: a newly created Issue object
    """

    number = payload["number"]
    url = payload["url"]
    html_url = payload["html_url"]
    title = payload["title"]
    body = payload["body"]
    labels = [x["name"] for x in payload["labels"]]
    assignees = [x["login"] for x in payload["assignees"]]
    return Issue(number, url, html_url, title, body, labels, assignees)


def process_issue(issue, strategy, rules):
    """Process a single issue.

    Processes a single :py:class:`Issue` object. Calls
    :py:func:`match_rule` to match the issue towards provided rules,
    and then :py:func:`apply_strategy` to apply the chosen strategy
    to change assignees. It also processes the optional fallback label, if
    present.

    Args:
        issue (Issue): Issue object to process
        strategy (str): strategy to apply: append, set, or change
        rules (dict): rules to match against the issue

    Returns:
        list: list of click messages that can be printed to terminal
    """

    users = list()

    # Find users matching rules
    without_fallback = {login: rules[login]
                        for login in rules
                        if login != "fallback"}
    for login, rule in without_fallback.items():
        if match_rule(issue, rule):
            users.append(login)

    # Perform changes
    echoes = apply_strategy(strategy, issue, users)

    # Perform fallback if necessary
    if len(issue.assignees) == 0:
        try:
            label = rules["fallback"]
            fallback = click.style(f"FALLBACK", fg="yellow", bold=True)
            if label in issue.labels:
                echoes.append(f"   {fallback}: already has label \"{label}\"")
            else:
                issue.update_labels = True
                issue.labels.append(label)
                echoes.append(f"   {fallback}: added label \"{label}\"")
        except KeyError:
            pass

    return echoes


def update_github(issue, session):
    """Update an issue on GitHub.

    Sends a patch requests to GitHub by using the supplied session to update an
    issue.

    Args:
        issue (Issue): Issue object to update
        session (:py:class:`requests.Session`): the session object to use
    """

    if issue.update_labels or issue.update_assignees:
        response = session.patch(issue.url, json=issue.serialize())
        response.raise_for_status()
