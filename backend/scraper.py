import asyncio
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import playwright, but make it optional
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available, will use alternative methods")

class WebScraper:
    """Web scraper for extracting data from websites."""
    
    def __init__(self, use_playwright=True):
        self.browser = None
        self.playwright = None
        self.use_playwright = use_playwright and PLAYWRIGHT_AVAILABLE
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.use_playwright:
            try:
                self.playwright = await async_playwright().start()
                # Try to launch browser with error handling and more permissive flags
                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-gpu',
                            '--disable-software-rasterizer',
                            '--disable-web-security',
                            '--disable-features=IsolateOrigins,site-per-process'
                        ],
                        chromium_sandbox=False
                    )
                    logger.info("Successfully launched Chromium browser")
                except Exception as e:
                    logger.error(f"Failed to launch browser: {e}")
                    logger.info("Trying Firefox as alternative...")
                    # Try Firefox as alternative
                    try:
                        self.browser = await self.playwright.firefox.launch(
                            headless=True,
                            args=['--no-sandbox']
                        )
                        logger.info("Successfully launched Firefox browser")
                    except Exception as e2:
                        logger.error(f"Firefox also failed: {e2}")
                        logger.info("Falling back to requests-based scraping")
                        if self.playwright:
                            await self.playwright.stop()
                        self.playwright = None
                        self.browser = None
                        self.use_playwright = False
            except Exception as e:
                logger.error(f"Playwright initialization failed: {e}")
                self.use_playwright = False
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common currency symbols and clean numbers
        text = re.sub(r'[€$£¥]', '', text)
        text = re.sub(r'[.,](?=\d{3})', '', text)  # Remove thousand separators
        text = re.sub(r',', '.', text)  # Replace decimal comma with dot
        
        return text
    
    def _convert_to_number(self, text: str) -> Optional[float]:
        """Convert text to number if possible."""
        cleaned = self._clean_text(text)
        
        # Extract numbers
        match = re.search(r'[\d.]+', cleaned)
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        
        return None
    
    async def _extract_with_selector(self, soup: BeautifulSoup, selector_config: Dict[str, str]) -> Optional[str]:
        """Extract data using a selector configuration."""
        selector_type = selector_config.get("type", "")
        selector_value = selector_config.get("value", "")
        
        try:
            if selector_type == "id":
                element = soup.find(id=selector_value)
                return element.get_text(strip=True) if element else None
            
            elif selector_type == "class":
                elements = soup.find_all(class_=selector_value)
                return elements[0].get_text(strip=True) if elements else None
            
            elif selector_type == "css":
                element = soup.select_one(selector_value)
                return element.get_text(strip=True) if element else None
            
            elif selector_type == "xpath":
                # For XPath, we'd need a different library like lxml
                # For now, we'll try to convert simple XPath to CSS
                css_selector = selector_value.replace('//', '').replace('[', '').replace(']', '')
                element = soup.select_one(css_selector)
                return element.get_text(strip=True) if element else None
            
            else:
                logger.warning(f"Unknown selector type: {selector_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting with selector {selector_type}='{selector_value}': {e}")
            return None
    
    async def _fetch_with_requests(self, url: str) -> str:
        """Fallback method using requests library."""
        import requests
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Website requires browser authentication - Playwright/browser is required for this site")
            raise
    
    async def scrape_apartment_data(self, url: str, scraper_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape apartment data from a URL using the provided configuration.
        
        Args:
            url: The URL to scrape
            scraper_config: Configuration dictionary containing selectors and field mappings
            
        Returns:
            Dictionary containing the scraped data
        """
        logger.info(f"Scraping URL: {url}")
        
        try:
            # Get page content
            if self.use_playwright and self.browser:
                # Use Playwright
                page = await self.browser.new_page()
                
                # Set extra headers to avoid detection
                await page.set_extra_http_headers({
                    'Accept-Language': 'en-US,en;q=0.9,de;q=0.8'
                })
                
                page.set_default_timeout(30000)
                await page.goto(url, wait_until="networkidle")
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                content = await page.content()
                await page.close()
            else:
                # Fallback to requests
                logger.warning("Using requests-based scraping - may not work with all websites")
                content = await self._fetch_with_requests(url)
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract data using selectors
            extracted_data = {}
            selectors = scraper_config.get("selectors", {})
            
            for field_name, selector_config in selectors.items():
                logger.debug(f"Extracting {field_name} with selector: {selector_config}")
                
                raw_value = await self._extract_with_selector(soup, selector_config)
                
                if raw_value:
                    # Try to convert to number for certain fields
                    if field_name in ["warm_rent", "deposit", "area", "rooms"]:
                        numeric_value = self._convert_to_number(raw_value)
                        extracted_data[field_name] = numeric_value if numeric_value is not None else raw_value
                    else:
                        extracted_data[field_name] = self._clean_text(raw_value)
                else:
                    extracted_data[field_name] = None
                    logger.warning(f"Could not extract {field_name}")
            
            logger.info(f"Successfully extracted data: {list(extracted_data.keys())}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            raise Exception(f"Scraping failed: {str(e)}")

async def scrape_apartment_data(url: str, scraper_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to scrape apartment data.
    
    Args:
        url: The URL to scrape
        scraper_config: Configuration dictionary containing selectors and field mappings
        
    Returns:
        Dictionary containing the scraped data
    """
    async with WebScraper() as scraper:
        return await scraper.scrape_apartment_data(url, scraper_config)

def extract_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None