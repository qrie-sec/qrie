# Qrie UI

Next.js frontend for the Qrie Cloud Security Posture Management platform.

## 🎨 Features

- **Dashboard**: Security findings overview with risk scoring
- **Findings**: Detailed security findings with filtering and pagination
- **Inventory**: Resource inventory across customer accounts
- **Management**: Policy management and configuration
- **Responsive Design**: Modern UI with Tailwind CSS and shadcn/ui components

## 🏗️ Architecture

\`\`\`
app/                    # Next.js App Router pages
├── dashboard/         # Dashboard and summary views
├── findings/          # Security findings interface
├── inventory/         # Resource inventory views
└── management/        # Policy management interface

components/            # Reusable UI components
├── ui/               # shadcn/ui components
└── charts/           # Chart components

lib/                  # Utilities and API client
├── api.ts           # API client with fallback test data
├── types.ts         # TypeScript type definitions
└── utils.ts         # Utility functions
\`\`\`

## 🚀 Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

\`\`\`bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:3000
\`\`\`

### Environment Configuration

Create `.env.local`:

\`\`\`bash
# API Configuration
NEXT_PUBLIC_API_BASE_URL=https://your-lambda-url.lambda-url.us-east-1.on.aws

# For local development (optional)
# NEXT_PUBLIC_API_BASE_URL=http://localhost:3001/api
\`\`\`

## 📦 Deployment

### Static Export to S3

\`\`\`bash
# From project root
./qop.py --deploy-ui --region us-east-1 --profile your-profile

# Or manually
export NEXT_PUBLIC_API_BASE_URL="https://your-api-url"
npm run build
aws s3 sync ./out s3://your-bucket/ --delete
\`\`\`

### Build Configuration

The app is configured for static export in `next.config.mjs`:

\`\`\`javascript
const nextConfig = {
  output: 'export',        // Static export
  images: {
    unoptimized: true,     # Required for S3 hosting
  },
}
\`\`\`

## 🔌 API Integration

### API Client

The `lib/api.ts` file provides:

- **Graceful fallback**: Uses test data if API is unavailable
- **Type safety**: Full TypeScript support
- **Error handling**: Proper error logging and fallback behavior

### Endpoints

- `GET /accounts` - Customer accounts
- `GET /resources` - Resource inventory with pagination
- `GET /findings` - Security findings with filtering
- `GET /policies` - Policy management
- `GET /summary/dashboard` - Dashboard summary data

### Test Data

When the API is unavailable, the UI falls back to comprehensive test data that demonstrates all features.

## 🎯 Features

### Dashboard

- Risk score trending
- Open findings summary
- Policy enforcement status
- Account and resource counts

### Findings

- Advanced filtering (account, policy, severity, state)
- Pagination support
- Detailed finding information
- Remediation guidance

### Inventory

- Resource browsing by account and type
- Resource configuration details
- Integration with findings

### Management

- Active policy overview
- Policy catalog browsing
- Scope configuration (planned)
- Policy launch/suspend (planned)

## 🧪 Testing

\`\`\`bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
\`\`\`

## 🔧 Customization

### Styling

- Uses Tailwind CSS for styling
- shadcn/ui for consistent components
- Custom color scheme in `tailwind.config.js`

### Components

- Modular component architecture
- Reusable UI components in `components/ui/`
- Chart components with Recharts

### API Configuration

- Environment-based API URL configuration
- Automatic fallback to test data
- Type-safe API client with error handling
