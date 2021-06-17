#! /usr/bin/env python3

"Disable specific security controls (awaiting full terraform support - see https://github.com/hashicorp/terraform-provider-aws/issues/11624)"

import boto3
import click
import json
import yaml
import datetime

account_id = boto3.client('sts').get_caller_identity().get('Account')

class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()

def read_config(config_file):
    "Read and parse config file"

    file = None
    try:
        with open(config_file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    except IOError:
        click.secho(f"Config '{config_file}' not accessible", fg="red")
        raise
    finally:
        try:
            if file:
                file.close()
        except IOError:
            pass

    return config

def reusable_arn(arn, region):
    return arn.replace(region, "{region}").replace(account_id, "{account}")

def parse_arn(arn, region):
    return arn.format(region=region, account_id=account_id)

@click.group()
def cli():
    pass

@cli.command(name="dump")
@click.option('--region', '-r', required=True, help='AWS region you want to work with')
@click.option('--verbose', '-v', is_flag=True, default=False, help='Verbose output', show_default=True)
def dump(region, verbose):
    """
    For each susbscribed standard, collects and dumps each security hub control and
    its status to standard output.

    The same file structure is used when applying changes to it.
    """
    if verbose:
        click.secho("Collect controls settings for the security hub", bold=True)

    client = boto3.client('securityhub', region_name=region)

    subs = client.get_enabled_standards()

    all_controls = {}
    for s in subs["StandardsSubscriptions"]:
        standard = reusable_arn(arn=s['StandardsArn'], region=region)
        all_controls[standard] = {}
        all_controls[standard]['subscription_arn'] = reusable_arn(
            arn=s['StandardsSubscriptionArn'],
            region=region,
        )
        all_controls[standard]['status'] = s['StandardsStatus']

        controls = client.describe_standards_controls(
            StandardsSubscriptionArn=s["StandardsSubscriptionArn"]
        )

        if verbose:
            click.secho(f"\n\nControls for {standard}", bold=True)
            # print(json.dumps(controls, indent=2, cls=DateTimeEncoder))

        details = {}
        for c in controls["Controls"]:
            details[c['ControlId']] = {
                "arn": reusable_arn(
                    arn=c['StandardsControlArn'],
                    region=region,
                ),
                "title": c['Title'],
                "description": c['Description'],
                "severity": c['SeverityRating'],
                "status": c['ControlStatus'],
                "disabled_reason": c['DisabledReason'] if 'DisabledReason' in c else "n/a",
            }
            if verbose:
                click.echo(f"{c['ControlId']}|{c['ControlStatus']}|{c['StandardsControlArn']}|{c['Title']}")
        all_controls[standard]['controls']= details
    
    click.echo(yaml.dump(all_controls, sort_keys=False))

# to update a particular control:
# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/securityhub.html#SecurityHub.Client.update_standards_control
@cli.command(name="apply")
@click.option('-c', '--config', type=click.Path(exists=True), help='Configuration file', required=False)
@click.option('--region', '-r', required=True, help='AWS region you want to work with')
@click.option('--dry-run', '-d', is_flag=True, default=False, help='Dry run, show what will be done but no actual changes are done', show_default=True)
@click.option('--verbose', '-v', is_flag=True, default=False, help='Verbose output', show_default=True)
def dump(config, region, dry_run, verbose):
    """
    Reads the control status from the configs and applies (if changes are detected).
    """
    if verbose:
        click.secho("Apply controls settings for the security hub", bold=True)

    config = read_config(config_file=config)

    client = boto3.client('securityhub', region_name=region)

    subs = client.get_enabled_standards()

    for s in subs["StandardsSubscriptions"]:
        standard = reusable_arn(arn=s['StandardsArn'], region=region)
        click.echo(f"Working with standard: {standard}")

        controls = client.describe_standards_controls(
            StandardsSubscriptionArn=s["StandardsSubscriptionArn"]
        )
        ds = config[standard]
        for c in controls["Controls"]:
            id = c['ControlId']
            current_status = c['ControlStatus']
            desired_status = ds['controls'][id]['status'].upper()

            if desired_status not in ("ENABLED", "DISABLED"):
                click.secho(
                    f"Status should be either 'ENABLED' or 'DISABLED', got {desired_status}. Skipping",
                    fg="red"
                )
            elif current_status == desired_status:
                if verbose:
                    click.echo(f"\t{id} --> current status {current_status} is the same as desired, no action needed")
            elif dry_run:
                click.echo(f"\t{id} --> update status from {current_status} to {desired_status} (but we're in dry run mode so no action taken).")
            else:
                click.echo(f"\t{id} --> update status from {current_status} to {desired_status}")

                response = client.update_standards_control(
                    StandardsControlArn=c['StandardsControlArn'],
                    ControlStatus=desired_status,
                    DisabledReason="" if desired_status == 'ENABLED' else ds['controls'][id]['disabled_reason']
                )


if __name__ == '__main__':
    cli()
