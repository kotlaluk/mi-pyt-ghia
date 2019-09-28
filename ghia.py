import click
import requests
import configparser
import re

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
                    rules[key][rule[0]].append(":".join(rule[1:]))

        return rules

    except KeyError:
        raise click.BadParameter("incorrect configuration format")

@click.command()
@click.argument("reposlug", metavar="REPOSLUG", required=True, callback=validate_reposlug)
@click.option("-s", "--strategy", help="How to handle assignment collisions.", type=click.Choice(["append", "set", "change"], case_sensitive=False), default="append", show_default=True)
@click.option("-d", "--dry-run", help="Run without making any changes.", is_flag=True)
@click.option("-a", "--config-auth", help="File with authorization configuration.", metavar="FILENAME", required=True, callback=validate_auth)
@click.option("-r", "--config-rules", help="File with assignment rules configuration.", metavar="FILENAME", required=True, callback=validate_rules)
def main(reposlug, strategy, dry_run, config_auth, config_rules):
    """ CLI tool for automatic issue assigning of GitHub issues"""
    if dry_run:
        print("dry_run")
    else:
        print("not dry_run")

if __name__ == "__main__":
    main()