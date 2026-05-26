# run_scraper.py
import asyncio
import sys
from scrapers.efsa_scraper import EfsaScraper
from scrapers.gnis_scraper import GnisScraper
from scrapers.franceagrimer_scraper import FranceAgrimerScraper

async def main():
    """Run multiple scrapers"""
    
    if len(sys.argv) < 2:
        print("Usage: python run_scraper.py <scraper_name> [options]")
        print("\nAvailable scrapers:")
        print("  1. efsa")
        print("  2. gnis")
        print("  3. franceagrimer")
        print("\nExample: python run_scraper.py efsa")
        print("Example: python run_scraper.py gnis --query 'maïs'")
        print("Example: python run_scraper.py franceagrimer --keywords 'passeport semence' --country 'FR'")
        return
    
    scraper_name = sys.argv[1].lower()
    
    # Parse additional arguments
    kwargs = {}
    i = 2
    while i < len(sys.argv):
        if sys.argv[i].startswith('--'):
            key = sys.argv[i][2:]
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                kwargs[key] = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        else:
            i += 1
    
    print(f"\n🚀 Starting scraper: {scraper_name}")
    print(f"📋 Parameters: {kwargs}\n")
    
    try:
        if scraper_name == 'efsa':
            scraper = EfsaScraper()
            await scraper.scrape(
                'https://www.efsa.europa.eu/en/topics/topic/pesticides',
                search_query=kwargs.get('query', 'pesticide')
            )
        
        elif scraper_name == 'gnis':
            scraper = GnisScraper()
            await scraper.scrape(
                'https://www.gnis-agri.org/',
                search_query=kwargs.get('query', 'semence')
            )
        
        elif scraper_name == 'franceagrimer':
            scraper = FranceAgrimerScraper()
            await scraper.scrape(
                'https://agent.expadon.fr/sites/infocom-site/accueil/recherche-avancee.html',
                keywords_search=kwargs.get('keywords', 'passeport semence'),
                country=kwargs.get('country', None)
            )
        
        else:
            print(f"❌ Unknown scraper: {scraper_name}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())