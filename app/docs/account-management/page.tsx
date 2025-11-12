"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, AlertTriangle, Users, Plus, Trash2, Terminal, Clock } from "lucide-react"

export default function AccountManagementPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-4">
          <Link href="/docs" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Account Management</h1>
            <p className="text-muted-foreground mt-1">
              Add, remove, and manage AWS accounts monitored by qrie
            </p>
          </div>
        </div>

        {/* Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>
              qrie monitors multiple AWS accounts from a centralized QOP (Qrie On-Premises) account
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-muted-foreground space-y-2">
              <p>Account management involves:</p>
              <ul className="ml-4 space-y-1">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Registering new AWS accounts to be monitored</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Running initial inventory scans for new accounts</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Viewing account status and last scan times</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Removing accounts from monitoring</span>
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Adding New Accounts */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Plus className="h-5 w-5 text-primary" />
              <CardTitle>Adding New Accounts</CardTitle>
            </div>
            <CardDescription>
              Register a new AWS account for qrie to monitor
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium mb-2">Prerequisites:</div>
              <ul className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>IAM role created in the new account with cross-account trust to QOP account</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>EventBridge rules configured to forward CloudTrail events to QOP account</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Account ID added to qrie_accounts DynamoDB table</span>
                </li>
              </ul>
            </div>

            <Alert>
              <AlertTitle>Note: Manual DynamoDB Operation</AlertTitle>
              <AlertDescription>
                Currently, adding accounts requires manual DynamoDB table updates. A UI for account management is coming soon. Contact your qrie administrator to add new accounts.
              </AlertDescription>
            </Alert>

            <div>
              <div className="font-medium mb-2">After account is registered:</div>
              <div className="text-sm text-muted-foreground space-y-3">
                <p>You have two options for initial scanning:</p>
                
                <div className="space-y-2">
                  <div className="font-medium text-foreground">Option 1: Immediate Bootstrap Scan (Recommended)</div>
                  <div>Run a bootstrap scan immediately to generate inventory and evaluate active policies:</div>
                  <div className="bg-muted p-4 rounded-lg font-mono text-sm mt-2">
                    <div className="flex items-start gap-2">
                      <Terminal className="h-4 w-4 mt-1 text-muted-foreground" />
                      <code>./qop.py --scan-account --account-id 999888777666 --region us-east-1 --profile qop</code>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 p-3 bg-blue-500/10 rounded-lg border border-blue-500/20 mt-2">
                    <Clock className="h-5 w-5 text-blue-500 mt-0.5" />
                    <div className="text-sm">
                      <div className="font-medium text-blue-500">Duration: 5-15 minutes</div>
                      <div className="text-muted-foreground">Generates inventory + evaluates all active policies</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="font-medium text-foreground">Option 2: Wait for Weekly Auto-Scan</div>
                  <div>The account will be automatically scanned during the next weekly inventory scan (Saturday midnight UTC).</div>
                  <Alert className="border-yellow-500/50 bg-yellow-500/10 mt-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-500" />
                    <AlertTitle className="text-yellow-500">Warning: Drift Detection</AlertTitle>
                    <AlertDescription>
                      If you wait for the weekly scan, any findings discovered will be reported as drift since the account wasn't in the baseline. Run Option 1 to avoid this.
                    </AlertDescription>
                  </Alert>
                </div>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">What the scan does:</div>
              <ol className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <Badge variant="outline" className="mt-0.5">1</Badge>
                  <span>Generates inventory for all supported services (S3, EC2, IAM)</span>
                </li>
                <li className="flex items-start gap-2">
                  <Badge variant="outline" className="mt-0.5">2</Badge>
                  <span>Evaluates resources against all active policies</span>
                </li>
                <li className="flex items-start gap-2">
                  <Badge variant="outline" className="mt-0.5">3</Badge>
                  <span>Creates findings for any detected issues</span>
                </li>
                <li className="flex items-start gap-2">
                  <Badge variant="outline" className="mt-0.5">4</Badge>
                  <span>Establishes baseline (this is a <Badge variant="secondary" className="text-xs">bootstrap</Badge> scan)</span>
                </li>
              </ol>
            </div>
          </CardContent>
        </Card>

        {/* Viewing Account Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Users className="h-5 w-5 text-primary" />
              <CardTitle>Viewing Account Status</CardTitle>
            </div>
            <CardDescription>
              Check which accounts are being monitored and their scan status
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium mb-2">Dashboard View:</div>
              <div className="text-sm text-muted-foreground">
                The <Link href="/" className="text-primary hover:underline">Dashboard</Link> shows:
                <ul className="ml-4 mt-2 space-y-1">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Total number of monitored accounts</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Last inventory scan timestamp</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Drift detection status</span>
                  </li>
                </ul>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">Inventory View:</div>
              <div className="text-sm text-muted-foreground">
                The <Link href="/inventory" className="text-primary hover:underline">Inventory</Link> page allows you to:
                <ul className="ml-4 mt-2 space-y-1">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Filter resources by account ID</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>See resource counts per account</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>View last seen timestamps for resources</span>
                  </li>
                </ul>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">Findings View:</div>
              <div className="text-sm text-muted-foreground">
                The <Link href="/findings" className="text-primary hover:underline">Findings</Link> page shows:
                <ul className="ml-4 mt-2 space-y-1">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Security findings per account</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>Filter by account to see account-specific issues</span>
                  </li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Removing Accounts */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Trash2 className="h-5 w-5 text-destructive" />
              <CardTitle>Removing Accounts</CardTitle>
            </div>
            <CardDescription>
              Stop monitoring an AWS account
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertTitle>Note: Manual DynamoDB Operation</AlertTitle>
              <AlertDescription>
                Currently, removing accounts requires manual DynamoDB table updates. Contact your qrie administrator to remove accounts.
              </AlertDescription>
            </Alert>

            <div>
              <div className="font-medium mb-2">What happens when you remove an account:</div>
              <ul className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Account is removed from qrie_accounts DynamoDB table</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>New events from this account are ignored</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Existing inventory and findings remain in database (soft delete)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Account will not appear in future scans</span>
                </li>
              </ul>
            </div>

            <div>
              <div className="font-medium mb-2">Data retention:</div>
              <div className="text-sm text-muted-foreground">
                Historical inventory and findings data for removed accounts is retained for audit purposes. A hard delete option (with confirmation) will be available in a future release.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Scheduled Scans */}
        <Card>
          <CardHeader>
            <CardTitle>Scheduled Scans (Anti-Entropy)</CardTitle>
            <CardDescription>
              Automatic scans that detect drift and configuration changes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium mb-2">Weekly Inventory Scan:</div>
              <div className="text-sm text-muted-foreground space-y-2">
                <p><strong>Schedule:</strong> Saturday 00:00 UTC</p>
                <p><strong>Purpose:</strong> Full inventory refresh across all accounts and services</p>
                <p><strong>Scan Type:</strong> <Badge variant="secondary" className="text-xs">anti-entropy</Badge> (updates drift metrics)</p>
                <p><strong>Duration:</strong> 10-30 minutes depending on total resource count</p>
              </div>
            </div>

            <div>
              <div className="font-medium mb-2">Daily Policy Scan:</div>
              <div className="text-sm text-muted-foreground space-y-2">
                <p><strong>Schedule:</strong> Daily at 04:00 UTC</p>
                <p><strong>Purpose:</strong> Re-evaluate all resources against active policies</p>
                <p><strong>Scan Type:</strong> <Badge variant="secondary" className="text-xs">anti-entropy</Badge> (updates drift metrics)</p>
                <p><strong>Duration:</strong> 5-15 minutes depending on policy count and resources</p>
              </div>
            </div>

            <Alert>
              <AlertTitle>Drift Detection</AlertTitle>
              <AlertDescription>
                The dashboard monitors these scheduled scans. If inventory scan is older than 8 days or policy scan is older than 26 hours, drift is detected and flagged on the dashboard.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Best Practices */}
        <Card>
          <CardHeader>
            <CardTitle>Best Practices</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[140px]">Bootstrap New Accounts</div>
              <div className="text-sm text-muted-foreground">
                Always run a bootstrap scan immediately after adding a new account to establish baseline and avoid drift false positives.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[140px]">Monitor Drift</div>
              <div className="text-sm text-muted-foreground">
                Check the dashboard regularly for drift detection alerts. Investigate if scheduled scans are failing.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[140px]">Document Accounts</div>
              <div className="text-sm text-muted-foreground">
                Keep a record of which accounts are monitored, their purpose (prod/dev/test), and any special scope configurations.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[140px]">Test First</div>
              <div className="text-sm text-muted-foreground">
                Add dev/test accounts first to verify EventBridge rules and IAM roles are configured correctly before adding production accounts.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Future Features */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle>Future Features</CardTitle>
            <CardDescription>Coming soon to qrie</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Account Management UI:</strong> Add/remove accounts directly from the UI without DynamoDB access</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Account Health Dashboard:</strong> Per-account metrics, scan history, and compliance scores</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Automated Onboarding:</strong> CloudFormation StackSets for one-click account setup</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Account Groups:</strong> Organize accounts by environment, team, or business unit</span>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps */}
        <Card>
          <CardHeader>
            <CardTitle>Next Steps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/docs/onboarding" className="block text-primary hover:underline">
              → Review Onboarding documentation
            </Link>
            <Link href="/docs/policy-management" className="block text-primary hover:underline">
              → Learn about Policy Management
            </Link>
            <Link href="/inventory" className="block text-primary hover:underline">
              → View Inventory to see all monitored accounts
            </Link>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
