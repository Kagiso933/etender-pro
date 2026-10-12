# Backend Setup Guide for SA eTender Pro

This guide will help you set up the backend scraper and API server for the eTender tool.

## Overview

The backend consists of two main components:

1. **Python Scraper** (`etender_scraper.py`) - Scrapes tender data from eTender.gov.za
2. **Node.js API Server** (`server.js`) - Provides REST API endpoints for the frontend

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

## Quick Start

### Option 1: Node.js Backend (Recommended)

This provides a REST API that your frontend can call.

#### 1. Install Dependencies

```bash
npm install
```

#### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your settings
```

#### 3. Start the Server

```bash
# Development mode (with auto-restart)
npm run dev

# Production mode
npm start
```

The API will be available at `http://localhost:3001`

#### 4. Update Frontend

Modify your frontend to call the API:

```javascript
// Instead of calling Anthropic API directly
const response = await fetch('http://localhost:3001/api/tenders');
const data = await response.json();
```

### Option 2: Python Scraper Only

Run the Python scraper standalone to generate a JSON file.

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Run the Scraper

```bash
python3 etender_scraper.py
```

This will create `etender_data.json` with scraped tender data.

#### 3. Use the Data

You can then load this JSON file into your frontend or import it into a database.

## API Endpoints

Once the Node.js server is running:

### GET /api/tenders
Get all tenders with optional filtering

**Query Parameters:**
- `category` - Filter by category (e.g., "Software Development")
- `search` - Search in title, department, description
- `minValue` - Minimum tender value
- `maxValue` - Maximum tender value
- `closingDays` - Tenders closing within X days

**Example:**
```bash
curl "http://localhost:3001/api/tenders?category=Software%20Development&closingDays=30"
```

### GET /api/tenders/:id
Get a specific tender by ID

### POST /api/refresh
Manually trigger a fresh scrape

### GET /api/stats
Get statistics about cached tenders

### GET /health
Health check endpoint

## Important Notes

### About eTender.gov.za Scraping

⚠️ **The scraper templates provided need to be customized** to match the actual HTML structure of eTender.gov.za.

To customize:

1. Visit https://etender.gov.za
2. Inspect the HTML structure using browser DevTools
3. Update the CSS selectors in the scraper code:
   - Find the actual class names for tender items
   - Update `.tender-item`, `.tender-title`, etc.
4. Test the scraper with small page counts first

### Legal Considerations

- Respect eTender.gov.za's terms of service
- Implement rate limiting (already included)
- Check if they provide an official API
- Consider reaching out to ask permission for automated access

### Rate Limiting

The scrapers include built-in delays:
- 2 seconds between page requests
- 1 second between detail requests

Adjust these in the code if needed, but be respectful.

## Deployment Options

### Deploy to Railway.app (Free)

1. Push your code to GitHub
2. Go to railway.app and sign up
3. Create new project from GitHub repo
4. Railway will auto-detect Node.js and deploy
5. Add environment variables in Railway dashboard

### Deploy to Render.com (Free)

1. Push code to GitHub
2. Go to render.com and sign up
3. Create new "Web Service"
4. Connect GitHub repo
5. Set build command: `npm install`
6. Set start command: `npm start`
7. Add environment variables

### Deploy to Heroku

1. Install Heroku CLI
2. Login: `heroku login`
3. Create app: `heroku create your-app-name`
4. Push code: `git push heroku main`
5. Set env vars: `heroku config:set KEY=value`

## Scheduled Updates

The Node.js server automatically scrapes new tenders every 6 hours using cron jobs.

To change the interval, edit `server.js`:

```javascript
// Current: Every 6 hours
cron.schedule('0 */6 * * *', updateTenderCache);

// Every 3 hours:
cron.schedule('0 */3 * * *', updateTenderCache);

// Every day at 9 AM:
cron.schedule('0 9 * * *', updateTenderCache);
```

## Troubleshooting

### Scraper Returns Empty Results

1. Check if eTender.gov.za structure changed
2. Verify CSS selectors using browser DevTools
3. Check if you're being blocked (User-Agent, rate limits)
4. Look at the HTML response in logs

### CORS Errors in Frontend

Add your frontend URL to ALLOWED_ORIGINS in `.env`:

```
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.netlify.app
```

### API Not Responding

1. Check if server is running: `curl http://localhost:3001/health`
2. Check logs for errors
3. Verify port 3001 is not in use
4. Check firewall settings

## Database Integration (Optional)

For production, consider storing tenders in a database:

### PostgreSQL with Supabase (Free)

```javascript
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_KEY
);

// Insert tenders
await supabase.from('tenders').insert(tenders);

// Query tenders
const { data } = await supabase
  .from('tenders')
  .select('*')
  .eq('category', 'IT Infrastructure');
```

### MongoDB Atlas (Free)

```javascript
const { MongoClient } = require('mongodb');

const client = new MongoClient(process.env.MONGODB_URI);
await client.connect();

const db = client.db('etender');
await db.collection('tenders').insertMany(tenders);
```

## Next Steps

1. **Customize the scraper** for actual eTender.gov.za HTML
2. **Test locally** with a small number of pages
3. **Deploy backend** to Railway/Render/Heroku
4. **Update frontend** to use backend API instead of direct Anthropic calls
5. **Set up monitoring** and alerts for scraper failures
6. **Consider database** for better data persistence

## Support

For issues or questions:
- Check the logs for detailed error messages
- Verify eTender.gov.za is accessible
- Test with `curl` to isolate frontend vs backend issues
- Monitor server resources (CPU, memory)

## Security Best Practices

1. Never commit `.env` file (it's in `.gitignore`)
2. Use environment variables for all secrets
3. Keep dependencies updated: `npm audit fix`
4. Use HTTPS in production
5. Implement request logging and monitoring
6. Add authentication if API will be public

---

Remember: The scraper templates are starting points. You'll need to adapt them to match the actual structure of eTender.gov.za. Happy scraping!
