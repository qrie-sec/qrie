#!/bin/bash

# Qrie Development Environment Setup
# Sets up all components for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "============================================================"
    echo "🚀 $1"
    echo "============================================================"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_header "QRIE DEVELOPMENT SETUP"
print_status "Project root: $PROJECT_ROOT"

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is required but not installed"
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is required but not installed"
    exit 1
fi
print_success "npm found: $(npm --version)"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_warning "AWS CLI not found - required for deployment"
else
    print_success "AWS CLI found: $(aws --version)"
fi

# Setup Infrastructure (Python/CDK)
print_header "SETTING UP INFRASTRUCTURE"
cd "$PROJECT_ROOT/qrie-infra"

print_status "Creating Python virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

print_status "Activating virtual environment and installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
print_success "Python dependencies installed"

print_status "Installing CDK CLI globally (if not present)..."
if ! command -v cdk &> /dev/null; then
    npm install -g aws-cdk
    print_success "CDK CLI installed"
else
    print_success "CDK CLI already installed: $(cdk --version)"
fi

# Setup UI (Node.js/Next.js)
print_header "SETTING UP UI"
cd "$PROJECT_ROOT/qrie-ui"

print_status "Installing Node.js dependencies..."
if [ -f "pnpm-lock.yaml" ]; then
    if command -v pnpm &> /dev/null; then
        pnpm install
        print_success "Dependencies installed with pnpm"
    else
        print_warning "pnpm-lock.yaml found but pnpm not installed, using npm"
        npm install
        print_success "Dependencies installed with npm"
    fi
else
    npm install
    print_success "Dependencies installed with npm"
fi

# Make scripts executable
print_header "SETTING UP SCRIPTS"
cd "$PROJECT_ROOT"

print_status "Making scripts executable..."
chmod +x qop.py
chmod +x tools/deploy/*.sh
chmod +x scripts/*.sh
print_success "Scripts are now executable"

# Final setup
print_header "SETUP COMPLETE"
print_success "Qrie development environment is ready!"

echo ""
echo "🎯 Next Steps:"
echo "1. Configure AWS credentials:"
echo "   aws configure --profile qop"
echo ""
echo "2. Test the setup:"
echo "   ./qop.py --build"
echo ""
echo "3. Deploy to AWS (optional):"
echo "   ./qop.py --full-deploy --region us-east-1 --profile qop"
echo ""
echo "4. Start local UI development:"
echo "   cd qrie-ui && npm run dev"
echo ""
echo "📚 Documentation:"
echo "   • README.md - Main project documentation"
echo "   • ARCHITECTURE.md - Repository structure and architecture"
echo "   • tools/deploy/CUSTOM-DOMAIN.md - Custom domain setup"
echo ""
print_success "Happy coding! 🚀"
