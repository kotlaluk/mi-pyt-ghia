import click
import requests


class GhiaError(Exception):
    pass


class Issue:
    def __init__(self, number, url, html_url, title, body, labels, assignees):
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
        for a in assignees:
            self.assignees.add(a)

    def serialize(self):
        output = dict()
        if self.update_labels:
            output["labels"] = self.labels
        if self.update_assignees:
            output["assignees"] = list(self.assignees)
        return output


def prepare_session(auth):
    session = requests.Session()
    session.headers["Authorization"] = f"token {auth}"
    session.headers["Accept"] = "application/vnd.github.v3+json"
    return session


def match_rule(issue, rule):
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
    number = payload["number"]
    url = payload["url"]
    html_url = payload["html_url"]
    title = payload["title"]
    body = payload["body"]
    labels = [x["name"] for x in payload["labels"]]
    assignees = [x["login"] for x in payload["assignees"]]
    return Issue(number, url, html_url, title, body, labels, assignees)


def process_issue(issue, strategy, rules):
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
    if issue.update_labels or issue.update_assignees:
        response = session.patch(issue.url, json=issue.serialize())
        response.raise_for_status()
