"""
.. module:: validators

This module contains validation functions that are used as callbacks for
validating user input from CLI app, validate contents of configuration files and
received payload messages.
"""

import re
import hmac
import configparser
from click import BadParameter


def validate_reposlug(ctx, param, reposlugs):
    """Callback to validate the provided reposlugs.

    The function checks whether the provided *reposlugs* are in owner/
    repository format.

    Args:
        ctx: context object obtained from click
        param: parameter object obtained from click
        reposlugs (tuple): one or more GitHub reposlugs in owner/repository format

    Raises:
        BadParameter: if any of the provided *reposlugs* is not in
                      owner/repository format

    Returns:
        tuple: the provided *reposlugs*, if valid
    """

    for reposlug in reposlugs:
        if not re.match("^[\\w-]+\\/[\\w-]+$", reposlug):
            raise BadParameter("not in owner/repository format")
    return reposlugs


def validate_auth(ctx, param, config_auth):
    """Callback to validate the provided authentication file.

    The function verifies the provided authentication file, especially the
    presence of "token" key in the "github" section.

    Args:
        ctx: context object obtained from click
        param: parameter object obtained from click
        config_auth (str): name of the file containing configuraion for
                           authentication

    Raises:
        BadParameter: if the provided file has incorrect configuration format

    Returns:
        dict: contents of the "github" section from the provided file
    """

    try:
        auth_parser = configparser.ConfigParser()
        auth_parser.read(config_auth)
        if "token" not in auth_parser["github"]:
            raise KeyError
        return auth_parser["github"]
    except KeyError:
        raise BadParameter("incorrect configuration format")


def validate_rules(ctx, param, config_rules):
    """Callback to validate the provided file with rules.

    The rules are loaded from the file provided in *config_rules* parameter and
    processed to a nested dictionary. In the first level, the keys of the
    dictionary are the labels used in the rules and "fallback" key (if present
    in the rules). The second level keys are "title", "text", "label" or "any"
    (applicable for non-fallback rules). For these keys, the value is a list of
    compiled regular expression objects. These objects should be used to match
    the respective part of a GitHub issue.

    Args:
        ctx: context object obtained from click
        param: parameter object obtained from click
        config_rules (str): name of the file containing the rules for issue
                            assignment

    Raises:
        BadParameter: if the provided file has incorrect configuration format

    Returns:
        dict: nested dictionary containing loaded issue assignment rules.
    """

    try:
        rules_parser = configparser.ConfigParser()
        rules_parser.optionxform = str
        rules_parser.read(config_rules)
        if "patterns" not in rules_parser:
            raise BadParameter("incorrect configuration format")
        rules = dict()

        # Handle fallback
        if rules_parser.has_section("fallback"):
            if rules_parser.has_option("fallback", "label"):
                rules["fallback"] = rules_parser["fallback"]["label"]
            else:
                raise KeyError

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
                    rules[key][rule[0]].append(re.compile(rule[1],
                                               re.IGNORECASE))

        return rules

    except (KeyError, re.error):
        raise BadParameter("incorrect configuration format")


def validate_signature(secret, data, header_signature):
    """Validate GitHub signature.

    Validates payloads received in requests from GitHub. GitHub uses an HMAC
    hexdigest to compute the hash of a payload and sets the result in the
    X-Hub-Signature header. This function computes the HMAC hexdigest from
    *data* and *secret* and compares it to *header_signature*.

    Args:
        secret (str): secret token set up with GitHub to secure messages
        data (str): payload from the request
        header_signature (str): value obtained from the X-Hub-Signature GitHub
                                header

    Returns:
        bool: True if the values match, False otherwise
    """

    digest_mode, signature = header_signature.split("=")
    mac = hmac.new(bytes(secret, "ascii"), msg=data,
                   digestmod=digest_mode)
    return hmac.compare_digest(signature, mac.hexdigest())
