# scrapers/franceagrimer_scraper.py
from base_scraper import BaseWebScraper
import logging

logger = logging.getLogger(__name__)

class FranceAgrimerScraper(BaseWebScraper):
    """Scraper for FranceAgriMer advanced search"""
    
    async def extract_content(self, 
                             keywords_search: str = "passeport semence",
                             country: str = None,
                             **kwargs):
        """
        Scrape FranceAgriMer with advanced search
        
        Args:
            keywords_search: Keywords to search for
            country: Optional country filter
        """
        try:
            # Fill keywords
            title_input = await self.page.query_selector('input#titre, input[name="titre"]')
            if title_input:
                await title_input.fill(keywords_search)
                logger.info(f"Entered keywords: {keywords_search}")
            
            # Select country if specified
            if country:
                try:
                    country_select = await self.page.query_selector('select#zone, select[name="zone"]')
                    if country_select:
                        await country_select.select_option(country)
                        logger.info(f"Selected country: {country}")
                except:
                    logger.warning(f"Could not select country: {country}")
            
            # Click search button
            search_btn = await self.page.query_selector('button[type="submit"], #search-btn')
            if search_btn:
                await search_btn.click()
                await self.page.wait_for_load_state('networkidle', timeout=15000)
        
        except Exception as e:
            logger.warning(f"Search setup failed: {e}")
        
        # Extract search results
        results = await self.page.query_selector_all(
            'div.result-item, div.search-result, tr.document-row'
        )
        
        logger.info(f"Found {len(results)} documents")
        
        for result in results:
            try:
                # Get document info
                title_elem = await result.query_selector('h3, a.result-title, td.title')
                title = await title_elem.inner_text() if title_elem else "No title"
                
                desc_elem = await result.query_selector('p.description, span.summary, td.description')
                description = await desc_elem.inner_text() if desc_elem else ""
                
                # Get document link/PDF
                link_elem = await result.query_selector('a')
                link = await link_elem.get_attribute('href') if link_elem else self.page.url
                
                # Check if PDF and download
                if link and link.endswith('.pdf'):
                    pdf_path = await self.download_pdf(self.page, link)
                    
                    if pdf_path:
                        pdf_text = self.extract_text_from_pdf(pdf_path)
                        self._add_result(
                            title=title,
                            content=pdf_text,
                            source=link,
                            category='certification',
                            pdf_source=link
                        )
                else:
                    self._add_result(
                        title=title,
                        content=description,
                        source=link,
                        category='certification'
                    )
            
            except Exception as e:
                logger.warning(f"Error processing result: {e}")
                continue