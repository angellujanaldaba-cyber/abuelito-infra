#!/usr/bin/env python3
import aws_cdk as cdk
from abuelito_infra.abuelito_infra_stack import AbuelitoInfraStack

app = cdk.App()

AbuelitoInfraStack(
    app,
    "AbuelitoInfraStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region")
    )
)

app.synth()
