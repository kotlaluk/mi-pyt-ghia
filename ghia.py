import click
import requests
import configparser

def validate_reposlug(ctx, param, reposlug):
    pass

def validate_auth(ctx, param, config_auth):
    pass

def validate_rules(ctx, param, config_rules):
    pass

@click.command()
@click.argument("REPOSLUG", required=True, callback=validate_reposlug)
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