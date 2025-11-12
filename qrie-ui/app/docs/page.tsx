"use client"

import { DashboardLayout } from "@/components/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import Link from "next/link"
import { BookOpen, Shield, Users } from "lucide-react"

export default function DocsPage() {
  const sections = [
    {
      title: "Onboarding",
      description: "Get started with qrie - initial setup, inventory generation, and first steps",
      icon: BookOpen,
      href: "/docs/onboarding",
      topics: [
        "Prerequisites and setup",
        "Initial inventory generation",
        "Checking inventory completion",
        "Troubleshooting common issues"
      ]
    },
    {
      title: "Policy Management",
      description: "Launch, configure, and manage security and compliance policies",
      icon: Shield,
      href: "/docs/policy-management",
      topics: [
        "Launching policies",
        "Understanding scope configuration",
        "Suspending policies",
        "Best practices and warnings"
      ]
    },
    {
      title: "Account Management",
      description: "Add, remove, and manage AWS accounts monitored by qrie",
      icon: Users,
      href: "/docs/account-management",
      topics: [
        "Adding new accounts",
        "Running bootstrap scans",
        "Removing accounts",
        "Viewing account status"
      ]
    }
  ]

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documentation</h1>
          <p className="text-muted-foreground mt-2">
            Learn how to use qrie to secure and monitor your AWS infrastructure
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => {
            const Icon = section.icon
            return (
              <Link key={section.href} href={section.href}>
                <Card className="h-full transition-colors hover:bg-accent cursor-pointer">
                  <CardHeader>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <CardTitle className="text-xl">{section.title}</CardTitle>
                    </div>
                    <CardDescription>{section.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      {section.topics.map((topic) => (
                        <li key={topic} className="flex items-start gap-2">
                          <span className="text-primary mt-1">•</span>
                          <span>{topic}</span>
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>

        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Need Help?</CardTitle>
            <CardDescription>
              Can't find what you're looking for? Check out these additional resources.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold">API:</div>
              <div className="text-sm text-muted-foreground">
                View the API documentation for programmatic access
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold">Support:</div>
              <div className="text-sm text-muted-foreground">
                Contact support@qrie.io for technical assistance
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="text-primary font-semibold">Roadmap:</div>
              <div className="text-sm text-muted-foreground">
                See upcoming features at qrie.io/roadmap
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
