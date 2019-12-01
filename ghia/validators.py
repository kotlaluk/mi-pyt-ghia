import re
import hmac
import configparser
from click import BadParameter


def validate_reposlug(ctx, param, reposlug):
    if re.match("^[\\w-]+\\/[\\w-]+$", reposlug):
        return reposlug
    else:
        raise BadParameter("not in owner/repository format")


def validate_auth(ctx, param, config_auth):
    try:
        auth_parser = configparser.ConfigParser()
        auth_parser.read(config_auth)
        if "token" not in auth_parser["github"]:
            raise KeyError
        return auth_parser["github"]
    except KeyError:
        raise BadParameter("incorrect configuration format")


def validate_rules(ctx, param, config_rules):
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
    digest_mode, signature = header_signature.split("=")
    mac = hmac.new(bytes(secret, "ascii"), msg=bytes(data, "ascii"),
                   digestmod=digest_mode)
    return hmac.compare_digest(signature, mac.hexdigest())
