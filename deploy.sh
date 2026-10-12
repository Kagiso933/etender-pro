#!/bin/bash

# SA eTender Pro - Automated Deployment Script
# This script helps you push to GitHub and deploy to free hosting platforms

set -e  # Exit on error

echo "================================================"
echo "  SA eTender Pro - Deployment Assistant"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install Git first."
    exit 1
fi

# Initialize git if not already initialized
if [ ! -d .git ]; then
    print_info "Initializing Git repository..."
    git init
    print_success "Git repository initialized"
fi

# Create .gitignore if it doesn't exist
if [ ! -f .gitignore ]; then
    print_info "Creating .gitignore file..."
    cat > .gitignore << 'GITIGNORE'
node_modules/
__pycache__/
*.pyc
.env
.env.local
*.log
tender_cache.json
etender_data.json
.DS_Store
GITIGNORE
    print_success ".gitignore created"
fi

# Prompt for GitHub repository URL
echo ""
print_info "GitHub Repository Setup"
echo "----------------------------------------"
read -p "Enter your GitHub repository URL (or press Enter to skip): " GITHUB_URL

if [ -z "$GITHUB_URL" ]; then
    print_warning "Skipping GitHub push. You can do this later."
else
    # Check if remote already exists
    if git remote get-url origin &> /dev/null; then
        print_info "Updating remote origin..."
        git remote set-url origin "$GITHUB_URL"
    else
        print_info "Adding remote origin..."
        git remote add origin "$GITHUB_URL"
    fi
    
    # Stage all files
    print_info "Staging files..."
    git add .
    
    # Commit
    read -p "Enter commit message (default: 'Initial commit'): " COMMIT_MSG
    COMMIT_MSG=${COMMIT_MSG:-"Initial commit"}
    
    git commit -m "$COMMIT_MSG" || print_warning "No changes to commit"
    
    # Push to GitHub
    print_info "Pushing to GitHub..."
    git branch -M main
    
    if git push -u origin main; then
        print_success "Successfully pushed to GitHub!"
    else
        print_warning "Push failed. You may need to authenticate or resolve conflicts."
    fi
fi

echo ""
echo "================================================"
echo "  Deployment Options"
echo "================================================"
echo ""
echo "Choose your deployment platform:"
echo "  1) Netlify (Frontend - Recommended)"
echo "  2) Vercel (Frontend)"
echo "  3) Railway (Backend - Recommended)"
echo "  4) Render (Backend)"
echo "  5) Deploy standalone HTML only (simplest)"
echo "  6) Skip deployment"
echo ""
read -p "Enter your choice (1-6): " DEPLOY_CHOICE

case $DEPLOY_CHOICE in
    1)
        echo ""
        print_info "Netlify Deployment"
        echo "----------------------------------------"
        
        if ! command -v netlify &> /dev/null; then
            print_warning "Netlify CLI not installed. Installing..."
            npm install -g netlify-cli
        fi
        
        echo "1. The standalone HTML file will be deployed"
        echo "2. You'll need to login to Netlify (it will open in browser)"
        echo ""
        read -p "Press Enter to continue..."
        
        # Create a simple netlify.toml
        cat > netlify.toml << 'NETLIFY'
[build]
  publish = "."
  command = "echo 'No build needed'"

[[redirects]]
  from = "/*"
  to = "/etender-tool-standalone.html"
  status = 200
NETLIFY
        
        netlify deploy --prod
        print_success "Deployed to Netlify!"
        ;;
        
    2)
        echo ""
        print_info "Vercel Deployment"
        echo "----------------------------------------"
        
        if ! command -v vercel &> /dev/null; then
            print_warning "Vercel CLI not installed. Installing..."
            npm install -g vercel
        fi
        
        echo "Deploying to Vercel..."
        vercel --prod
        print_success "Deployed to Vercel!"
        ;;
        
    3)
        echo ""
        print_info "Railway Deployment (Backend)"
        echo "----------------------------------------"
        echo ""
        echo "Railway deployment steps:"
        echo "1. Go to https://railway.app"
        echo "2. Sign up or login"
        echo "3. Click 'New Project' → 'Deploy from GitHub repo'"
        echo "4. Select your repository"
        echo "5. Railway will auto-detect Node.js and deploy"
        echo "6. Add environment variables in the dashboard:"
        echo "   - PORT=3001"
        echo "   - ANTHROPIC_API_KEY=your_key_here"
        echo ""
        read -p "Press Enter when done to continue..."
        print_success "Railway setup instructions displayed"
        ;;
        
    4)
        echo ""
        print_info "Render Deployment (Backend)"
        echo "----------------------------------------"
        echo ""
        echo "Render deployment steps:"
        echo "1. Go to https://render.com"
        echo "2. Sign up or login"
        echo "3. Click 'New' → 'Web Service'"
        echo "4. Connect your GitHub repository"
        echo "5. Configure:"
        echo "   - Build Command: npm install"
        echo "   - Start Command: npm start"
        echo "6. Add environment variables:"
        echo "   - PORT=3001"
        echo "   - ANTHROPIC_API_KEY=your_key_here"
        echo ""
        read -p "Press Enter when done to continue..."
        print_success "Render setup instructions displayed"
        ;;
        
    5)
        echo ""
        print_info "Standalone HTML Deployment"
        echo "----------------------------------------"
        echo ""
        echo "Your standalone HTML file is ready!"
        echo ""
        echo "You can:"
        echo "1. Just open etender-tool-standalone.html locally"
        echo "2. Upload to any web hosting (GitHub Pages, Netlify, etc.)"
        echo "3. Share the file directly with others"
        echo ""
        print_success "No deployment needed - file is ready to use!"
        ;;
        
    6)
        print_warning "Skipping deployment"
        ;;
        
    *)
        print_error "Invalid choice"
        ;;
esac

echo ""
echo "================================================"
echo "  Deployment Complete!"
echo "================================================"
echo ""
print_info "Next Steps:"
echo "1. If you deployed frontend: Open the URL provided"
echo "2. If you deployed backend: Update frontend to use your API URL"
echo "3. Customize the scrapers for real eTender.gov.za HTML"
echo "4. Test the application thoroughly"
echo ""
print_success "All done! Check README.md for more information."
