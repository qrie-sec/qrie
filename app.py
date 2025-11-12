#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.core_stack import CoreStack
from stacks.web_stack import WebStack

app = cdk.App()

account = app.node.try_get_context("account") or os.environ.get("CDK_DEFAULT_ACCOUNT")
region  = app.node.try_get_context("region")  or os.environ.get("CDK_DEFAULT_REGION")
env_kwargs = {"env": cdk.Environment(account=account, region=region)} if account and region else {}

core = CoreStack(
    app, "QrieCore",
    viewer_trusted_account_id = app.node.try_get_context("viewer_trusted_account_id"),
    customer_org_id           = app.node.try_get_context("customer_org_id"),
    **env_kwargs,
)

WebStack(app, "QrieWeb", ui_domain=app.node.try_get_context("ui_domain"), **env_kwargs)

app.synth()
