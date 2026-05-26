# scrapers/gnis_scraper.py
from base_scraper import BaseWebScraper
import logging

logger = logging.getLogger(__name__)

class GnisScraper(BaseWebScraper):
    """Scraper for GNIS seed certifications"""
    
    async def extract_content(self, search_query: str = "semence", **kwargs):
        """
        Scrape GNIS website for seed certification data
        
        Args:
            search_query: What to search for (default: semence)
        """
        # Fill search form
        try:
            title_input = await self.page.query_selector('input[placeholder*="titre"], input#titre')
            if title_input:
                await title_input.fill(search_query)
            
            search_btn = await self.page.query_selector('button[type="submit"], input[type="submit"]')
            if search_btn:
                await search_btn.click()
                await self.page.wait_for_load_state('networkidle', timeout=10000)
        
        except Exception as e:
            logger.warning(f"Form submission failed: {e}")
        
        # Extract variety information
        variety_items = await self.page.query_selector_all(
            'div.variety-item, tr.variety-row, li.variety'
        )
        
        logger.info(f"Found {len(variety_items)} varieties")
        
        for item in variety_items:
            try:
                # Extract variety data
                name_elem = await item.query_selector('h3, td.name, span.variety-name')
                name = await name_elem.inner_text() if name_elem else "No name"
                
                species_elem = await item.query_selector('span.species, td.species')
                species = await species_elem.inner_text() if species_elem else ""
                
                approval_elem = await item.query_selector('span.approval-date, td.date')
                approval_date = await approval_elem.inner_text() if approval_elem else ""
                
                purity_elem = await item.query_selector('span.purity, td.purity')
                purity = await purity_elem.inner_text() if purity_elem else ""
                
                # Combine into content
                content = f"Variété: {name}\nEspèce: {species}\nDate approbation: {approval_date}\nPureté: {purity}"
                
                # Check for PDF document
                pdf_link = await item.query_selector('a[href*=".pdf"]')
                if pdf_link:
                    pdf_url = await pdf_link.get_attribute('href')
                    pdf_path = await self.download_pdf(self.page, pdf_url)
                    
                    if pdf_path:
                        pdf_text = self.extract_text_from_pdf(pdf_path)
                        content = f"{content}\n\nDocumentation:\n{pdf_text[:500]}"
                
                self._add_result(
                    title=name,
                    content=content,
                    source=self.page.url,
                    category='certification'
                )
            
            except Exception as e:
                logger.warning(f"Error processing variety: {e}")
                continue