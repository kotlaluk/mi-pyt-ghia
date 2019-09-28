import click
import requests
import configparser
import re
import sys
import json

GITHUB_URL = "https://api.github.com/repos/"

class GhiaError(Exception):
    pass

class Issue:
    def __init__(self, number, url, title, body, labels, assignees):
        self.number = number
        self.url = url
        self.title = title
        self.body = body
        self.labels = labels
        self.assignees = assignees

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
            raise click.BadParameter("incorrect configuration format")
        return auth_parser["github"]["token"]
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
        try:
            fallback = rules_parser["fallback"]["label"]
            if fallback is not None:
                rules.update({"fallback":fallback})
        except KeyError:
            pass

        # Handle patterns
        for key, value in rules_parser["patterns"].items():
            rules[key] = dict()
            rules[key]["any"] = list()
            rules[key]["title"] = list()
            rules[key]["text"] = list()
            rules[key]["label"] = list()
            for line in value.split("\n"):
                rule = line.split(":")
                if len(rule) > 1:
                    rules[key][rule[0]].append(re.compile(":".join(rule[1:])))

        return rules

    except KeyError:
        raise click.BadParameter("incorrect configuration format")

def process_issue(issue, reposlug, strategy, rules, dry_run):
    pass

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
                number = i["number"]
                url = i["url"]
                title = i["title"]
                body = i["body"]
                labels = [x["name"] for x in i["labels"]]
                assignees = [x["login"] for x in i["assignees"]]
                issue = Issue(number, url, title, body, labels, assignees)

                # Process the issue
                try:
                    process_issue(issue, reposlug, strategy, rules, dry_run)
                except GhiaError as e:
                    error = click.style("ERROR", fg="red", bold=True)
                    click.echo(f"{error}: {e}")

            # Go to the next page
            try:
                issues_url = response.links['next']['url']
            except KeyError:
                issues_url = None
    except requests.HTTPError:
        raise GhiaError(f"Could not list issues for repository {reposlug}")

@click.command()
@click.argument("reposlug", metavar="REPOSLUG", required=True, callback=validate_reposlug)
@click.option("-s", "--strategy", help="How to handle assignment collisions.", type=click.Choice(["append", "set", "change"], case_sensitive=False), default="append", show_default=True)
@click.option("-d", "--dry-run", help="Run without making any changes.", is_flag=True)
@click.option("-a", "--config-auth", help="File with authorization configuration.", metavar="FILENAME", required=True, callback=validate_auth)
@click.option("-r", "--config-rules", help="File with assignment rules configuration.", metavar="FILENAME", required=True, callback=validate_rules)
def main(reposlug, strategy, config_auth, config_rules, dry_run):
    """ CLI tool for automatic issue assigning of GitHub issues"""
    try:
        process_repository(reposlug, strategy, config_auth, config_rules, dry_run)
    except GhiaError as e:
        error = click.style("ERROR", fg="red", bold=True)
        click.echo(f"{error}: {e}")
        sys.exit(10)

if __name__ == "__main__":
    main()