"""
.. module:: web

Module web contains flask web application that shows the current configuration
in a static web page, and listens to GitHub webhooks *ping* and *issues*.
"""

import os
import flask
import requests
from click import BadParameter

from .github import GhiaError, create_issue, process_issue, prepare_session,\
                    update_github
from .validators import validate_auth, validate_rules, validate_signature


app = flask.Flask(__name__)


def read_config():
    """Read the configuration provided by environment variables.

    Prepares a dictionary containing configuration entries. Reads value from
    GITHUB_USER environment variable and attempts to parse configuration files
    provided in GHIA_CONFIG environment variables.

    The files may contain authentication or rules configuration. The resulting
    dictionary is nested, containing fields "auth" and "rules" in the first
    level.

    Raises:
        GhiaError: if an error occurs during loading/parsing of the
                   configuration files

    Returns:
        dict: dictionary containing the loaded configuration entries, with "rules" and "auth" keys
    """

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
    """Process GET request towards the web application.

    Args:
        config (dict): prepared config dictionary by :py:func:`read_config`

    Returns:
        a static flask webpage containing information about the current
        configuration
    """

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
    """Process received ping event.

    Args:
        request_payload ([type]): dictionary representing JSON format of the
                                  received payload from the ping event

    Returns:
        str: message "Ping successful"
    """

    app.logger.info("Received PING event")
    return "Ping successful"


def process_post_issues(request_payload, config, session):
    """Process received issues event.

    Validates the action in the received issues event. If the action is one of
    Calls "opened", "edited", "transferred", "reopened", "assigned",
    "unassigned", "labeled", or "unlabeled", extracts information about the
    issue from the received payload and creates an `py:class:`Issue` object.

    After the `py:class:`Issue` object is created, calls :py:func:`process_issue`
    to perform processing of the issue according to currently valid config
    and calls :py:func:`update_github` to update the issue on GitHub.

    Args:
        request_payload ([type]): dictionary representing JSON format of the
                                  received payload from the issues event
        config (dict): prepared config dictionary by :py:func:`read_config`
        session (:py:class:`requests.Session`): an initialized and prepared
                                                session object to use for
                                                updating the issue on GitHub

    Returns:
        str: message informing that the issue was updated
    """

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
    """Route function for the flask web application.

    The flask web application listens on "/" path for incoming GET and POST
    requests. If it receives a GET requests, :py:func:`process_get` is called
    to show a static webpage containing information about current configuration.

    If a POST request is received, firstly its validation is performed (in case
    it contains "X-Hub-Signature" header). Subsequently, the reques action is
    read from "X-GitHub-Event" header. If the action is *ping* or *issues*
    event, the corresponding function is called to process the action.

    The application may respond with following HTTP error codes:
        - 501 if an unsupported action is received
        - 401 if the validation of the signature fails
        - 400 if the incoming request has an invalid format
    """

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
