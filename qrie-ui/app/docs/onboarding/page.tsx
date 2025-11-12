"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, AlertTriangle, CheckCircle2, Clock, Terminal } from "lucide-react"

export default function OnboardingPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-4">
          <Link href="/docs" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Onboarding</h1>
            <p className="text-muted-foreground mt-1">
              Get started with qrie - initial setup and inventory generation
            </p>
          </div>
        </div>

        {/* Prerequisites */}
        <Card>
          <CardHeader>
            <CardTitle>Prerequisites</CardTitle>
            <CardDescription>Before you begin, ensure you have the following:</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              <div>
                <div className="font-medium">AWS Account Access</div>
                <div className="text-sm text-muted-foreground">
                  IAM permissions to create roles and EventBridge rules
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              <div>
                <div className="font-medium">QOP Account Deployed</div>
                <div className="text-sm text-muted-foreground">
                  Qrie engineers have set up your dedicated QOP (Qrie On-Premises) account
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              <div>
                <div className="font-medium">EventBridge Rules Configured</div>
                <div className="text-sm text-muted-foreground">
                  CloudTrail events forwarding to QOP account via EventBridge
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 1: Initial Inventory */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="text-lg px-3 py-1">Step 1</Badge>
              <CardTitle>Generate Initial Inventory</CardTitle>
            </div>
            <CardDescription>
              Inventory is the foundation - policies need resources to evaluate
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Important</AlertTitle>
              <AlertDescription>
                Do nothing else until inventory generation completes. This is a bootstrap scan that establishes your baseline.
              </AlertDescription>
            </Alert>

            <div>
              <div className="font-medium mb-2">Run the inventory generation command:</div>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm">
                <div className="flex items-start gap-2">
                  <Terminal className="h-4 w-4 mt-1 text-muted-foreground" />
                  <code>./qop.py --generate-inventory --region us-east-1 --profile qop</code>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="font-medium">What happens:</div>
              <ul className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Scans all supported services (S3, EC2, IAM) across all your AWS accounts</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Stores resource configurations in the qrie_resources DynamoDB table</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>This is a <Badge variant="secondary" className="text-xs">bootstrap</Badge> scan - drift metrics are NOT updated</span>
                </li>
              </ul>
            </div>

            <div className="flex items-start gap-3 p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Clock className="h-5 w-5 text-blue-500 mt-0.5" />
              <div className="text-sm">
                <div className="font-medium text-blue-500">Expected Duration</div>
                <div className="text-muted-foreground">5-15 minutes depending on resource count</div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 2: Check Completion */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="text-lg px-3 py-1">Step 2</Badge>
              <CardTitle>Check Inventory Completion</CardTitle>
            </div>
            <CardDescription>
              Verify that inventory generation has finished successfully
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium mb-2">Method 1: Dashboard</div>
              <div className="text-sm text-muted-foreground space-y-2">
                <p>Navigate to the <Link href="/" className="text-primary hover:underline">Dashboard</Link> and check:</p>
                <ul className="ml-4 space-y-1">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span><strong>Resources</strong> count should be greater than 0</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span><strong>Last Inventory Scan</strong> timestamp should be recent</span>
                  </li>
                </ul>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">Method 2: Inventory Page</div>
              <div className="text-sm text-muted-foreground">
                <p>Visit the <Link href="/inventory" className="text-primary hover:underline">Inventory</Link> page to see all discovered resources</p>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">Method 3: Command Line</div>
              <div className="bg-muted p-4 rounded-lg font-mono text-sm">
                <code>aws dynamodb scan --table-name qrie_resources --select COUNT --region us-east-1 --profile qop</code>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Step 3: Launch Policies */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="text-lg px-3 py-1">Step 3</Badge>
              <CardTitle>Launch Your First Policies</CardTitle>
            </div>
            <CardDescription>
              Once inventory is complete, you can start launching policies
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm text-muted-foreground space-y-3">
              <p>Navigate to the <Link href="/management" className="text-primary hover:underline">Management</Link> page to:</p>
              <ul className="ml-4 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Browse available policies by category (IAM, S3, EC2, etc.)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Click "Launch" on policies you want to activate</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Configure scope (which accounts to monitor)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Optionally customize severity and remediation steps</span>
                </li>
              </ul>
            </div>

            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>Automatic Bootstrap Scan</AlertTitle>
              <AlertDescription>
                When you launch a policy, qrie automatically triggers a bootstrap scan to evaluate all resources against that policy. This creates your initial findings baseline. Deleting a policy removes it and purges all associated findings.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Troubleshooting */}
        <Card>
          <CardHeader>
            <CardTitle>Troubleshooting</CardTitle>
            <CardDescription>Common issues and solutions</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium text-sm">No resources found after inventory scan</div>
              <div className="text-sm text-muted-foreground mt-1 space-y-1">
                <p>Check:</p>
                <ul className="ml-4 space-y-1">
                  <li>• EventBridge rules are correctly forwarding events to QOP account</li>
                  <li>• IAM roles have necessary permissions (s3:ListBuckets, ec2:DescribeInstances, iam:ListUsers, etc.)</li>
                  <li>• Customer accounts are registered in qrie_accounts DynamoDB table</li>
                </ul>
              </div>
            </div>

            <div>
              <div className="font-medium text-sm">Inventory scan takes too long</div>
              <div className="text-sm text-muted-foreground mt-1">
                Large AWS environments (1000+ resources) may take 15-20 minutes. This is normal. You can monitor progress in CloudWatch logs for the qrie_inventory_generator Lambda.
              </div>
            </div>

            <div>
              <div className="font-medium text-sm">Permission errors during scan</div>
              <div className="text-sm text-muted-foreground mt-1">
                Ensure the Lambda execution role has cross-account assume role permissions and the customer account IAM roles trust the QOP account.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle>Next Steps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/docs/policy-management" className="block text-primary hover:underline">
              → Learn about Policy Management
            </Link>
            <Link href="/docs/account-management" className="block text-primary hover:underline">
              → Learn about Account Management
            </Link>
            <Link href="/management" className="block text-primary hover:underline">
              → Go to Management page to launch policies
            </Link>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
