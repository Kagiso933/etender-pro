const express = require('express');
const cors = require('cors');
const axios = require('axios');
const cheerio = require('cheerio');
const cron = require('node-cron');
const helmet = require('helmet');
const fs = require('fs').promises;
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(helmet());
app.use(cors());
app.use(express.json());

// In-memory cache for tender data
let tenderCache = [];
let lastScrapeTime = null;

// IT keywords for filtering
const IT_KEYWORDS = [
    'software', 'hardware', 'IT', 'information technology',
    'computer', 'network', 'server', 'cloud', 'database',
    'cybersecurity', 'security', 'ERP', 'CRM', 'system'
];

/**
 * Web scraper for eTender.gov.za
 */
async function scrapeTenders() {
    console.log('[SCRAPER] Starting tender scrape...');
    const tenders = [];
    
    try {
        // NOTE: This is a template implementation
        // The actual selectors and URLs need to match etender.gov.za structure
        
        const baseUrl = 'https://etender.gov.za';
        const searchUrl = `${baseUrl}/tenders`;
        
        // Fetch tender listing page
        const response = await axios.get(searchUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            timeout: 30000
        });
        
        const $ = cheerio.load(response.data);
        
        // Parse tender items (adjust selector based on actual HTML)
        $('.tender-item').each((index, element) => {
            try {
                const tender = {
                    id: $(element).attr('data-id') || `T${Date.now()}-${index}`,
                    title: $(element).find('.tender-title').text().trim(),
                    department: $(element).find('.department').text().trim(),
                    value: $(element).find('.value').text().trim(),
                    closingDate: parseTenderDate($(element).find('.closing-date').text().trim()),
                    description: $(element).find('.description').text().trim(),
                    category: '',
                    link: baseUrl + $(element).find('a').attr('href'),
                    scrapedAt: new Date().toISOString()
                };
                
                // Filter for IT-related tenders
                const searchText = `${tender.title} ${tender.description}`.toLowerCase();
                const isIT = IT_KEYWORDS.some(kw => searchText.includes(kw.toLowerCase()));
                
                if (isIT) {
                    tender.category = categorizeTender(tender);
                    tenders.push(tender);
                }
            } catch (err) {
                console.error('[SCRAPER] Error parsing tender:', err.message);
            }
        });
        
        console.log(`[SCRAPER] Found ${tenders.length} IT tenders`);
        return tenders;
        
    } catch (error) {
        console.error('[SCRAPER] Error during scrape:', error.message);
        return [];
    }
}

/**
 * Parse tender closing date
 */
function parseTenderDate(dateStr) {
    if (!dateStr) return new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
    
    try {
        // Try parsing common SA date formats
        const parts = dateStr.split(/[\/\-]/);
        if (parts.length === 3) {
            // Assume DD/MM/YYYY or DD-MM-YYYY
            const [day, month, year] = parts;
            return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        }
    } catch (err) {
        console.error('[SCRAPER] Date parse error:', err.message);
    }
    
    return new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
}

/**
 * Categorize tender based on keywords
 */
function categorizeTender(tender) {
    const text = `${tender.title} ${tender.description}`.toLowerCase();
    
    const categories = {
        'Software Development': ['software', 'development', 'programming', 'erp', 'crm'],
        'IT Infrastructure': ['infrastructure', 'network', 'server', 'hardware'],
        'Cybersecurity': ['security', 'cybersecurity', 'firewall', 'penetration'],
        'Cloud Services': ['cloud', 'azure', 'aws', 'saas'],
        'Data & Analytics': ['data', 'analytics', 'bi', 'database']
    };
    
    for (const [category, keywords] of Object.entries(categories)) {
        if (keywords.some(kw => text.includes(kw))) {
            return category;
        }
    }
    
    return 'General IT Services';
}

/**
 * Update tender cache
 */
