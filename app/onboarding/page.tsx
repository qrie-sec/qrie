export default function OnboardingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-950/50 backdrop-blur">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-2xl bg-emerald-400/10 ring-1 ring-emerald-400/40 flex items-center justify-center">
              <span className="text-emerald-300 font-black text-lg">q</span>
            </div>
            <span className="font-semibold tracking-wide text-lg">qrie</span>
          </div>
          <h1 className="text-4xl font-black tracking-tight">Get Started with Qrie</h1>
          <p className="mt-3 text-slate-400 text-lg">Deploy your CNAPP solution in minutes with our guided setup process</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Overview Section */}
        <div className="mb-16">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-blue-500/10 ring-1 ring-blue-400/40 flex items-center justify-center">
                <span className="text-blue-300 text-sm">📋</span>
              </div>
              Onboarding Overview
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">1</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">Initial Contact</h3>
                    <p className="text-sm text-slate-400">Contact Qrie for a personalized demo and consultation</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">2</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">Agreement</h3>
                    <p className="text-sm text-slate-400">Sign a simple order form to get started</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">3</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">QOP Deployment</h3>
                    <p className="text-sm text-slate-400">We deploy your per-region QOP stacks and provide SQS Queue ARNs</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">4</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">Event Connection</h3>
                    <p className="text-sm text-slate-400">Your team deploys CloudFormation stacks to forward events</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">5</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">Verification</h3>
                    <p className="text-sm text-slate-400">We confirm events are flowing and your UI shows live data</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-emerald-300 text-xs font-bold">✓</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-200">Ready to Go</h3>
                    <p className="text-sm text-slate-400">Your dedicated Qrie instance is live and monitoring</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Implementation Steps */}
        <div className="space-y-12">
          {/* Step 1: Initial Contact */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <div className="bg-gradient-to-r from-emerald-500/10 to-blue-500/10 border-b border-slate-800 p-6">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center">
                  <span className="text-emerald-300 font-bold text-lg">1</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Initial Contact</h2>
                  <p className="text-slate-400">Contact Qrie for a personalized demo and consultation</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <p className="text-slate-300 mb-4">
                Reach out to the Qrie team to schedule a demo and discuss your cloud security monitoring needs. 
                We&rsquo;ll walk through your AWS environment and explain how Qrie can provide comprehensive visibility 
                into your cloud infrastructure.
              </p>
              <div className="rounded-lg bg-blue-500/5 border border-blue-500/20 p-4">
                <h3 className="font-semibold text-blue-300 mb-2">What to expect</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• 30-minute product demonstration</li>
                  <li>• Discussion of your specific security requirements</li>
                  <li>• Architecture overview and deployment planning</li>
                  <li>• Pricing and contract terms review</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Step 2: Agreement */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border-b border-slate-800 p-6">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-blue-500/20 ring-1 ring-blue-400/40 flex items-center justify-center">
                  <span className="text-blue-300 font-bold text-lg">2</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Agreement</h2>
                  <p className="text-slate-400">Sign a simple order form to get started</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <p className="text-slate-300 mb-4">
                Once you&rsquo;re ready to proceed, we&rsquo;ll provide a straightforward order form that outlines the 
                service terms, pricing, and deployment timeline.
              </p>
              <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-4">
                <h3 className="font-semibold text-emerald-300 mb-2">Agreement includes</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Service level agreements (SLAs)</li>
                  <li>• Data processing and privacy terms</li>
                  <li>• Regional deployment specifications</li>
                  <li>• Support and maintenance coverage</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Step 3: QOP Deployment */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <div className="bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border-b border-slate-800 p-6">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-purple-500/20 ring-1 ring-purple-400/40 flex items-center justify-center">
                  <span className="text-purple-300 font-bold text-lg">3</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">QOP Deployment</h2>
                  <p className="text-slate-400">We deploy your per-region QOP stacks and provide SQS Queue ARNs</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <p className="text-slate-300 mb-4">
                The Qrie team deploys your dedicated Qrie-on-Premises (QOP) infrastructure in your specified AWS regions. 
                This includes all the backend processing, storage, and UI components needed for your security monitoring.
              </p>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-lg bg-indigo-500/5 border border-indigo-500/20 p-4">
                  <h3 className="font-semibold text-indigo-300 mb-2">What gets deployed</h3>
                  <ul className="text-sm text-slate-300 space-y-1">
                    <li>• SQS queues for event ingestion</li>
                    <li>• Lambda functions for processing</li>
                    <li>• DynamoDB tables for storage</li>
                    <li>• Web UI with CloudFront distribution</li>
                  </ul>
                </div>
                <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-4">
                  <h3 className="font-semibold text-amber-300 mb-2">You receive</h3>
                  <ul className="text-sm text-slate-300 space-y-1">
                    <li>• SQS Queue ARNs for each region</li>
                    <li>• Web UI access credentials</li>
                    <li>• CloudFormation template for setup</li>
                    <li>• Documentation and support contacts</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Step 4: Event Connection */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-500/10 to-emerald-500/10 border-b border-slate-800 p-6">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-indigo-500/20 ring-1 ring-indigo-400/40 flex items-center justify-center">
                  <span className="text-indigo-300 font-bold text-lg">4</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Event Connection</h2>
                  <p className="text-slate-400">Deploy CloudFormation stacks to forward events from your AWS account to Qrie</p>
                </div>
              </div>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="rounded-xl bg-blue-500/5 border border-blue-500/20 p-4">
                <h3 className="font-semibold text-blue-300 mb-2">Before getting started, ensure you have:</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• ✅ Signed agreements and contract</li>
                  <li>• ✅ Confirmation from Qrie team that QOP account is deployed for you</li>
                  <li>• ✅ SQS Queue ARN provided by Qrie team (this is the queue in your dedicated QOP account where your events are processed)</li>
                  <li>• ✅ Admin access to your AWS account (root credentials or IAM user with AdministratorAccess permissions)</li>
                </ul>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-3">Step 4.1: Download CloudFormation Template</h3>
                <div className="rounded-lg bg-slate-950/50 border border-slate-700 p-4">
                  <p className="text-sm text-slate-300 mb-2">Download the bootstrap template for connecting your AWS account:</p>
                  <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                    <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Download Template</div>
                    <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Download the CloudFormation template
curl -fsSL -o qrie-customer-bootstrap.yaml \\
  https://qrie.io/onboarding/customer_bootstrap.yaml`}</code></pre>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    <strong>Alternative:</strong> <a href="/onboarding/customer_bootstrap.yaml" className="text-emerald-300 hover:text-emerald-200 underline">Download directly from browser</a>
                  </p>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-3">Step 4.2: Enable CloudTrail EventBridge Integration</h3>
                <div className="rounded-xl bg-red-500/5 border border-red-500/20 p-4">
                  <h4 className="font-semibold text-red-300 mb-2">⚠️ Critical: CloudTrail EventBridge Integration</h4>
                  <p className="text-sm text-slate-400 mb-2">
                    The EventBridge rules won&rsquo;t trigger without CloudTrail sending events to EventBridge. Enable this if not already configured:
                  </p>
                  <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                    <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Enable CloudTrail → EventBridge</div>
                    <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Option 1: Basic setup (captures ALL services, filtered by EventBridge rules)
aws cloudtrail put-event-selectors \\
  --trail-name <your-existing-trail-name> \\
  --event-selectors '[{
    "ReadWriteType": "WriteOnly",
    "IncludeManagementEvents": true,
    "DataResources": []
  }]' \\
  --region us-east-1

