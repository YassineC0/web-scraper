# scrapers/efsa_scraper.py
from base_scraper import BaseWebScraper
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)

class EfsaScraper(BaseWebScraper):
    """Scraper for EFSA pesticide approvals"""
    
    async def extract_content(self, search_query: str = "pesticide", **kwargs):
        """
        Scrape EFSA website for pesticide information
        
        Args:
            search_query: What to search for (default: pesticide)
        """
        # Find and click search box
        try:
            search_input = await self.page.query_selector('input[type="search"]')
            if search_input:
                await search_input.fill(search_query)
                await search_input.press('Enter')
                await self.page.wait_for_load_state('networkidle', timeout=10000)
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        
        # Extract results
        results = await self.page.query_selector_all('article, div.result-item, li.search-result')
        
        logger.info(f"Found {len(results)} results")
        
        for result in results:
            try:
                # Get title
                title_elem = await result.query_selector('h2, h3, a')
                title = await title_elem.inner_text() if title_elem else "No title"
                
                # Get content/description
                content_elem = await result.query_selector('p, div.description, span.summary')
                content = await content_elem.inner_text() if content_elem else "No content"
                
                # Get link
                link_elem = await result.query_selector('a')
                link = await link_elem.get_attribute('href') if link_elem else self.page.url
                
                # Check for PDF
                pdf_link = await result.query_selector('a[href*=".pdf"]')
                if pdf_link:
                    pdf_url = await pdf_link.get_attribute('href')
                    pdf_path = await self.download_pdf(self.page, pdf_url)
                    
                    if pdf_path:
                        pdf_text = self.extract_text_from_pdf(pdf_path)
                        self._add_result(
                            title=title,
                            content=pdf_text,
                            source=link,
                            category='phytosanitaire',
                            pdf_source=pdf_url
                        )
                else:
                    self._add_result(
                        title=title,
                        content=content,
                        source=link,
                        category='phytosanitaire'
                    )
            
            except Exception as e:
                logger.warning(f"Error processing result: {e}")
                continue