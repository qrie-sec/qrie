This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Onboarding artifacts (public URLs)

- CloudFormation template (YAML): `/onboarding/customer_bootstrap.yaml`
- Onboarding guide (page): `/onboarding`
- Onboarding guide (raw markdown): `/onboarding/onboarding_guide.md`

### Bootstrap YAML Source of Truth

**⚠️ IMPORTANT:** The `customer_bootstrap.yaml` file is **NOT** edited directly in qrie-lp.

- **Source of Truth:** `qrie-infra/onboarding/customer_bootstrap.yaml`
- **Served to Customers:** `qrie-lp/public/onboarding/customer_bootstrap.yaml` (copy)

**To update the bootstrap YAML:**
```bash
# 1. Edit the source file
vim qrie-infra/onboarding/customer_bootstrap.yaml

# 2. Copy to landing page
cp qrie-infra/onboarding/customer_bootstrap.yaml qrie-lp/public/onboarding/

# 3. Commit both files together
git add qrie-infra/onboarding/customer_bootstrap.yaml qrie-lp/public/onboarding/customer_bootstrap.yaml
git commit -m "Update customer bootstrap YAML"

# 4. Deploy landing page to update https://qrie.io/onboarding/customer_bootstrap.yaml
```

### Usage Notes

- In production, customers download via:
  ```bash
  curl -fsSL -o qrie-customer-bootstrap.yaml \
    https://qrie.io/onboarding/customer_bootstrap.yaml
  ```

- In local dev, the URLs resolve under `http://localhost:3000`:
  ```bash
  curl -fsSL -o qrie-customer-bootstrap.yaml \
    http://localhost:3000/onboarding/customer_bootstrap.yaml
  ```

- These artifacts are hosted from `public/onboarding/` and are cacheable via your CDN. If you prefer not to serve from the LP domain, alternatives:
  - Host the YAML on an S3 bucket fronted by CloudFront and update the `curl` URL.
  - Use a GitHub release asset or raw file URL.
