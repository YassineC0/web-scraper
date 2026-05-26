# base_scraper.py
import os
import json
from typing import Dict, List
from pathlib import Path
from datetime import datetime
import asyncio
from playwright.async_api import async_playwright, Page, Browser
import requests
from langdetect import detect
from deep_translator import GoogleTranslator
import pdfplumber
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseWebScraper:
    """Base class for all website scrapers"""
    
    def __init__(self, keywords_file: str = "keywords.json", output_file: str = None):
        """
        Initialize scraper with keyword configuration
        
        Args:
            keywords_file: Path to JSON file with keywords
            output_file: Optional output file to save results (JSON)
        """
        self.keywords = self._load_keywords(keywords_file)
        self.output_file = output_file or f"output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.browser = None
        self.page = None
        self.downloads_folder = Path("downloads")
        self.downloads_folder.mkdir(exist_ok=True)
        self.results = []
    
    def _load_keywords(self, keywords_file: str) -> Dict[str, List[str]]:
        """Load keywords from JSON config file"""
        try:
            with open(keywords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Keywords file not found: {keywords_file}")
            return {}
    
    async def setup(self):
        """Initialize Playwright browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
    
    async def teardown(self):
        """Close Playwright browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _detect_and_translate(self, text: str) -> str:
        """
        Detect language and translate to French if needed
        
        Args:
            text: Text to translate
            
        Returns:
            French text
        """
        try:
            # Detect language
            detected_lang = detect(text)
            
            # If already French, return as-is
            if detected_lang == 'fr':
                return text
            
            # Translate to French
            logger.info(f"Translating from {detected_lang} to French")
            translator = GoogleTranslator(source_language=detected_lang, target_language='fr')
            translated = translator.translate(text)
            return translated
        
        except Exception as e:
            logger.warning(f"Translation error: {e}. Returning original text.")
            return text
    
    def _filter_by_keywords(self, text: str, category: str = None) -> bool:
        """
        Check if text contains relevant keywords
        
        Args:
            text: Text to check
            category: Optional category to filter keywords
            
        Returns:
            True if relevant keywords found
        """
        text_lower = text.lower()
        
        # If category specified, check only that category
        if category and category in self.keywords:
            keywords_to_check = self.keywords[category]
        else:
            # Check all keywords across all categories
            keywords_to_check = []
            for key_list in self.keywords.values():
                keywords_to_check.extend(key_list)
        
        # Return True if ANY keyword found
        return any(keyword.lower() in text_lower for keyword in keywords_to_check)
    
    async def download_pdf(self, page: Page, pdf_url: str) -> str:
        """
        Download PDF file and return path
        
        Args:
            page: Playwright page object
            pdf_url: URL of PDF file
            
        Returns:
            Path to downloaded PDF
        """
        try:
            # Handle relative URLs
            if pdf_url.startswith('/'):
                base_url = page.url.split('/')[2]
                pdf_url = f"https://{base_url}{pdf_url}"
            elif not pdf_url.startswith('http'):
                base_url = '/'.join(page.url.split('/')[:-1])
                pdf_url = f"{base_url}/{pdf_url}"
            
            # Download file
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Save file
            file_name = pdf_url.split('/')[-1] or 'document.pdf'
            file_path = self.downloads_folder / file_name
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded PDF: {file_path}")
            return str(file_path)
        
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return ""
    
    async def scrape(self, url: str, **kwargs):
        """
        Main scraping method - override in child classes
        
        Args:
            url: Website URL to scrape
            **kwargs: Additional parameters for specific scrapers
        """
        await self.setup()
        try:
            self.page = await self.browser.new_page()
            
            logger.info(f"Navigating to {url}")
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Call site-specific extraction
            await self.extract_content(**kwargs)
            
            # Save results
            self._save_results()
            
            logger.info(f"Scraping complete. Results saved to {self.output_file}")
        
        finally:
            await self.teardown()
    
    async def extract_content(self, **kwargs):
        """Override in child classes"""
        raise NotImplementedError("Child classes must implement extract_content()")
    
    def _add_result(self, title: str, content: str, source: str, category: str, pdf_source: str = None):
        """
        Add result to results list (with translation and keyword filtering)
        
        Args:
            title: Title of the content
            content: Content text
            source: URL source
            category: Content category (for keyword filtering)
            pdf_source: Original PDF URL if from PDF
        """
        # Translate content to French
        translated_content = self._detect_and_translate(content)
        translated_title = self._detect_and_translate(title)
        
        # Filter by keywords
        if not self._filter_by_keywords(translated_content, category):
            logger.debug(f"Skipped (no keywords): {title}")
            return
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'title': translated_title,
            'content': translated_content[:500],  # First 500 chars
            'full_content': translated_content,
            'source': source,
            'category': category,
            'pdf_source': pdf_source,
            'language_original': detect(content),
            'contains_keywords': self._get_matching_keywords(translated_content)
        }
        
        self.results.append(result)
        logger.info(f"Added result: {translated_title[:50]}...")
    
    def _get_matching_keywords(self, text: str) -> List[str]:
        """Get list of keywords found in text"""
        matching = []
        text_lower = text.lower()
        
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matching.append(keyword)
        
        return list(set(matching))  # Remove duplicates
    
    def _save_results(self):
        """Save results to JSON file"""
        output_data = {
            'scrape_timestamp': datetime.now().isoformat(),
            'total_results': len(self.results),
            'results': self.results
        }
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # Also print to console
        print("\n" + "="*80)
        print(f"📊 SCRAPING RESULTS ({len(self.results)} items)")
        print("="*80)
        
        for i, result in enumerate(self.results, 1):
            print(f"\n[{i}] {result['title']}")
            print(f"    🏷️  Category: {result['category']}")
            print(f"    🔗 Source: {result['source']}")
            print(f"    🗂️  Language: {result['language_original']} → French")
            print(f"    🔑 Keywords: {', '.join(result['contains_keywords'])}")
            print(f"    📝 Preview: {result['content'][:100]}...")
        
        print("\n" + "="*80)
        print(f"✅ Results saved to: {self.output_file}")
        print("="*80 + "\n")