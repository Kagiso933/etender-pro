# Quick Start Guide - SA eTender Pro

Get your tender management tool live in minutes!

## 🚀 Fastest Path to Live (3 Steps - 5 Minutes)

### Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository (e.g., "etender-pro")
3. **Don't initialize** with README, .gitignore, or license
4. Copy the repository URL (e.g., `https://github.com/yourusername/etender-pro.git`)

### Step 2: Run Deployment Script

**On Mac/Linux:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**On Windows:**
```
deploy.bat
```

### Step 3: Follow the Prompts

The script will:
1. Initialize Git (if needed)
2. Ask for your GitHub URL → **Paste the URL from Step 1**
3. Commit and push your code
4. Ask which platform to deploy to → **Choose option 1 (Netlify)**

That's it! Your tool will be live at a Netlify URL.

---

## 📋 Manual Deployment (If Scripts Don't Work)

### Option A: Deploy to Netlify (Frontend Only)

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_GITHUB_URL
   git push -u origin main
   ```

2. **Deploy on Netlify:**
   - Go to https://app.netlify.com
   - Click "Add new site" → "Import an existing project"
   - Select GitHub and authorize
   - Choose your repository
   - Click "Deploy site"

3. **Done!** Your site will be live at `https://your-site.netlify.app`

### Option B: Deploy Backend to Railway

1. **Push to GitHub** (same as above)

2. **Deploy on Railway:**
   - Go to https://railway.app
   - Sign up with GitHub
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway auto-detects Node.js and deploys

3. **Add Environment Variables:**
   - In Railway dashboard, click your service
   - Go to "Variables" tab
   - Add:
     - `PORT` = `3001`
     - `ANTHROPIC_API_KEY` = `your_api_key_here`

4. **Get Your API URL:**
   - Railway will give you a URL like `https://your-app.railway.app`
   - This is your backend API

5. **Update Frontend:**
   - Replace API calls in frontend to use your Railway URL
   - Redeploy frontend to Netlify

---

## 🎯 Super Simple Path (No Deployment)

Don't want to deploy at all? Just use it locally:

1. **Open the HTML file:**
   - Double-click `etender-tool-standalone.html`
   - Works immediately in any browser!

2. **Or run backend locally:**
   ```bash
   npm install
   cp .env.example .env
   npm start
   ```
   Then open http://localhost:3001

---

## 🔑 Getting an Anthropic API Key

The AI features need an API key:

1. Go to https://console.anthropic.com
2. Sign up or login
3. Go to "API Keys"
4. Click "Create Key"
5. Copy your key
6. Add to `.env` file:
   ```
   ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
   ```

**Free tier:** $5 credit, then pay-as-you-go (~$0.01 per analysis)

---

## 📱 Deployment Checklist

### Frontend Deployed ✅
- [ ] Code pushed to GitHub
- [ ] Deployed to Netlify/Vercel
- [ ] Site loads correctly
- [ ] AI features work (needs API key)
- [ ] Sample tenders display

### Backend Deployed ✅
- [ ] Code pushed to GitHub
- [ ] Deployed to Railway/Render
- [ ] Environment variables set
- [ ] `/health` endpoint responds
- [ ] Frontend connected to backend API

### Production Ready ✅
- [ ] Scrapers customized for real eTender.gov.za HTML
- [ ] Tested with live tender data
- [ ] API key secured (not in frontend code)
- [ ] Error handling tested
- [ ] Mobile responsive

---

## 🐛 Common Issues & Fixes

### "Push rejected" when pushing to GitHub
**Fix:** You may need to authenticate
```bash
# Use GitHub CLI
gh auth login

# Or use Personal Access Token
git remote set-url origin https://USERNAME:TOKEN@github.com/username/repo.git
```

### Netlify build fails
**Fix:** For standalone HTML, no build is needed
- Check `netlify.toml` has correct settings
- Or just drag-and-drop the HTML file in Netlify UI

### "Module not found" errors
**Fix:** Install dependencies
```bash
npm install
# or
pip install -r requirements.txt
```

### CORS errors when calling backend
**Fix:** Add your frontend URL to backend `.env`
```
ALLOWED_ORIGINS=https://your-site.netlify.app
```

### AI features not working
**Fix:** Check API key is set correctly
- Verify in `.env` file
- Check browser console for error messages
- Ensure you have API credits

---

## 📞 Need Help?

1. **Check the logs:**
   - Browser console (F12) for frontend errors
   - Backend logs in Railway/Render dashboard
   - Terminal output if running locally

2. **Review documentation:**
   - `README.md` - Overview
   - `BACKEND_SETUP.md` - Backend details
   - `DEPLOYMENT_GUIDE.md` - Frontend deployment

3. **Test components individually:**
   - Does standalone HTML work locally?
   - Does backend `/health` endpoint respond?
   - Are environment variables set?

---

## 🎓 Learning Path

**Day 1:** Get it running locally
- Run standalone HTML
- Explore features with sample data

**Day 2:** Deploy frontend
- Push to GitHub
- Deploy to Netlify
- Test AI features

**Day 3:** Add backend
- Deploy to Railway
- Connect frontend to API
- Test scraping with sample site

**Week 2:** Customize for production
- Inspect eTender.gov.za HTML
- Update scraper selectors
- Test with real data
- Add monitoring

---

## ✨ Next Steps

Once deployed:

1. **Test thoroughly** with the sample data
2. **Customize scrapers** for real eTender.gov.za (see BACKEND_SETUP.md)
3. **Add monitoring** (UptimeRobot, Sentry, etc.)
4. **Set up alerts** for scraper failures
5. **Iterate and improve** based on usage

---

**You're all set! Questions? Check the other documentation files or the inline code comments.**