# Option 2: Advanced filtering (only EC2, S3, IAM at CloudTrail level)
aws cloudtrail put-event-selectors \\
  --trail-name <your-existing-trail-name> \\
  --advanced-event-selectors '[{
    "Name": "Log EC2, S3, IAM write events only",
    "FieldSelectors": [
      {"Field": "category", "Equals": ["Management"]},
      {"Field": "readOnly", "Equals": ["false"]},
      {"Field": "eventSource", "Equals": ["ec2.amazonaws.com", "s3.amazonaws.com", "iam.amazonaws.com"]}
    ]
  }]' \\
  --region us-east-1

# Option 3: Create new trail with EventBridge integration
aws cloudtrail create-trail \\
  --name qrie-eventbridge-trail \\
  --s3-bucket-name <your-cloudtrail-bucket> \\
  --include-global-service-events \\
  --is-multi-region-trail \\
  --enable-log-file-validation \\
  --region us-east-1

aws cloudtrail start-logging \\
  --name qrie-eventbridge-trail \\
  --region us-east-1`}</code></pre>
                  </div>

                  <div className="mt-4 rounded-lg bg-purple-500/5 border border-purple-500/20 p-3">
                    <h5 className="font-semibold text-purple-300 text-sm mb-2">💡 Alternative: Use AWS Console</h5>
                    <ul className="text-xs text-slate-400 space-y-1">
                      <li>• Go to CloudTrail → Trails → Select your trail</li>
                      <li>• Under &quot;Event selectors&quot; → Edit</li>
                      <li>• Ensure &quot;Management events&quot; and &quot;Write&quot; are selected</li>
                      <li>• Save changes</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-3">Step 4.3: Deploy CloudFormation Stack</h3>
                <div className="rounded-xl bg-red-500/5 border border-red-500/20 p-4 mb-4">
                  <h4 className="font-semibold text-red-300 mb-2">⚠️ Important: Regional Deployment Strategy</h4>
                  <div className="text-sm text-slate-400 space-y-2">
                    <p><strong>us-east-1 (Required):</strong> Must be deployed to capture IAM events (global service)</p>
                    <p><strong>Other regions:</strong> Deploy in regions where you have EC2, S3, and other regional resources</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-lg bg-slate-950/50 border border-slate-700 p-4">
                    <p className="text-sm text-slate-300 mb-2"><span className="font-medium">Start with us-east-1:</span></p>
                    <ul className="text-xs text-slate-400 space-y-1 ml-4 mb-3">
                      <li>• Navigate to AWS Console in your target account</li>
                      <li>• Search for &quot;CloudShell&quot; and open it</li>
                      <li>• <strong>Set region to us-east-1</strong> (required for IAM events)</li>
                    </ul>
                    <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                      <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Deploy to us-east-1</div>
                      <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Set your QOP SQS ARN and Account ID for us-east-1 (replace with actual values from Qrie team)
AWS_REGION="us-east-1"
QOP_QUEUE_ARN="arn:aws:sqs:$AWS_REGION:<QOP_ACCOUNT_ID>:<your-qrie-queue-us-east-1>"
QOP_ACCOUNT_ID="<QOP_ACCOUNT_ID>"

# Deploy to us-east-1 first (REQUIRED for global services like IAM)
aws cloudformation deploy \\
  --region $AWS_REGION \\
  --stack-name QrieForwardToQOP \\
  --template-file qrie-customer-bootstrap.yaml \\
  --parameter-overrides QopQueueArn="$QOP_QUEUE_ARN" QopAccountId="$QOP_ACCOUNT_ID" \\
  --capabilities CAPABILITY_NAMED_IAM`}</code></pre>
                    </div>
                  </div>

                  <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-4">
                    <h4 className="font-medium text-amber-300 text-sm mb-2">Deploy to Additional Regions</h4>
                    <p className="text-xs text-slate-400 mb-2">Repeat for each region where you have resources to monitor:</p>
                    <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                      <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Additional Regions</div>
                      <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Example: Deploy to us-west-2
