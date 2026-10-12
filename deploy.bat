@echo off
REM SA eTender Pro - Windows Deployment Script
REM This script helps you push to GitHub and deploy to free hosting platforms

setlocal enabledelayedexpansion

echo ================================================
echo   SA eTender Pro - Deployment Assistant
echo ================================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed. Please install Git first.
    echo Download from: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Initialize git if not already initialized
if not exist .git (
    echo Initializing Git repository...
    git init
    echo Git repository initialized
)

REM Create .gitignore if it doesn't exist
if not exist .gitignore (
    echo Creating .gitignore file...
    (
        echo node_modules/
        echo __pycache__/
        echo *.pyc
        echo .env
        echo .env.local
        echo *.log
        echo tender_cache.json
        echo etender_data.json
        echo .DS_Store
    ) > .gitignore
    echo .gitignore created
)

REM Prompt for GitHub repository URL
echo.
echo GitHub Repository Setup
echo ----------------------------------------
set /p GITHUB_URL="Enter your GitHub repository URL (or press Enter to skip): "

if "%GITHUB_URL%"=="" (
    echo Skipping GitHub push. You can do this later.
) else (
    REM Check if remote already exists
    git remote get-url origin >nul 2>&1
    if %errorlevel% equ 0 (
        echo Updating remote origin...
        git remote set-url origin "%GITHUB_URL%"
    ) else (
        echo Adding remote origin...
        git remote add origin "%GITHUB_URL%"
    )
    
    REM Stage all files
    echo Staging files...
    git add .
    
    REM Commit
    set /p COMMIT_MSG="Enter commit message (default: Initial commit): "
    if "%COMMIT_MSG%"=="" set COMMIT_MSG=Initial commit
    
    git commit -m "%COMMIT_MSG%"
    
    REM Push to GitHub
    echo Pushing to GitHub...
    git branch -M main
    git push -u origin main
    
    if %errorlevel% equ 0 (
        echo Successfully pushed to GitHub!
    ) else (
        echo Push failed. You may need to authenticate or resolve conflicts.
    )
)

echo.
echo ================================================
echo   Deployment Options
echo ================================================
echo.
echo Choose your deployment platform:
echo   1) Netlify (Frontend - Recommended)
echo   2) Vercel (Frontend)
echo   3) Railway (Backend - Instructions)
echo   4) Render (Backend - Instructions)
echo   5) Deploy standalone HTML only (simplest)
echo   6) Skip deployment
echo.
set /p DEPLOY_CHOICE="Enter your choice (1-6): "

if "%DEPLOY_CHOICE%"=="1" (
    echo.
    echo Netlify Deployment
    echo ----------------------------------------
    
    REM Check if Netlify CLI is installed
    netlify --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Netlify CLI not installed. Installing...
        call npm install -g netlify-cli
    )
    
    echo.
    echo 1. The standalone HTML file will be deployed
    echo 2. You'll need to login to Netlify (it will open in browser)
    echo.
    pause
    
    REM Create netlify.toml
    (
        echo [build]
        echo   publish = "."
        echo   command = "echo 'No build needed'"
        echo.
        echo [[redirects]]
        echo   from = "/*"
        echo   to = "/etender-tool-standalone.html"
        echo   status = 200
    ) > netlify.toml
    
    call netlify deploy --prod
    echo Deployed to Netlify!
    
) else if "%DEPLOY_CHOICE%"=="2" (
    echo.
    echo Vercel Deployment
    echo ----------------------------------------
    
    REM Check if Vercel CLI is installed
    vercel --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Vercel CLI not installed. Installing...
        call npm install -g vercel
    )
    
    echo Deploying to Vercel...
    call vercel --prod
    echo Deployed to Vercel!
    
) else if "%DEPLOY_CHOICE%"=="3" (
    echo.
    echo Railway Deployment (Backend)
    echo ----------------------------------------
    echo.
    echo Railway deployment steps:
    echo 1. Go to https://railway.app
    echo 2. Sign up or login
    echo 3. Click 'New Project' - 'Deploy from GitHub repo'
    echo 4. Select your repository
    echo 5. Railway will auto-detect Node.js and deploy
    echo 6. Add environment variables in the dashboard:
    echo    - PORT=3001
    echo    - ANTHROPIC_API_KEY=your_key_here
    echo.
    pause
    
) else if "%DEPLOY_CHOICE%"=="4" (
    echo.
    echo Render Deployment (Backend)
    echo ----------------------------------------
    echo.
    echo Render deployment steps:
    echo 1. Go to https://render.com
    echo 2. Sign up or login
    echo 3. Click 'New' - 'Web Service'
    echo 4. Connect your GitHub repository
    echo 5. Configure:
    echo    - Build Command: npm install
    echo    - Start Command: npm start
    echo 6. Add environment variables:
    echo    - PORT=3001
    echo    - ANTHROPIC_API_KEY=your_key_here
    echo.
    pause
    
) else if "%DEPLOY_CHOICE%"=="5" (
    echo.
    echo Standalone HTML Deployment
    echo ----------------------------------------
    echo.
    echo Your standalone HTML file is ready!
    echo.
    echo You can:
    echo 1. Just open etender-tool-standalone.html locally
    echo 2. Upload to any web hosting (GitHub Pages, Netlify, etc.)
    echo 3. Share the file directly with others
    echo.
    echo No deployment needed - file is ready to use!
    
) else if "%DEPLOY_CHOICE%"=="6" (
    echo Skipping deployment
) else (
    echo Invalid choice
)

echo.
echo ================================================
echo   Deployment Complete!
echo ================================================
echo.
echo Next Steps:
echo 1. If you deployed frontend: Open the URL provided
echo 2. If you deployed backend: Update frontend to use your API URL
echo 3. Customize the scrapers for real eTender.gov.za HTML
echo 4. Test the application thoroughly
echo.
echo All done! Check README.md for more information.
echo.
pause
