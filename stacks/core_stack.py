from typing import Optional
import aws_cdk as cdk
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_dynamodb as ddb,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_iam as iam,
    aws_cognito as cognito,
    aws_events as events,
    aws_events_targets as targets,
    aws_ssm as ssm,
)

class CoreStack(Stack):
    """
    QOP core (per-customer, per-region): EventBridge (customer) -> SQS (this stack) -> Lambda.

    V0 gating strategy for cross-account EventBridge -> SQS:
      - Prefer Org-ID scoping (auto-includes any new accounts in that Org).
      - If no Org-ID, fall back to requiring the EventBridge rule name prefix only
        (matches your customer bootstrap template). This is acceptable for MVP;
        you can add allow-listing or exact RuleARNs later without breaking callers.
    """

    def __init__(self,
                 scope: cdk.App,
                 construct_id: str,
                 *,
                 viewer_trusted_account_id: Optional[str] = None,
                 customer_org_id: Optional[str] = None,  # prefer this if available
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)



        # ------    BEGIN: DynamoDB (Tables) ------
        # 
        # 1. Accounts (qrie_accounts) Table - Customer account registry
        # 2. Inventory (qrie_resources) Table
        # 3. Findings (qrie_findings) Table
        # 4. Policies (qrie_policies) Table - Policy definitions and configurations
        # 5. Summary (qrie_summary) Table - Cached summaries (dashboard, findings, etc.)
        # 
        accounts = ddb.Table(
            self, "QrieAccounts",
            table_name="qrie_accounts",
            partition_key=ddb.Attribute(name="AccountId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        resources = ddb.Table(
            self, "QrieResources",
            table_name="qrie_resources",
            partition_key=ddb.Attribute(name="AccountService", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="ARN", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        findings = ddb.Table(
            self, "QrieFindings",
            table_name="qrie_findings",
            partition_key=ddb.Attribute(name="ARN", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="Policy", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Add GSI for querying findings by account/service with state
        findings.add_global_secondary_index(
            index_name="AccountService-State-index",
            partition_key=ddb.Attribute(name="AccountService", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="State", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL
        )
        
        policies = ddb.Table(
            self, "QriePolicies",
            table_name="qrie_policies",
            partition_key=ddb.Attribute(name="PolicyId", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # Add GSI for querying policies by service
        policies.add_global_secondary_index(
            index_name="ServiceIndex",
            partition_key=ddb.Attribute(name="Service", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL
        )
        
        summary = ddb.Table(
            self, "QrieSummary",
            table_name="qrie_summary",
            partition_key=ddb.Attribute(name="Type", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        #
        # ------    END: DynamoDB (Tables) ------




        # ------    BEGIN: SQS (event ingress) ------
        # 
        dlq = sqs.Queue(self, "QrieEventsDLQ",
                        retention_period=Duration.days(7))

        queue_name = "qrie-events-queue"
        events_queue = sqs.Queue(
            self, "QrieEventsQueue",
            queue_name=queue_name,
            visibility_timeout=Duration.minutes(16),
            dead_letter_queue=sqs.DeadLetterQueue(queue=dlq, max_receive_count=5)
            # SSE-SQS default is fine for V0
        )

        # ---------- Cross-account EventBridge -> SQS policy ----------
        # Allow cross-account EventBridge role from customer bootstrap template
        # Role name pattern: QrieEventsToSqs-{AccountId}-{Region}
        # Note: EventBridge assumes this role to send messages, not the service principal directly
        events_queue.add_to_resource_policy(iam.PolicyStatement(
            sid="AllowCrossAccountEventBridgeRole",
            effect=iam.Effect.ALLOW,
            principals=[iam.AnyPrincipal()],
            actions=["sqs:SendMessage"],
            resources=[events_queue.queue_arn],
            conditions={
                "StringLike": {
                    "aws:PrincipalArn": f"arn:aws:iam::*:role/QrieEventsToSqs-*-{self.region}"
                }
            },
        ))
        #
        # ------    END: SQS (event ingress) ------



        # ------    BEGIN: Lambda Functions    ------
        # 1. Policy Scanner
        # 2. Event Processor  
        # 3. Inventory Generator (dedicated lambda)
        # 4. Unified API Handler (replaces separate API functions)

        
        
        # 1. Policy scanner: read resources, write findings
        #
        policy_scanner_fn = _lambda.Function(
            self, "QriePolicyScanner",
            function_name="qrie_policy_scanner",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="scan_processor.scan_handler.scan_policy",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            log_group=logs.LogGroup.from_log_group_name(self, "QriePolicyScannerLogGroup", "/aws/lambda/qrie_policy_scanner"),
            environment={
                "ACCOUNTS_TABLE": accounts.table_name,
                "RESOURCES_TABLE": resources.table_name,
                "FINDINGS_TABLE": findings.table_name,
                "POLICIES_TABLE": policies.table_name
            }
        )
        logs.LogRetention(
            self,
            "QriePolicyScannerLogRetention",
            log_group_name="/aws/lambda/qrie_policy_scanner",
            retention=logs.RetentionDays.ONE_WEEK,
        )
        accounts.grant_read_data(policy_scanner_fn)
        resources.grant_read_data(policy_scanner_fn)
        findings.grant_write_data(policy_scanner_fn)
        policies.grant_read_data(policy_scanner_fn)
        
        # Add cross-account role assumption permissions for policy scanner lambda
        policy_scanner_fn.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sts:AssumeRole"],
            resources=[f"arn:aws:iam::*:role/QrieReadOnly-*"],
            conditions={
                "StringEquals": {
                    "sts:ExternalId": f"qrie-{self.account}-2024"
                }
            }
        ))

        
        # 2. Event processor: consume queue, upsert resources/findings
        #
        event_processor_fn = _lambda.Function(
            self, "QrieEventProcessor",
            function_name="qrie_event_processor",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="event_processor.event_handler.process_event",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            log_group=logs.LogGroup.from_log_group_name(self, "QrieEventProcessorLogGroup", "/aws/lambda/qrie_event_processor"),
            environment={
                "ACCOUNTS_TABLE": accounts.table_name,
                "RESOURCES_TABLE": resources.table_name,
                "FINDINGS_TABLE": findings.table_name,
                "POLICIES_TABLE": policies.table_name
            }
        )
        logs.LogRetention(
            self,
            "QrieEventProcessorLogRetention",
            log_group_name="/aws/lambda/qrie_event_processor",
            retention=logs.RetentionDays.ONE_WEEK,
        )
        events_queue.grant_consume_messages(event_processor_fn)
        accounts.grant_read_data(event_processor_fn)
        resources.grant_write_data(event_processor_fn)
        findings.grant_write_data(event_processor_fn)
        policies.grant_read_data(event_processor_fn)
        
        # Add SQS queue trigger to Lambda function
        _lambda.EventSourceMapping(
            self, "QrieEventsMapping",
            target=event_processor_fn,
            event_source_arn=events_queue.queue_arn,
            batch_size=10,
            enabled=True
        )

        # 3. Inventory Generator: Generate inventory for all services
        #
        inventory_generator_fn = _lambda.Function(
            self, "QrieInventoryGenerator",
            function_name="qrie_inventory_generator",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="inventory_generator.inventory_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            log_group=logs.LogGroup.from_log_group_name(self, "QrieInventoryGeneratorLogGroup", "/aws/lambda/qrie_inventory_generator"),
            environment={
                "ACCOUNTS_TABLE": accounts.table_name,
                "RESOURCES_TABLE": resources.table_name
            }
        )
        logs.LogRetention(
            self,
            "QrieInventoryGeneratorLogRetention",
            log_group_name="/aws/lambda/qrie_inventory_generator",
            retention=logs.RetentionDays.ONE_WEEK,
        )
        accounts.grant_read_data(inventory_generator_fn)
        resources.grant_read_write_data(inventory_generator_fn)
        
        # Add cross-account role assumption permissions for inventory generator
        inventory_generator_fn.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sts:AssumeRole"],
            resources=[f"arn:aws:iam::*:role/QrieReadOnly-*"],
            conditions={
                "StringEquals": {
                    "sts:ExternalId": f"qrie-{self.account}-2024"
                }
            }
        ))
        
        # Anti-Entropy Strategy: Weekly full inventory scan (Saturday midnight UTC)
        events.Rule(
            self, "WeeklyInventorySchedule",
            schedule=events.Schedule.cron(minute="0", hour="0", week_day="SAT"),
            targets=[targets.LambdaFunction(
                inventory_generator_fn,
                event=events.RuleTargetInput.from_object({
                    "service": "all",
                    "scan_type": "anti-entropy"  # Anti-entropy scan updates drift metrics
                })
            )],
            description="Weekly full inventory scan - Saturday 00:00 UTC (anti-entropy)"
        )
        
        # Anti-Entropy Strategy: Daily policy scans (4 AM UTC)
        events.Rule(
            self, "DailyPolicyScanSchedule",
            schedule=events.Schedule.cron(minute="0", hour="4"),
            targets=[targets.LambdaFunction(
                policy_scanner_fn,
                event=events.RuleTargetInput.from_object({
                    "scan_type": "anti-entropy"  # Anti-entropy scan updates drift metrics
                })
            )],
            description="Daily policy scan - 04:00 UTC (anti-entropy)"
        )
        
        
        # 4. Unified API Handler: Single Lambda URL for all UI endpoints
        #
        api_handler_fn = _lambda.Function(
            self, "QrieApiHandler",
            function_name="qrie_api_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="api.api_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.minutes(15),
            log_group=logs.LogGroup.from_log_group_name(self, "QrieApiHandlerLogGroup", "/aws/lambda/qrie_api_handler"),
            environment={
                "ACCOUNTS_TABLE": accounts.table_name,
                "RESOURCES_TABLE": resources.table_name,
                "FINDINGS_TABLE": findings.table_name,
                "POLICIES_TABLE": policies.table_name,
                "SUMMARY_TABLE": summary.table_name
            }
        )
        
        logs.LogRetention(
            self,
            "QrieApiHandlerLogRetention",
            log_group_name="/aws/lambda/qrie_api_handler",
            retention=logs.RetentionDays.ONE_WEEK,
        )
        
        # Grant permissions to all tables
        accounts.grant_read_data(api_handler_fn)
        resources.grant_read_data(api_handler_fn)
        findings.grant_read_data(api_handler_fn)
        policies.grant_read_data(api_handler_fn)
        summary.grant_read_write_data(api_handler_fn)
        
        api_url = api_handler_fn.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"],
                allowed_methods=[_lambda.HttpMethod.GET],
                allowed_headers=["Content-Type", "Authorization"],
                max_age=Duration.hours(1)
            )
        )
        
        # API URL will be output in the final outputs section below
        #
        # ------    END: Lambda Functions    ------





        # ---------- Cross-account viewer role (COMMENTED OUT FOR MVP) ----------
        # This would allow customer's AWS account to directly access QOP DynamoDB tables
        # Not needed for MVP since we have Lambda Function URLs for API access
        # Can be re-enabled later if cross-account direct DB access is required
        #
        # if viewer_trusted_account_id:
        #     viewer_role = iam.Role(
        #         self, "QrieCustomerViewer",
        #         role_name="QrieCustomerViewer",
        #         assumed_by=iam.AccountPrincipal(viewer_trusted_account_id)
        #     )
        #     iam.Policy(self, "ViewerReadPolicy",
        #         statements=[iam.PolicyStatement(
        #             actions=["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
        #             resources=[resources.table_arn, findings.table_arn]
        #         )]
        #     ).attach_to_role(viewer_role)



        # ---------- Cognito Identity Pool (REMOVED FOR MVP) ----------
        # This setup allowed browsers to directly access DynamoDB tables via Cognito Identity Pool
        # Not needed for MVP since we have Lambda Function URLs (FindingsApiUrl, InventoryApiUrl)
        # UI will call these APIs instead of direct DynamoDB access
        # This simplifies security model and reduces attack surface


        # Outputs
        cdk.CfnOutput(self, "EventsQueueUrl", value=events_queue.queue_url)
        # if viewer_trusted_account_id:
        #     cdk.CfnOutput(self, "ViewerRoleArn", value=viewer_role.role_arn)
        cdk.CfnOutput(self, "ResourcesTable", value=resources.table_name)
        cdk.CfnOutput(self, "FindingsTable", value=findings.table_name)
        cdk.CfnOutput(self, "PoliciesTable", value=policies.table_name)
        cdk.CfnOutput(self, "QopAccountId", value=self.account)
        cdk.CfnOutput(self, "ApiUrl", value=api_url.url)
        cdk.CfnOutput(self, "InventoryGeneratorArn", value=inventory_generator_fn.function_arn)
