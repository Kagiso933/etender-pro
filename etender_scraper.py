#!/usr/bin/env python3
"""
eTender.gov.za IT Tender Scraper
Scrapes IT tenders from South African government tender portal
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import re
import logging
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ETenderScraper:
    """Main scraper class for eTender.gov.za"""
    
    def __init__(self):
        self.base_url = "https://etender.gov.za"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # IT-related keywords for filtering
        self.it_keywords = [
            'software', 'hardware', 'IT', 'information technology',
            'computer', 'network', 'server', 'cloud', 'database',
            'cybersecurity', 'security', 'ERP', 'CRM', 'system',
            'application', 'web', 'digital', 'technology', 'infrastructure'
        ]
        
        self.categories = {
            'Software Development': ['software', 'development', 'programming', 'erp', 'crm'],
            'IT Infrastructure': ['infrastructure', 'network', 'server', 'hardware', 'cabling'],
            'Cybersecurity': ['security', 'cybersecurity', 'firewall', 'penetration'],
            'Cloud Services': ['cloud', 'azure', 'aws', 'saas', 'migration'],
            'Data & Analytics': ['data', 'analytics', 'bi', 'database'],
        }
    
    def search_tenders(self, max_pages=5) -> List[Dict]:
        """Search for tenders on eTender portal"""
        logger.info(f"Searching tenders (max {max_pages} pages)...")
        tenders = []
        
        try:
            # Example implementation - actual selectors need to match real site
            for page in range(1, max_pages + 1):
                url = f"{self.base_url}/tenders?page={page}&category=IT"
                response = self.session.get(url, timeout=30)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch page {page}: {response.status_code}")
                    continue
                
                soup = BeautifulSoup(response.content, 'html.parser')
                tender_items = self._extract_tenders_from_page(soup)
                tenders.extend(tender_items)
                
                logger.info(f"Page {page}: Found {len(tender_items)} tenders")
                time.sleep(2)  # Respectful scraping delay
        
        except Exception as e:
            logger.error(f"Error during search: {e}")
        
        return tenders
    
    def _extract_tenders_from_page(self, soup) -> List[Dict]:
        """Extract tender data from page HTML"""
        tenders = []
        
        # NOTE: These selectors are examples and need to be updated
        # based on the actual HTML structure of etender.gov.za
        tender_items = soup.find_all('div', class_='tender-item')
        
        for item in tender_items:
            try:
                tender = {
                    'id': item.get('data-id', f'T{int(time.time())}'),
                    'title': self._safe_extract(item, 'h3', 'tender-title'),
                    'department': self._safe_extract(item, 'span', 'department'),
                    'value': self._safe_extract(item, 'span', 'value'),
                    'closingDate': self._parse_closing_date(item),
                    'description': self._safe_extract(item, 'p', 'description'),
                    'category': '',
                    'link': self._extract_link(item),
                    'requirements': [],
                    'technicalSpecs': [],
                    'scrapedAt': datetime.now().isoformat()
                }
                
                # Only include if IT-related
                if self._is_it_related(tender):
                    tender['category'] = self._categorize(tender)
                    tenders.append(tender)
                    
            except Exception as e:
                logger.error(f"Error parsing tender item: {e}")
                continue
        
        return tenders
    
    def _safe_extract(self, element, tag, class_name=''):
        """Safely extract text from HTML element"""
        try:
            if class_name:
                found = element.find(tag, class_=class_name)
            else:
                found = element.find(tag)
            return found.text.strip() if found else ''
        except:
            return ''
    
    def _extract_link(self, element):
        """Extract tender detail link"""
        try:
            link = element.find('a', class_='tender-link')
            if link and link.get('href'):
                href = link['href']
                if href.startswith('http'):
                    return href
                return self.base_url + href
        except:
            pass
        return ''
    
    def _parse_closing_date(self, element):
        """Parse and format closing date"""
        try:
            date_elem = element.find('span', class_='closing-date')
            if date_elem:
                date_str = date_elem.text.strip()
                # Try multiple date formats
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d %B %Y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except:
                        continue
                return date_str
        except:
            pass
        return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    def _is_it_related(self, tender) -> bool:
        """Check if tender is IT-related"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        return any(kw.lower() in text for kw in self.it_keywords)
    
    def _categorize(self, tender) -> str:
        """Categorize tender based on keywords"""
        text = f"{tender.get('title', '')} {tender.get('description', '')}".lower()
        
        for category, keywords in self.categories.items():
            if any(kw in text for kw in keywords):
                return category
        
        return 'General IT Services'
    
    def get_tender_details(self, tender_url: str) -> Dict:
        """Fetch detailed information for a specific tender"""
        try:
            response = self.session.get(tender_url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            details = {
                'requirements': self._extract_list(soup, 'requirements'),
                'technicalSpecs': self._extract_list(soup, 'specifications'),
                'documents': self._extract_documents(soup),
            }
            
            time.sleep(1)
            return details
        except Exception as e:
            logger.error(f"Error fetching details: {e}")
            return {}
    
    def _extract_list(self, soup, section_id):
        """Extract list items from a section"""
        try:
            section = soup.find('div', id=section_id)
            if section:
                items = section.find_all('li')
                return [item.text.strip() for item in items]
        except:
            pass
        return []
    
    def _extract_documents(self, soup):
        """Extract downloadable documents"""
        docs = []
        try:
            doc_section = soup.find('div', id='documents')
            if doc_section:
                links = doc_section.find_all('a')
                for link in links:
                    if link.get('href'):
                        docs.append({
                            'name': link.text.strip(),
                            'url': link['href']
                        })
        except:
            pass
        return docs
    
    def enrich_tender(self, tender: Dict) -> Dict:
        """Enrich tender with additional details"""
        if tender.get('link'):
            details = self.get_tender_details(tender['link'])
            tender.update(details)
        
        # Calculate days remaining
        try:
            closing = datetime.strptime(tender['closingDate'], '%Y-%m-%d')
            days = (closing - datetime.now()).days
            tender['daysRemaining'] = max(0, days)
        except:
            tender['daysRemaining'] = 0
        
        return tender
    
    def run(self, output_file='tenders.json', max_pages=5, enrich=True):
        """Main execution method"""
        logger.info("Starting eTender scraper...")
        
        # Search tenders
        tenders = self.search_tenders(max_pages=max_pages)
        logger.info(f"Found {len(tenders)} IT tenders")
        
        # Enrich with details (limited to avoid too many requests)
        if enrich and tenders:
            enriched = []
            for i, tender in enumerate(tenders[:15], 1):
                logger.info(f"Enriching {i}/{min(15, len(tenders))}: {tender.get('id')}")
                enriched.append(self.enrich_tender(tender))
                time.sleep(2)
            tenders = enriched
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tenders, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(tenders)} tenders to {output_file}")
        return tenders


def main():
    """CLI entry point"""
    scraper = ETenderScraper()
    tenders = scraper.run(
        output_file='etender_data.json',
        max_pages=5,
        enrich=True
    )
    
    print(f"\n{'='*60}")
    print(f"Scraping Complete - Found {len(tenders)} IT Tenders")
    print(f"{'='*60}")
    
    if tenders:
        categories = {}
        for t in tenders:
            cat = t.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\nBy Category:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")


if __name__ == '__main__':
    main()
