"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"
import { ArrowLeft, AlertTriangle, Shield, Clock, Trash2, ExternalLink } from "lucide-react"

export default function PolicyManagementPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-4xl">
        <div className="flex items-center gap-4">
          <Link href="/docs" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Policy Management</h1>
            <p className="text-muted-foreground mt-1">
              Launch, configure, and manage security and compliance policies
            </p>
          </div>
        </div>

        {/* Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Overview</CardTitle>
            <CardDescription>
              Policies are the rules that qrie uses to evaluate your AWS resources for security and compliance issues
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm text-muted-foreground space-y-2">
              <p>Each policy:</p>
              <ul className="ml-4 space-y-1">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Evaluates specific resource types (S3 buckets, IAM users, EC2 instances, etc.)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Checks for security misconfigurations or compliance violations</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Creates findings when issues are detected</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Provides remediation guidance</span>
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>

        {/* Launching Policies */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Shield className="h-5 w-5 text-primary" />
              <CardTitle>Launching Policies</CardTitle>
            </div>
            <CardDescription>
              Activate policies to start monitoring your resources
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-yellow-500/50 bg-yellow-500/10">
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
              <AlertTitle className="text-yellow-500">Important</AlertTitle>
              <AlertDescription>
                Policy launch is an expensive operation. Do not randomly enable/disable policies. Launch them once and adjust scope/severity as needed.
              </AlertDescription>
            </Alert>

            <div>
              <div className="font-medium mb-2">Steps to launch a policy:</div>
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">1</Badge>
                  <div>
                    <div className="font-medium text-foreground">Navigate to Management page</div>
                    <div>Go to <Link href="/management" className="text-primary hover:underline">Management</Link> to see all available policies</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">2</Badge>
                  <div>
                    <div className="font-medium text-foreground">Browse by category</div>
                    <div>Policies are organized by service (IAM, S3, EC2) and compliance framework (CIS, HIPAA, etc.)</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">3</Badge>
                  <div>
                    <div className="font-medium text-foreground">Click "Launch" on desired policy</div>
                    <div>Review the policy description and default settings</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">4</Badge>
                  <div>
                    <div className="font-medium text-foreground">Configure scope</div>
                    <div>Choose which accounts, tags, or OUs to monitor (default: all accounts)</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">5</Badge>
                  <div>
                    <div className="font-medium text-foreground">Customize (optional)</div>
                    <div>Adjust severity (0-100) or customize remediation steps</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Badge variant="outline" className="mt-0.5">6</Badge>
                  <div>
                    <div className="font-medium text-foreground">Confirm launch</div>
                    <div>Policy is activated and bootstrap scan is triggered automatically</div>
                  </div>
                </li>
              </ol>
            </div>

            <div className="flex items-start gap-3 p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Clock className="h-5 w-5 text-blue-500 mt-0.5" />
              <div className="text-sm">
                <div className="font-medium text-blue-500">Automatic Bootstrap Scan</div>
                <div className="text-muted-foreground">
                  When you launch a policy, qrie automatically triggers a <Badge variant="secondary" className="text-xs">bootstrap</Badge> scan that evaluates all resources in scope. This creates your initial findings baseline. Duration: 2-10 minutes depending on resource count.
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Understanding Scope */}
        <Card>
          <CardHeader>
            <CardTitle>Understanding Scope Configuration</CardTitle>
            <CardDescription>
              Control which resources are evaluated by a policy
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="font-medium mb-2">Scope Options:</div>
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Include Accounts</div>
                  <div className="text-muted-foreground">List of AWS account IDs to monitor (default: all)</div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Exclude Accounts</div>
                  <div className="text-muted-foreground">List of AWS account IDs to skip</div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Include Tags</div>
                  <div className="text-muted-foreground">Only evaluate resources with these tags (e.g., Environment=Production)</div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Exclude Tags</div>
                  <div className="text-muted-foreground">Skip resources with these tags (e.g., SkipCompliance=true)</div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Include OU Paths</div>
                  <div className="text-muted-foreground">Monitor accounts in specific AWS Organizations OUs</div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="font-medium text-foreground min-w-[140px]">Exclude OU Paths</div>
                  <div className="text-muted-foreground">Skip accounts in specific OUs</div>
                </div>
              </div>
            </div>

            <Alert>
              <AlertTitle>Tip: Start Broad, Refine Later</AlertTitle>
              <AlertDescription>
                It's better to launch policies with broad scope (all accounts) and then narrow down using exclusions, rather than trying to get the scope perfect on first launch.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* Suspending Policies */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Trash2 className="h-5 w-5 text-destructive" />
              <CardTitle>Suspending Policies</CardTitle>
            </div>
            <CardDescription>
              Temporarily or permanently disable policies
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-red-500/50 bg-red-500/10">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <AlertTitle className="text-red-500">Warning: Findings Are Purged</AlertTitle>
              <AlertDescription>
                When you suspend a policy, all findings for that policy are marked as RESOLVED and cannot be recovered. Consider adjusting scope instead of suspending if you want to keep historical data.
              </AlertDescription>
            </Alert>

            <div>
              <div className="font-medium mb-2">To suspend a policy:</div>
              <ol className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">1.</span>
                  <span>Go to <Link href="/management" className="text-primary hover:underline">Management</Link> page</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">2.</span>
                  <span>Find the active policy you want to suspend</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">3.</span>
                  <span>Click "Suspend" button</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">4.</span>
                  <span>Confirm the action (you'll see how many findings will be purged)</span>
                </li>
              </ol>
            </div>

            <div>
              <div className="font-medium mb-2">What happens when you suspend:</div>
              <ul className="space-y-2 text-sm text-muted-foreground ml-4">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Policy status changes to "suspended"</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>All ACTIVE findings are marked as RESOLVED with reason "POLICY_SUSPENDED"</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>Policy stops evaluating resources</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>No new findings will be created for this policy</span>
                </li>
              </ul>
            </div>

            <div>
              <div className="font-medium mb-2">Alternative: Adjust scope instead</div>
              <div className="text-sm text-muted-foreground">
                If you want to stop monitoring certain resources but keep findings history, use the "Edit" button to adjust the policy scope with exclusions rather than suspending the entire policy.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Best Practices */}
        <Card>
          <CardHeader>
            <CardTitle>Best Practices</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[100px]">Launch Once</div>
              <div className="text-sm text-muted-foreground">
                Policy launch scans all resources (expensive). Launch policies once and adjust scope/severity as needed rather than repeatedly enabling/disabling.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[100px]">Start Simple</div>
              <div className="text-sm text-muted-foreground">
                Begin with high-severity policies (IAM, encryption, public access) before adding lower-priority checks.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[100px]">Use Exclusions</div>
              <div className="text-sm text-muted-foreground">
                Use scope exclusions for dev/test accounts or resources with legitimate exceptions rather than suspending entire policies.
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold min-w-[100px]">Monitor Drift</div>
              <div className="text-sm text-muted-foreground">
                Check the dashboard's "Last Policy Scan" metric. If drift is detected (scan older than 26 hours), investigate scheduled scan failures.
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Future Features */}
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CardTitle>Future Features</CardTitle>
              <Link href="https://qrie.io/roadmap" target="_blank" className="text-primary hover:underline text-sm flex items-center gap-1">
                View Roadmap <ExternalLink className="h-3 w-3" />
              </Link>
            </div>
            <CardDescription>Coming soon to qrie</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Policy Pause:</strong> Temporarily disable policies without purging findings (findings flagged but retained)</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Findings Archive:</strong> Export purged findings to S3 before deletion for compliance audit trails</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Custom Policies:</strong> Define your own policies using Python evaluation modules</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-primary mt-1">•</span>
              <span><strong>Policy Templates:</strong> Pre-configured policy bundles for compliance frameworks (HIPAA, PCI-DSS, SOC 2)</span>
            </div>
          </CardContent>
        </Card>

        {/* Next Steps */}
        <Card>
          <CardHeader>
            <CardTitle>Next Steps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/docs/account-management" className="block text-primary hover:underline">
              → Learn about Account Management
            </Link>
            <Link href="/management" className="block text-primary hover:underline">
              → Go to Management page to launch policies
            </Link>
            <Link href="/findings" className="block text-primary hover:underline">
              → View Findings to see policy evaluation results
            </Link>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
