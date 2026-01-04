from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SCRAPER_CONFIG
from database.db import get_category_id, get_platform_id, save_product, save_price


class ShopeeScraper:
    def __init__(self, headless=None):
        self.headless = headless if headless is not None else SCRAPER_CONFIG['headless']
        self.delay = SCRAPER_CONFIG['delay_between_requests']
        self.platform_id = get_platform_id('Shopee')
        self.base_url = "https://shopee.com.my"

    def search_products(self, keyword, category_slug='ram', max_pages=1):
        """Search for products and save to database"""
        category_id = get_category_id(category_slug)
        all_products = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            for page_num in range(max_pages):
                search_url = f"{self.base_url}/search?keyword={keyword}&page={page_num}"
                print(f"Scraping: {search_url}")

                try:
                    page.goto(search_url, wait_until='networkidle', timeout=60000)

                    # Wait for products to load
                    page.wait_for_selector('.shopee-search-item-result__item', timeout=30000)

                    # Scroll to load more products
                    for _ in range(3):
                        page.mouse.wheel(0, 1000)
                        time.sleep(0.5)

                    time.sleep(2)  # Wait for lazy-loaded content

                    # Get page content
                    html = page.content()
                    products = self._parse_search_results(html, category_id)
                    all_products.extend(products)

                    print(f"Found {len(products)} products on page {page_num + 1}")

                    time.sleep(self.delay)

                except Exception as e:
                    print(f"Error scraping page {page_num + 1}: {e}")
                    # Take screenshot for debugging
                    page.screenshot(path=f"error_page_{page_num}.png")

            browser.close()

        return all_products

    def _parse_search_results(self, html, category_id):
        """Parse search results HTML and extract product data"""
        soup = BeautifulSoup(html, 'html.parser')
        products = []

        # Find all product items
        items = soup.select('.shopee-search-item-result__item')

        for item in items:
            try:
                product_data = self._extract_product_data(item, category_id)
                if product_data:
                    # Save to database
                    product_id = save_product(product_data)
                    save_price(product_id, {
                        'price': product_data['price'],
                        'original_price': product_data.get('original_price'),
                        'discount_percent': product_data.get('discount_percent'),
                        'sold': product_data.get('sold')
                    })
                    products.append(product_data)
            except Exception as e:
                print(f"Error extracting product: {e}")
                continue

        return products

    def _extract_product_data(self, item, category_id):
        """Extract product data from a single item element"""
        # Get product link
        link_elem = item.select_one('a[href*="-i."]')
        if not link_elem:
            return None

        href = link_elem.get('href', '')
        url = f"{self.base_url}{href}" if href.startswith('/') else href

        # Get product name
        name_elem = item.select_one('.Cve6sh, .ie3A\\+n, [data-sqe="name"]')
        name = name_elem.get_text(strip=True) if name_elem else "Unknown"

        # Get price - Shopee uses various class names
        price = 0
        price_elem = item.select_one('.vioxXd, .ZEgDH9, [class*="price"]')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price = self._parse_price(price_text)

        # Get original price (if discounted)
        original_price = None
        orig_price_elem = item.select_one('.TLh\\+ng, [class*="original"]')
        if orig_price_elem:
            orig_text = orig_price_elem.get_text(strip=True)
            original_price = self._parse_price(orig_text)

        # Get discount percentage
        discount_percent = None
        discount_elem = item.select_one('.se8WpE, [class*="discount"]')
        if discount_elem:
            discount_text = discount_elem.get_text(strip=True)
            match = re.search(r'(\d+)%', discount_text)
            if match:
                discount_percent = int(match.group(1))

        # Get sold count
        sold = None
        sold_elem = item.select_one('.OwmBnn, [class*="sold"]')
        if sold_elem:
            sold_text = sold_elem.get_text(strip=True)
            sold = self._parse_sold(sold_text)

        # Get shop name
        shop_name = None
        shop_elem = item.select_one('.zGGwiV, [class*="shop"]')
        if shop_elem:
            shop_name = shop_elem.get_text(strip=True)

        # Get image
        image_url = None
        img_elem = item.select_one('img')
        if img_elem:
            image_url = img_elem.get('src') or img_elem.get('data-src')

        return {
            'category_id': category_id,
            'platform_id': self.platform_id,
            'name': name,
            'url': url,
            'price': price,
            'original_price': original_price,
            'discount_percent': discount_percent,
            'sold': sold,
            'shop_name': shop_name,
            'image_url': image_url,
            'specs': {}
        }

    def _parse_price(self, price_text):
        """Parse price text to float (handles RM, commas, ranges)"""
        if not price_text:
            return 0
        # Remove currency symbol and spaces
        clean = re.sub(r'[RMrm\s]', '', price_text)
        # Handle price ranges (take the lower price)
        if '-' in clean:
            clean = clean.split('-')[0]
        # Remove commas
        clean = clean.replace(',', '')
        try:
            return float(clean)
        except ValueError:
            return 0

    def _parse_sold(self, sold_text):
        """Parse sold count (handles '1.2k sold', '500 sold')"""
        if not sold_text:
            return None
        match = re.search(r'([\d.]+)(k)?', sold_text.lower())
        if match:
            num = float(match.group(1))
            if match.group(2) == 'k':
                num *= 1000
            return int(num)
        return None


if __name__ == "__main__":
    # Test the scraper
    scraper = ShopeeScraper(headless=False)
    products = scraper.search_products("ddr5 ram", category_slug='ram', max_pages=1)

    print(f"\n{'='*50}")
    print(f"Total products scraped: {len(products)}")
    print(f"{'='*50}")

    for p in products[:5]:  # Show first 5
        print(f"\n{p['name'][:50]}...")
        print(f"  Price: RM{p['price']}")
        if p['original_price']:
            print(f"  Original: RM{p['original_price']} ({p['discount_percent']}% off)")
        if p['sold']:
            print(f"  Sold: {p['sold']}")
