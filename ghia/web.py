import os
import flask
import hmac
import click
import requests

from .github import GhiaError, create_issue, process_issue
from .validators import validate_auth, validate_rules

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
