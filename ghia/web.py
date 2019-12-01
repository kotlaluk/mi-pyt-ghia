import os
import flask
import requests
from click import BadParameter

from .github import GhiaError, create_issue, process_issue, prepare_session,\
                    update_github
from .validators import validate_auth, validate_rules, validate_signature


app = flask.Flask(__name__)


def read_config():
    config = dict()
    config["rules"] = dict()
    config["auth"] = dict()

    # Read environment variables
    try:
        config["auth"]["user"] = os.environ["GITHUB_USER"]
        if len(config["auth"]["user"]) == 0:
            raise GhiaError("No GitHub user specified")
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
            except BadParameter:
                errors += 1
            try:
                a = dict()
                a = validate_auth(None, None, file)
                config["auth"].update(a)
            except BadParameter:
                errors += 1
            if errors >= 2:
                raise GhiaError(f"Invalid format of configuration file {file}")
    except KeyError:
        raise GhiaError("No configuration files found")
    return config


def process_get(config):
    without_fallback = {login: config["rules"][login]
                        for login in config["rules"]
                        if login != "fallback"}
    try:
        fallback = config["rules"]["fallback"]
    except KeyError:
        fallback = None
    return flask.render_template("index.html", user=config["auth"]["user"],
                                 rules=without_fallback, fallback=fallback)


def process_post_ping(request_payload):
    app.logger.info("Received PING event")
    return "Ping successful"


def process_post_issues(request_payload, config, session):
    app.logger.info("Received ISSUES event")
    if request_payload["action"] in ("opened", "edited",
                                     "transferred", "reopened",
                                     "assigned", "unassigned",
                                     "labeled", "unlabeled"):
        payload = request_payload["issue"]
        issue = create_issue(payload)

        process_issue(issue, "append", config["rules"])
        update_github(issue, session)
        app.logger.info("Issue sent successfully")
        return f"Issue {issue.number} ({issue.title}) was successfully updated."
    else:
        flask.abort(501)


@app.route("/", methods=["GET", "POST"])
def index():
    config = read_config()

    if flask.request.method == "GET":
        return process_get(config)

    if flask.request.method == "POST":
        # Perform validation if present
        try:
            signature = flask.request.headers["X-Hub-Signature"]
            if not validate_signature(str(config["auth"]["secret"]),
                                      flask.request.data, signature):
                flask.abort(401)
        except KeyError:
            pass

        # Prepare session
        session = prepare_session(config['auth']['token'])

        # Process received action
        try:
            event = flask.request.headers["X-GitHub-Event"]
            if event == "ping":
                return process_post_ping(flask.request.json)
            elif event == "issues":
                return process_post_issues(flask.request.json, config, session)
            else:
                flask.abort(501)
        except KeyError:
            flask.abort(400)
