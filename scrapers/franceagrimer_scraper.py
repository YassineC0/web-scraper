# scrapers/franceagrimer_scraper.py
from .base_scraper import BaseWebScraper
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

import logging
import time
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import json

logger = logging.getLogger(__name__)

class FranceAgrimerScraper(BaseWebScraper):
    """Scraper for FranceAgriMer advanced search using Selenium"""
    
    async def extract_content(self, **kwargs):
        """ 
        Scrape FranceAgriMer for ALL countries:
        1. Thématique: Exportation
        2. Zone économique: ALL COUNTRIES (one by one)
        3. Marchandise niveau1: Végétal
        4. Navigate through ALL PAGES
        5. Download ALL PDFs in parallel
        6. Extract text and create structured documents for LLM
        """
        try:
            logger.info("Starting FranceAgriMer scraper for ALL COUNTRIES and ALL PAGES...\n")
            
            # Setup Chrome options with download folder
            downloads_path = str(Path("downloads").absolute())
            Path(downloads_path).mkdir(exist_ok=True)
            
            # Create output folder for structured data
            output_path = str(Path("extracted_data").absolute())
            Path(output_path).mkdir(exist_ok=True)
            
            # First, get list of all available countries
            countries = await self._get_available_countries(downloads_path)
            logger.info(f"\n✓ Found {len(countries)} countries: {', '.join(countries[:5])}...\n")
            
            # For each country, do the search and download
            total_documents = 0
            all_extracted_data = []
            
            for country in countries:
                logger.info(f"\n{'='*80}")
                logger.info(f"SCRAPING FOR COUNTRY: {country}")
                logger.info(f"{'='*80}\n")
                
                extracted_data = await self._scrape_country(country, downloads_path, output_path)
                all_extracted_data.extend(extracted_data)
                total_documents += len(extracted_data)
                
                # Small delay between countries
                time.sleep(1)
            
            # Save all extracted data to a single JSON file for LLM
            llm_data_path = Path(output_path) / "all_documents.json"
            with open(llm_data_path, 'w', encoding='utf-8') as f:
                json.dump(all_extracted_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"\n\n{'='*80}")
            logger.info(f"✅ TOTAL: Successfully downloaded and extracted {total_documents} documents")
            logger.info(f"✅ Structured data saved to: {llm_data_path}")
            logger.info(f"{'='*80}\n")
        
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            import traceback
            traceback.print_exc()
    
    async def _get_available_countries(self, downloads_path):
        """Get list of all available countries from the Zone dropdown"""
        try:
            options = Options()
            options.add_argument('--start-maximized')
            options.add_experimental_option("prefs", {
                "download.default_directory": downloads_path,
                "download.prompt_for_download": False,
                "profile.default_content_settings.popups": 0
            })
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            url = "https://agent.expadon.fr/sites/infocom-site/accueil/recherche-avancee.html"
            logger.info(f"Navigating to {url}")
            driver.get(url)
            time.sleep(3)
            
            logger.info("Getting list of all countries...")
            
            # Find Zone input
            zone_input = None
            labels = driver.find_elements(By.TAG_NAME, "label")
            for label in labels:
                text = label.text.strip().lower()
                if "zone" in text and "pays" in text:
                    parent = label.find_element(By.XPATH, "./..")
                    inputs = parent.find_elements(By.TAG_NAME, "input")
                    if inputs:
                        zone_input = inputs[0]
                        break
            
            if zone_input:
                zone_input.click()
                time.sleep(1)
                
                # Get all dropdown options
                dropdown_options = driver.find_elements(By.XPATH, "//*[@role='option']")
                
                countries = []
                for opt in dropdown_options:
                    try:
                        text = opt.text.strip()
                        if text and len(text) > 0:
                            countries.append(text)
                    except:
                        pass
                
                driver.quit()
                return countries if countries else ["Brésil"]
            
            driver.quit()
            return ["Brésil"]
        
        except Exception as e:
            logger.warning(f"Could not get countries list: {e}. Using fallback.")
            return ["Brésil"]
    
    async def _scrape_country(self, country, downloads_path, output_path):
        """Scrape a specific country, ALL PAGES, and download all documents"""
        extracted_data = []
        
        try:
            options = Options()
            options.add_argument('--start-maximized')
            options.add_experimental_option("prefs", {
                "download.default_directory": downloads_path,
                "download.prompt_for_download": False,
                "profile.default_content_settings.popups": 0
            })
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            url = "https://agent.expadon.fr/sites/infocom-site/accueil/recherche-avancee.html"
            logger.info(f"Navigating to {url}")
            driver.get(url)
            time.sleep(2)
            
            # STEP 1: Thématique
            logger.info("Setting Thématique = Exportation")
            try:
                selects = driver.find_elements(By.TAG_NAME, "select")
                if selects:
                    Select(selects[0]).select_by_visible_text("Exportation")
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Could not set Thématique: {e}")
            
            # STEP 2: Zone économique
            logger.info(f"Setting Zone = {country}")
            try:
                zone_input = None
                labels = driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    text = label.text.strip().lower()
                    if "zone" in text and "pays" in text:
                        parent = label.find_element(By.XPATH, "./..")
                        inputs = parent.find_elements(By.TAG_NAME, "input")
                        if inputs:
                            zone_input = inputs[0]
                            break
                
                if zone_input:
                    zone_input.click()
                    time.sleep(0.5)
                    zone_input.clear()
                    
                    for c in country:
                        zone_input.send_keys(c)
                        time.sleep(0.05)
                    
                    time.sleep(0.5)
                    zone_input.send_keys("\ue015")  # Down
                    time.sleep(0.2)
                    zone_input.send_keys("\ue007")  # Enter
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Could not set Zone: {e}")
                driver.quit()
                return extracted_data
            
            # STEP 3: Marchandise
            logger.info("Setting Marchandise = Végétal")
            try:
                selects = driver.find_elements(By.TAG_NAME, "select")
                for select in selects:
                    options_list = select.find_elements(By.TAG_NAME, "option")
                    option_texts = [opt.text for opt in options_list]
                    
                    if "Végétal" in option_texts:
                        Select(select).select_by_visible_text("Végétal")
                        time.sleep(0.5)
                        break
            except Exception as e:
                logger.warning(f"Could not set Marchandise: {e}")
            
            # STEP 4: Click search
            logger.info("Clicking search button...")
            try:
                search_button = None
                try:
                    search_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Lancer')]")
                except:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    if buttons:
                        search_button = buttons[-1]
                
                if search_button:
                    search_button.click()
                    time.sleep(4)
            except Exception as e:
                logger.warning(f"Could not click search: {e}")
            
            # STEP 5: Navigate through ALL PAGES
            current_page = 1
            total_documents_country = 0
            
            while True:
                logger.info(f"\n--- Processing PAGE {current_page} ---")
                
                # Get all documents on current page
                documents = driver.find_elements(By.XPATH, "//div[contains(@class, 'result')]")
                logger.info(f"Found {len(documents)} documents on page {current_page}")
                pagination_elements = driver.find_elements(By.XPATH, "//*")

                logger.info("=== PAGINATION DEBUG ===")

                for elem in pagination_elements:
                    try:
                        text = elem.text.strip()

                        if text in ["1", "2", "3", "4", "5", "Suivant", ">"]:
                            logger.info(
                                f"TAG={elem.tag_name} TEXT='{text}' "
                                f"CLASS='{elem.get_attribute('class')}' "
                                f"ID='{elem.get_attribute('id')}'"
                            )
                    except:
                        pass
                
                if len(documents) == 0:
                    logger.info("No documents found, pagination complete.")
                    break
                
                # Collect all download info BEFORE closing browser
                downloads_info = []
                for i, doc in enumerate(documents):
                    try:
                        title_elem = doc.find_element(By.XPATH, ".//h2 | .//h3 | .//strong | .//b")
                        title = title_elem.text.strip()
                        
                        download_button = None
                        try:
                            download_button = doc.find_element(By.XPATH, ".//a[contains(@href, 'download') or contains(text(), 'Télécharger')]")
                        except:
                            try:
                                download_button = doc.find_element(By.XPATH, ".//button[contains(text(), 'Télécharger')]")
                            except:
                                try:
                                    download_button = doc.find_element(By.XPATH, ".//a[contains(@href, '.pdf')]")
                                except:
                                    pass
                        
                        if download_button:
                            href = None
                            try:
                                href = download_button.get_attribute('href')
                            except:
                                pass
                            
                            downloads_info.append({
                                'title': title,
                                'button': download_button,
                                'href': href,
                                'index': i+1,
                                'country': country
                            })
                    except:
                        pass
                
                # STEP 6: Parallel downloads for this page
                logger.info(f"Downloading {len(downloads_info)} documents from page {current_page} in parallel...")
                
                # Use ThreadPoolExecutor for parallel downloads
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = []
                    
                    for info in downloads_info:
                        future = executor.submit(
                            self._download_and_extract_pdf,
                            driver,
                            info['button'],
                            info['title'],
                            info['href'],
                            downloads_path,
                            info['country'],
                            output_path
                        )
                        futures.append(future)
                    
                    # Wait for all downloads to complete
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            if result:
                                extracted_data.append(result)
                                total_documents_country += 1
                        except Exception as e:
                            logger.error(f"Download failed: {e}")
                
                logger.info(f"✓ Downloaded {total_documents_country} documents from page {current_page} for {country}\n")
                
                # STEP 7: Look for next page button
                # STEP 7: Pagination
                try:
                    logger.info(f"Trying to go to page {current_page + 1}")

                    next_page_xpath = f"//a[contains(text(), '{current_page + 1}')]"

                    next_page_button = driver.find_element(By.XPATH, next_page_xpath)

                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        next_page_button
                    )

                    time.sleep(1)

                    driver.execute_script("arguments[0].click();", next_page_button)

                    logger.info(f"✓ Switched to page {current_page + 1}")

                    current_page += 1

                    time.sleep(4)

                except Exception as e:
                    logger.info(f"No more pages found: {e}")
                break
            
            logger.info(f"✓ Total documents for {country}: {total_documents_country}\n")
            
            driver.quit()
            return extracted_data
        
        except Exception as e:
            logger.error(f"Error scraping country {country}: {e}")
            return extracted_data
    
    def _download_and_extract_pdf(self, driver, button, title, href, downloads_path, country, output_path):
        """Download and extract PDF (called in parallel)"""
        try:
            logger.info(f"  [{title[:50]}...] Downloading...")
            
            # Click button
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
            time.sleep(0.2)
            button.click()
            time.sleep(2)
            
            # Find downloaded file
            downloaded_file = self._find_latest_file(downloads_path)
            
            if downloaded_file:
                # Sanitize and rename with proper title
                new_name = self._sanitize_filename(f"{country}_{title}") + ".pdf"
                new_path = Path(downloads_path) / new_name
                
                try:
                    Path(downloaded_file).rename(new_path)
                except:
                    # File might already exist, add timestamp
                    import uuid
                    new_name = self._sanitize_filename(f"{country}_{title}_{uuid.uuid4().hex[:8]}") + ".pdf"
                    new_path = Path(downloads_path) / new_name
                    Path(downloaded_file).rename(new_path)
                
                logger.info(f"  [{title[:50]}...] ✓ Saved")
                
                # Extract text
                pdf_text = self.extract_text_from_pdf(str(new_path))
                
                if pdf_text and len(pdf_text.strip()) > 50:
                    # Create structured data for LLM
                    structured_data = {
                        'title': title,
                        'country': country,
                        'filename': new_name,
                        'file_path': str(new_path),
                        'content': pdf_text,
                        'content_length': len(pdf_text),
                        'category': 'certification'
                    }
                    
                    # Also add to base scraper results
                    self._add_result(
                        title=f"[{country}] {title}",
                        content=pdf_text,
                        source=str(new_path),
                        category='certification',
                        pdf_source=str(new_path)
                    )
                    
                    return structured_data
            
            return None
        
        except Exception as e:
            logger.error(f"Error downloading {title}: {e}")
            return None
    
    def _find_latest_file(self, directory):
        """Find the most recently modified file in directory"""
        files = list(Path(directory).glob('*'))
        if not files:
            return None
        
        # Exclude JSON files
        pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
        if not pdf_files:
            return None
        
        latest = max(pdf_files, key=lambda p: p.stat().st_mtime)
        return str(latest)
    
    def _sanitize_filename(self, filename):
        """Remove illegal characters from filename"""
        illegal_chars = '<>:"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # Remove multiple spaces
        filename = ' '.join(filename.split())
        
        return filename[:100]