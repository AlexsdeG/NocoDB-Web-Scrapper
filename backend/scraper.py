import asyncio
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    """Web scraper for extracting data from websites."""
    
    def __init__(self):
        self.browser = None
        self.playwright = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
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
                if element:
                    text = element.get_text(strip=True)
                    logger.debug(f"Found element by ID '{selector_value}': {text[:50]}...")
                    return text
                else:
                    logger.debug(f"No element found with ID '{selector_value}'")
                    return None
            
            elif selector_type == "class":
                elements = soup.find_all(class_=selector_value)
                if elements:
                    text = elements[0].get_text(strip=True)
                    logger.debug(f"Found element by class '{selector_value}': {text[:50]}...")
                    return text
                else:
                    logger.debug(f"No element found with class '{selector_value}'")
                    return None
            
            elif selector_type == "css":
                element = soup.select_one(selector_value)
                if element:
                    text = element.get_text(strip=True)
                    logger.debug(f"Found element by CSS '{selector_value}': {text[:50]}...")
                    return text
                else:
                    logger.debug(f"No element found with CSS '{selector_value}'")
                    return None
            
            elif selector_type == "xpath":
                # For XPath, we'd need a different library like lxml
                # For now, we'll try to convert simple XPath to CSS
                css_selector = selector_value.replace('//', '').replace('[', '').replace(']', '')
                element = soup.select_one(css_selector)
                if element:
                    text = element.get_text(strip=True)
                    logger.debug(f"Found element by XPath '{selector_value}': {text[:50]}...")
                    return text
                else:
                    logger.debug(f"No element found with XPath '{selector_value}'")
                    return None
            
            else:
                logger.warning(f"Unknown selector type: {selector_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting with selector {selector_type}='{selector_value}': {e}")
            return None
    
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
            # Create a new page and navigate to the URL
            page = await self.browser.new_page()
            
            # Set a reasonable timeout
            page.set_default_timeout(30000)
            
            # Navigate to the URL and wait for content to load
            await page.goto(url, wait_until="networkidle")
            
            # Wait a bit more for dynamic content to load
            await page.wait_for_timeout(2000)
            
            # Get the page content
            content = await page.content()
            await page.close()
            
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
            logger.debug(f"Extracted data values: {extracted_data}")
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