AWS_REGION="us-west-2"
QOP_QUEUE_ARN="arn:aws:sqs:$AWS_REGION:<QOP_ACCOUNT_ID>:<your-qrie-queue-us-west-2>"
QOP_ACCOUNT_ID="<QOP_ACCOUNT_ID>"

aws cloudformation deploy \\
  --region $AWS_REGION \\
  --stack-name QrieForwardToQOP \\
  --template-file qrie-customer-bootstrap.yaml \\
  --parameter-overrides QopQueueArn="$QOP_QUEUE_ARN" QopAccountId="$QOP_ACCOUNT_ID" \\
  --capabilities CAPABILITY_NAMED_IAM`}</code></pre>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Step 5: Verification & Go-Live */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
            <div className="bg-gradient-to-r from-emerald-500/10 to-green-500/10 border-b border-slate-800 p-6">
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-xl bg-emerald-500/20 ring-1 ring-emerald-400/40 flex items-center justify-center">
                  <span className="text-emerald-300 font-bold text-lg">5</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Verification & Go-Live</h2>
                  <p className="text-slate-400">Confirm your setup is working correctly with end-to-end testing</p>
                </div>
              </div>
            </div>
            
            <div className="p-6 space-y-6">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-4">
                  <h3 className="font-semibold text-emerald-300 text-sm mb-2">✓ Stack Deployment</h3>
                  <p className="text-xs text-slate-400">Verify all CloudFormation stacks show <code>CREATE_COMPLETE</code> status in each deployed region.</p>
                </div>
                <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-4">
                  <h3 className="font-semibold text-emerald-300 text-sm mb-2">✓ Event Flow</h3>
                  <p className="text-xs text-slate-400">Qrie team confirms test events are received and processed successfully.</p>
                </div>
              </div>

              <div>
                <h3 className="font-semibold text-slate-200 mb-3">End-to-End Testing</h3>
                <div className="rounded-lg bg-slate-950/50 border border-slate-700 p-4">
                  <p className="text-sm text-slate-300 mb-2">Send test events to verify the complete pipeline is working:</p>
                  <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                    <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Test Events (Write Operations Only)</div>
                    <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Test IAM events (only works in us-east-1 due to global service)
aws iam create-user --user-name qrie-test-user
aws iam delete-user --user-name qrie-test-user

# Test S3 write events
aws s3 mb s3://qrie-test-bucket-$(date +%s)
aws s3 rb s3://qrie-test-bucket-$(date +%s)

# Test EC2 write events (use appropriate region)
aws ec2 create-security-group --group-name qrie-test-sg --description "Qrie test security group"
aws ec2 delete-security-group --group-name qrie-test-sg`}</code></pre>
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    <strong>Note:</strong> IAM events only appear in us-east-1 CloudTrail. The Qrie team will confirm receipt of events from all deployed regions and verify they&rsquo;re being processed by your QOP Lambda functions.
                  </p>
                </div>

                <div className="mt-4 rounded-lg bg-blue-500/5 border border-blue-500/20 p-4">
                  <h4 className="font-semibold text-blue-300 mb-2">How to evaluate test results</h4>
                  <div className="text-sm text-slate-300 space-y-2">
                    <p><strong>Web UI (Coming Soon):</strong> The Qrie web interface will display security findings and resource inventory. During initial setup, this UI is still being prepared for your deployment.</p>
                    <p><strong>QOP Account Access:</strong> You have access to your dedicated QOP account where you can:</p>
                    <ul className="text-xs text-slate-400 ml-4 space-y-1">
                      <li>• Monitor Lambda function executions in CloudWatch</li>
                      <li>• Check DynamoDB tables for new findings and resource entries</li>
                      <li>• View SQS queue metrics to confirm event ingestion</li>
                    </ul>
                    <p><strong>Advanced Testing:</strong> Create a non-compliant resource (e.g., an S3 bucket with public read access) to generate a positive security finding that should appear in your QOP DynamoDB tables.</p>
                  </div>
                </div>
              </div>
              
              <div className="rounded-lg bg-slate-950/50 border border-slate-700 p-4">
                <p className="text-sm text-slate-300 mb-2"><span className="font-medium">Security Note:</span></p>
                <p className="text-xs text-slate-400">Your QOP SQS queue only accepts events from the specific EventBridge rules created by this stack (prefix: <code>qrie-forward-*</code>). The queue is not publicly accessible.</p>
              </div>

              <div className="rounded-lg bg-green-500/5 border border-green-500/20 p-4">
                <h3 className="font-semibold text-green-300 mb-2">🎉 Ready to Go!</h3>
                <p className="text-sm text-slate-300">
                  Once verification is complete, your dedicated Qrie instance is live and monitoring your AWS environment. 
                  You&rsquo;ll receive access to your web UI and can start exploring security findings and resource inventory.
                </p>
              </div>
            </div>
          </div>

          {/* Architecture Overview */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 ring-1 ring-indigo-400/40 flex items-center justify-center">
                <span className="text-indigo-300 text-sm">🏗️</span>
              </div>
              What Gets Deployed
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-semibold text-slate-200 mb-3">In Your AWS Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <code className="text-emerald-300">QrieEventsToSqs-&lt;account&gt;-&lt;region&gt;</code> IAM role
                      <p className="text-xs text-slate-400">Trusted by EventBridge with SQS send permissions</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-yellow-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <code className="text-yellow-300">QrieReadOnly-&lt;account&gt;</code> cross-account IAM role
                      <p className="text-xs text-slate-400">SecurityAudit permissions for resource discovery and policy evaluation</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-blue-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <code className="text-blue-300">qrie-forward-ec2-&lt;region&gt;</code> EventBridge rule
                      <p className="text-xs text-slate-400">Monitors EC2 API write operations</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-purple-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <code className="text-purple-300">qrie-forward-s3-&lt;region&gt;</code> EventBridge rule
                      <p className="text-xs text-slate-400">Monitors S3 API write operations</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-orange-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <code className="text-orange-300">qrie-forward-iam-&lt;region&gt;</code> EventBridge rule
                      <p className="text-xs text-slate-400">Monitors IAM API write operations</p>
                    </div>
                  </div>
                </div>
              </div>
              
              <div>
                <h3 className="font-semibold text-slate-200 mb-3">In Qrie QOP Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-emerald-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <span className="text-emerald-300">SQS Queue + DLQ</span>
                      <p className="text-xs text-slate-400">Secure event ingress with resource policies</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-blue-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <span className="text-blue-300">DynamoDB Tables</span>
                      <p className="text-xs text-slate-400">Resource inventory and security findings storage</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-purple-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <span className="text-purple-300">Lambda Functions</span>
                      <p className="text-xs text-slate-400">Event processing, inventory, and policy scanning</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <div className="h-2 w-2 rounded-full bg-orange-400 mt-2 flex-shrink-0"></div>
                    <div>
                      <span className="text-orange-300">Web UI Stack</span>
                      <p className="text-xs text-slate-400">CloudFront + S3 + Cognito for dashboard access</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Troubleshooting Section */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 mb-12">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-red-500/10 ring-1 ring-red-400/40 flex items-center justify-center">
                <span className="text-red-300 text-sm">🔧</span>
              </div>
              Troubleshooting
            </h2>
            
            <div className="space-y-4">
              <div className="rounded-lg bg-red-500/5 border border-red-500/20 p-4">
                <h3 className="font-semibold text-red-300 mb-2">EventBridge Rules Not Triggering</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Verify CloudTrail is sending events to EventBridge (not just S3)</li>
                  <li>• Check that management events are enabled on your CloudTrail</li>
                  <li>• Ensure the trail covers the region where you&rsquo;re testing</li>
                </ul>
              </div>
              <div className="rounded-lg bg-amber-500/5 border border-amber-500/20 p-4">
                <h3 className="font-semibold text-amber-300 mb-2">Events Not Reaching QOP Queue</h3>
                <ul className="text-sm text-slate-300 space-y-1">
                  <li>• Verify the QOP SQS queue ARN is correct</li>
                  <li>• Check cross-account SQS permissions in QOP account</li>
                  <li>• Confirm EventBridge IAM role has SQS send permissions</li>
                </ul>
              </div>
              <div className="rounded-lg bg-orange-500/5 border border-orange-500/20 p-4">
                <h3 className="font-semibold text-orange-300 mb-2">CloudFormation Stack Redeploy Issues</h3>
                <p className="text-sm text-slate-300 mb-2">If you encounter IAM policy parsing errors or other issues when redeploying:</p>
                <div className="rounded-lg bg-slate-900 border border-slate-600 overflow-hidden">
                  <div className="bg-slate-800 px-3 py-2 text-xs text-slate-400 font-mono">Delete and Recreate Stack</div>
                  <pre className="p-4 text-xs font-mono text-slate-200 overflow-x-auto"><code>{`# Delete the existing stack
aws cloudformation delete-stack \\
  --stack-name QrieForwardToQOP \\
  --region us-east-1

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \\
  --stack-name QrieForwardToQOP \\
  --region us-east-1

# Deploy fresh stack
aws cloudformation deploy \\
  --region us-east-1 \\
  --stack-name QrieForwardToQOP \\
  --template-file qrie-customer-bootstrap.yaml \\
  --parameter-overrides QopQueueArn="<your-qop-queue-arn>" QopAccountId="<qop-account-id>" \\
  --capabilities CAPABILITY_NAMED_IAM`}</code></pre>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  <strong>Note:</strong> Deleting and recreating the stack may cause a brief gap in event forwarding during the transition.
                </p>
              </div>
            </div>
          </div>

          {/* FAQ Section */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-yellow-500/10 ring-1 ring-yellow-400/40 flex items-center justify-center">
                <span className="text-yellow-300 text-sm">❓</span>
              </div>
              Frequently Asked Questions
            </h2>
            
            <div className="space-y-6">
              <div className="rounded-lg border border-slate-700 bg-slate-950/30 p-4">
                <h3 className="font-semibold text-slate-200 mb-2">Is the QOP SQS queue secure?</h3>
                <p className="text-sm text-slate-400">Yes. The queue uses resource policies that only allow EventBridge service access from rules with the <code>qrie-forward-*</code> prefix in your account/region. It&rsquo;s not publicly accessible.</p>
              </div>
              
              <div className="rounded-lg border border-slate-700 bg-slate-950/30 p-4">
                <h3 className="font-semibold text-slate-200 mb-2">Can we add more AWS services later?</h3>
                <p className="text-sm text-slate-400">Absolutely. Update the bootstrap stack to include additional EventBridge rules for services like RDS, EKS, etc. The QOP SQS policy already supports the rule prefix pattern.</p>
              </div>
              
              <div className="rounded-lg border border-slate-700 bg-slate-950/30 p-4">
                <h3 className="font-semibold text-slate-200 mb-2">How do we scale to 10+ regions?</h3>
                <p className="text-sm text-slate-400">Use AWS StackSets to deploy across multiple accounts/regions simultaneously, or run the CloudShell commands in a loop. Each QOP region operates independently.</p>
              </div>
              
              <div className="rounded-lg border border-slate-700 bg-slate-950/30 p-4">
                <h3 className="font-semibold text-slate-200 mb-2">What about offboarding?</h3>
                <p className="text-sm text-slate-400">Simply disable the EventBridge rules in your account and we&rsquo;ll revoke the viewer role. Your data remains in your dedicated QOP instance until you&rsquo;re ready to fully decommission.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
