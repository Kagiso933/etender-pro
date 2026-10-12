# SA eTender Pro - Complete Package

AI-Powered IT Tender Management System for South African Government Tenders

## 📦 What's Included

This package contains everything you need to run a complete tender management system:

### Frontend
- **etender-tool-standalone.html** - Ready-to-use web interface (just open in browser)
- **etender-tool.jsx** - React component version for integration

### Backend
- **server.js** - Node.js Express API server with automatic scraping
- **etender_scraper.py** - Python web scraper for eTender.gov.za
- **package.json** - Node.js dependencies
- **requirements.txt** - Python dependencies

### Configuration
- **.env.example** - Environment variables template
- **.gitignore** - Git ignore rules
- **DEPLOYMENT_GUIDE.md** - Frontend deployment instructions
- **BACKEND_SETUP.md** - Backend setup and deployment guide

## 🚀 Quick Start Options

### Option 1: Standalone HTML (Fastest - 30 seconds)

1. Download **etender-tool-standalone.html**
2. Double-click to open in your browser
3. Done! The tool is now running

**Note:** AI features work immediately, but tender data is sample data.

### Option 2: Full System with Backend (15 minutes)

1. **Set up the backend:**
   ```bash
   npm install
   cp .env.example .env
   npm start
   ```

2. **Open the frontend:**
   - Use the standalone HTML file, OR
   - Deploy the React version to Netlify/Vercel

3. **Customize the scraper:**
   - Update CSS selectors in `server.js` or `etender_scraper.py`
   - Match the actual HTML structure of eTender.gov.za

## 📖 Documentation

- **DEPLOYMENT_GUIDE.md** - How to deploy the frontend
- **BACKEND_SETUP.md** - How to set up and deploy the backend
- Both files contain detailed, step-by-step instructions

## ✨ Features

### Frontend Features
- Search and filter IT tenders by category, value, closing date
- AI-powered tender analysis (risk assessment, compliance, suppliers)
- Automated bid document generation
- Bid requirement tracking and checklist
- Beautiful, modern UI with dark theme

### Backend Features
- Automatic scraping of eTender.gov.za every 6 hours
- REST API with filtering and search
- Built-in rate limiting and respectful scraping
- Tender categorization (Software, Infrastructure, Security, Cloud, etc.)
- Health monitoring and statistics

## 🔧 Customization Required

⚠️ **Important:** The web scrapers are templates and need customization:

1. Visit https://etender.gov.za
2. Inspect the HTML structure using browser DevTools
3. Update the CSS selectors in the scraper code
4. Test with a small number of pages first

See **BACKEND_SETUP.md** for detailed instructions.

## 🌐 Deployment

### Frontend Options
- **Netlify** (recommended, free)
- **Vercel** (alternative, free)
- **GitHub Pages**
- Or just use the standalone HTML file!

### Backend Options
- **Railway.app** (recommended, free tier)
- **Render.com** (alternative, free tier)
- **Heroku** (paid but reliable)
- Run locally on your own server

## 📚 API Endpoints

When backend is running on http://localhost:3001:

- `GET /api/tenders` - Get all tenders (with filters)
- `GET /api/tenders/:id` - Get specific tender
- `POST /api/refresh` - Trigger manual scrape
- `GET /api/stats` - Get statistics
- `GET /health` - Health check

## 🔒 Security Notes

1. Never commit your `.env` file
2. Keep your Anthropic API key secure
3. Use environment variables for all secrets
4. Enable CORS only for your domains in production
5. Consider adding authentication for the API

## 📝 Legal Considerations

- Respect eTender.gov.za's terms of service
- The scrapers include rate limiting
- Check if eTender provides an official API
- Consider requesting permission for automated access

## 🐛 Troubleshooting

### Scraper Returns No Data
1. Check if eTender.gov.za structure changed
2. Verify CSS selectors match actual HTML
3. Check browser DevTools console for errors
4. Review scraper logs

### CORS Errors
1. Add your frontend URL to `ALLOWED_ORIGINS` in `.env`
2. Make sure backend is running
3. Check browser console for exact error

### AI Features Not Working
1. Verify Anthropic API key is set
2. Check API quota/credits
3. Look for error messages in console
4. Try the standalone HTML version

## 💡 Tips for Success

1. **Start Simple:** Use the standalone HTML first to test
2. **Customize Gradually:** Get the scraper working with actual eTender.gov.za HTML
3. **Test Locally:** Always test locally before deploying
4. **Monitor:** Set up logging and monitoring in production
5. **Iterate:** The scraper may need updates as eTender.gov.za changes

## 📞 Support

For detailed setup instructions, see:
- DEPLOYMENT_GUIDE.md - Frontend deployment
- BACKEND_SETUP.md - Backend setup and API documentation

## 🎯 Next Steps

1. Choose your deployment option (standalone HTML or full system)
2. Follow the relevant guide (DEPLOYMENT_GUIDE or BACKEND_SETUP)
3. Customize the scraper for eTender.gov.za
4. Deploy and start managing tenders!

## 🛠️ Tech Stack

**Frontend:**
- React 18
- Tailwind CSS (via CDN)
- Anthropic Claude API

**Backend:**
- Node.js + Express
- Python 3 + BeautifulSoup
- Cheerio (for Node.js scraping)
- Cron jobs for scheduling

---

**Built with ❤️ for South African businesses bidding on government IT tenders**