async function updateTenderCache() {
    try {
        console.log('[CACHE] Updating tender cache...');
        const tenders = await scrapeTenders();
        
        if (tenders.length > 0) {
            tenderCache = tenders;
            lastScrapeTime = new Date();
            
            // Save to file for persistence
            await fs.writeFile(
                'tender_cache.json',
                JSON.stringify({ tenders, lastUpdate: lastScrapeTime }, null, 2)
            );
            
            console.log(`[CACHE] Updated with ${tenders.length} tenders`);
        }
    } catch (error) {
        console.error('[CACHE] Update error:', error.message);
    }
}

// API Routes

/**
 * GET /api/tenders - Get all tenders
 */
app.get('/api/tenders', (req, res) => {
    const { category, search, minValue, maxValue, closingDays } = req.query;
    
    let filtered = [...tenderCache];
    
    // Filter by category
    if (category && category !== 'all') {
        filtered = filtered.filter(t => t.category === category);
    }
    
    // Filter by search query
    if (search) {
        const query = search.toLowerCase();
        filtered = filtered.filter(t => 
            t.title.toLowerCase().includes(query) ||
            t.department.toLowerCase().includes(query) ||
            t.description.toLowerCase().includes(query)
        );
    }
    
    // Filter by value range
    if (minValue || maxValue) {
        filtered = filtered.filter(t => {
            const value = parseInt(t.value.replace(/[^\d]/g, ''));
            if (minValue && value < parseInt(minValue)) return false;
            if (maxValue && value > parseInt(maxValue)) return false;
            return true;
        });
    }
    
    // Filter by closing date
    if (closingDays) {
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() + parseInt(closingDays));
        filtered = filtered.filter(t => {
            const closing = new Date(t.closingDate);
            return closing <= cutoff;
        });
    }
    
    res.json({
        success: true,
        count: filtered.length,
        lastUpdate: lastScrapeTime,
        tenders: filtered
    });
});

/**
 * GET /api/tenders/:id - Get specific tender
 */
app.get('/api/tenders/:id', (req, res) => {
    const tender = tenderCache.find(t => t.id === req.params.id);
    
    if (!tender) {
        return res.status(404).json({
            success: false,
            error: 'Tender not found'
        });
    }
    
    res.json({
        success: true,
        tender
    });
});

/**
 * POST /api/refresh - Manually trigger scrape
 */
app.post('/api/refresh', async (req, res) => {
    try {
        await updateTenderCache();
        res.json({
            success: true,
            message: 'Cache updated successfully',
            count: tenderCache.length
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * GET /api/stats - Get statistics
 */
app.get('/api/stats', (req, res) => {
    const categories = {};
    tenderCache.forEach(t => {
        categories[t.category] = (categories[t.category] || 0) + 1;
    });
    
    res.json({
        success: true,
        total: tenderCache.length,
        lastUpdate: lastScrapeTime,
        categories
    });
});

/**
 * GET /health - Health check
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        uptime: process.uptime(),
        tenderCount: tenderCache.length,
        lastScrape: lastScrapeTime
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('[ERROR]', err);
    res.status(500).json({
        success: false,
        error: 'Internal server error'
    });
});

// Initialize
async function initialize() {
    try {
        // Try to load cached data
        const cached = await fs.readFile('tender_cache.json', 'utf-8');
        const data = JSON.parse(cached);
        tenderCache = data.tenders || [];
        lastScrapeTime = data.lastUpdate ? new Date(data.lastUpdate) : null;
        console.log(`[INIT] Loaded ${tenderCache.length} cached tenders`);
    } catch (err) {
        console.log('[INIT] No cache found, will scrape on first request');
    }
    
    // Perform initial scrape if cache is empty or old
    if (tenderCache.length === 0 || !lastScrapeTime || 
        (Date.now() - new Date(lastScrapeTime).getTime() > 6 * 60 * 60 * 1000)) {
        await updateTenderCache();
    }
    
    // Schedule automatic updates every 6 hours
    cron.schedule('0 */6 * * *', () => {
        console.log('[CRON] Running scheduled tender update...');
        updateTenderCache();
    });
    
    console.log('[CRON] Scheduled updates every 6 hours');
}

// Start server
app.listen(PORT, async () => {
    console.log(`[SERVER] Running on port ${PORT}`);
    await initialize();
});
