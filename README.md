# AWS Security Hub controls manager

AWS Security hub comes with an extensive set of controls which can be disabled if you believe there are reasons to.

However, you typically need to do that across multiple regions and potentially multiple accounts, making this a tedious process to do it manually.

Terraform is not supporting the management of individuals controls (yet, [but it has been requested for a while now](https://github.com/hashicorp/terraform-provider-aws/issues/11624)).

This simple script allows you to dump the controls you have in place and `apply` them to other regions and/or accounts.

## Usage

```console
$ ./aws-sh-controls-mngr.py --help
Usage: aws-sh-controls-mngr.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  apply  Reads the control status from the configs and applies (if changes...
  dump   For each susbscribed standard, collects and dumps each security
         hub...

$ ./aws-sh-controls-mngr.py dump -r eu-central-1 > ./out.yaml

$ ./aws-sh-controls-mngr.py apply -c ./out.yaml -r eu-central-1
Working with standard: arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0
Working with standard: arn:aws:securityhub:{region}::standards/aws-foundational-security-best-practices/v/1.0.0
```
