import click
import requests
import configparser
import re
import sys
import os
import flask
import hmac

GITHUB_URL = "https://api.github.com/repos/"

app = flask.Flask(__name__)

def read_config():
    config = dict()
    config["rules"] = dict()
    config["auth"] = dict()

    # Read environment variables
    try:
        config["auth"]["user"] = os.environ["GITHUB_USER"]
    except KeyError:
        raise GhiaError("No GitHub user specified")
    
    try:
        config_files = os.environ["GHIA_CONFIG"].split(":")
        
        # Process configuration files
        for file in config_files:
            errors = 0
            try:
                r = dict()
                r = validate_rules(None, None, file)
                config["rules"].update(r)
            except click.BadParameter:
                errors += 1
            try:
                a = dict()
                a = validate_auth(None, None, file)
                config["auth"].update(a)
            except click.BadParameter:
                errors +=1
            if errors == 2:
                raise GhiaError(f"Invalid format of configuration file {file}")
    except KeyError:
        raise GhiaError("No configuration files found")
    return config

def validate_signature(secret, header_signature, data):
    digest_mode, signature = header_signature.split("=")
    mac = hmac.new(bytes(secret, "ascii"), msg=data, digestmod=digest_mode)
    return hmac.compare_digest(signature, mac.hexdigest())

@app.route("/", methods=["GET", "POST"])
def index():
    config = read_config()

    if flask.request.method == "GET":
        without_fallback = {login: config["rules"][login] \
                for login in config["rules"] if login != "fallback"}
        try:
            fallback = config["rules"]["fallback"]
        except KeyError:
            fallback = None
        return flask.render_template("index.html", user=config["auth"]["user"], \
        rules=without_fallback, fallback=fallback)

    if flask.request.method == "POST":
        # Perform validation if present
        try:
            signature = flask.request.headers["X-Hub-Signature"]
            if not validate_signature(str(config["auth"]["secret"]), signature, flask.request.data):
                flask.abort(401)
        except KeyError:
            pass

        # Process received action
        try:
            event = flask.request.headers["X-GitHub-Event"]
            if event == "ping":
                app.logger.info("Received PING event")
                return "Ping successful"
            elif event =="issues":
                if flask.request.json["action"] in ("opened", "edited", "transferred", \
                    "reopened", "assigned", "unassigned", "labeled", "unlabeled"):
                    app.logger.info("Received ISSUES event")
                    payload = flask.request.json["issue"]
                    repo_url = payload["repository_url"].split("/")
                    reposlug = f"{repo_url[-2]}/{repo_url[-1]}"
                    issue = create_issue(payload)

                    session = requests.Session()
                    session.headers["Authorization"] = f"token {config['auth']['token']}"
                    session.headers["Accept"] = "application/vnd.github.v3+json"
                    process_issue(issue, reposlug, "append", config["rules"], False, session, print_output=False)
                    app.logger.info("Issue sent successfully")
                    return f"Issue {issue.number} ({issue.title}) was successfully updated."
                else:
                    flask.abort(501)
            else:
                flask.abort(501)
        except KeyError:
            flask.abort(400)

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

def create_issue(payload):
    number = payload["number"]
    url = payload["url"]
    html_url = payload["html_url"]
    title = payload["title"]
    body = payload["body"]
    labels = [x["name"] for x in payload["labels"]]
    assignees = [x["login"] for x in payload["assignees"]]
    return Issue(number, url, html_url, title, body, labels, assignees)

def validate_reposlug(ctx, param, reposlug):
    if re.match("[\\w-]+\\/[\\w-]+", reposlug):
        return reposlug
    else:
        raise click.BadParameter("not in owner/repository format")

def validate_auth(ctx, param, config_auth):
    try:
        auth_parser = configparser.ConfigParser()
        auth_parser.read(config_auth)
        if "token" not in auth_parser["github"]:
            raise KeyError
        return auth_parser["github"]
    except KeyError:
        raise click.BadParameter("incorrect configuration format")

def validate_rules(ctx, param, config_rules):
    try:
        rules_parser = configparser.ConfigParser()
        rules_parser.optionxform = str
        rules_parser.read(config_rules)
        if "patterns" not in rules_parser:
            raise click.BadParameter("incorrect configuration format")
        rules = dict()

        # Handle fallback
        if rules_parser.has_option("fallback", "label"):
            rules["fallback"] = rules_parser["fallback"]["label"]

        # Handle patterns
        for key, value in rules_parser["patterns"].items():
            rules[key] = dict()
            rules[key]["any"] = list()
            rules[key]["title"] = list()
            rules[key]["text"] = list()
            rules[key]["label"] = list()
            for line in value.split("\n"):
                rule = line.split(":", 1)
                if len(rule) == 2:
                    rules[key][rule[0]].append(re.compile(rule[1], re.IGNORECASE))

        return rules

    except KeyError:
        raise click.BadParameter("incorrect configuration format")

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
                symbol = click.style("=", fg="green", bold=True)
            else:
                symbol = click.style("+", fg="green", bold=True)
        else:
            symbol = click.style("-", fg="red", bold=True)
        echoes.append(f"   {symbol} {user}")

    return echoes

def process_issue(issue, reposlug, strategy, rules, dry_run, session, print_output=True):
    if print_output:
        echo_name = click.style(f"{reposlug}#{issue.number}", bold=True)
        click.echo(f"-> {echo_name} ({issue.html_url})")
    try:
        users = list()

        # Find users matching rules
        without_fallback = {login: rules[login] \
            for login in rules if login != "fallback"}
        for login, rule in without_fallback.items():
            if match_rule(issue, rule):
                issue.update_assignees = True
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

        # Update issues on GitHub
        if (not dry_run) and (issue.update_labels or issue.update_assignees):
            response = session.patch(issue.url, json=issue.serialize())
            response.raise_for_status()

        # Echo output
        if print_output:
            for echo in echoes:
                click.echo(echo)

    except requests.HTTPError:
        raise GhiaError(f"Could not update issue {reposlug}#{issue.number}")

def process_repository(reposlug, strategy, token, rules, dry_run):
    # Prepare session
    issues_url = f"{GITHUB_URL}{reposlug}/issues"
    session = requests.Session()
    session.headers["Authorization"] = f"token {token}"
    session.headers["Accept"] = "application/vnd.github.v3+json"
    
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
                    process_issue(issue, reposlug, strategy, rules, dry_run, session)
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
    type=click.Choice(["append", "set", "change"], case_sensitive=False), 
    default="append", show_default=True)
@click.option("-d", "--dry-run", help="Run without making any changes.", is_flag=True)
@click.option("-a", "--config-auth", help="File with authorization configuration.", 
    metavar="FILENAME", required=True, type=click.Path(exists=True), 
    callback=validate_auth)
@click.option("-r", "--config-rules", help="File with assignment rules configuration.", 
    metavar="FILENAME", required=True, type=click.Path(exists=True), 
    callback=validate_rules)
def main(reposlug, strategy, config_auth, config_rules, dry_run):
    """ CLI tool for automatic issue assigning of GitHub issues"""
    try:
        token = config_auth["token"]
        process_repository(reposlug, strategy, token, config_rules, dry_run)
    except GhiaError as e:
        error = click.style("ERROR", fg="red", bold=True)
        click.echo(f"{error}: {e}", err=True)
        sys.exit(10)

if __name__ == "__main__":
    main()
    