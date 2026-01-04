#!/usr/bin/env python
"""
Scrap-RAM: Hardware Price Tracker for Malaysia
"""
import argparse
from scraper.shopee import ShopeeScraper
from database.db import get_all_products


def login(args):
    """Login to Shopee and save session"""
    scraper = ShopeeScraper()
    scraper.login()


def scrape(args):
    """Run the scraper"""
    print(f"Starting scrape for: {args.keyword}")
    print(f"Category: {args.category}")
    print(f"Pages: {args.pages}")
    print("-" * 40)

    scraper = ShopeeScraper(headless=args.headless)
    products = scraper.search_products(
        keyword=args.keyword,
        category_slug=args.category,
        max_pages=args.pages
    )

    print(f"\nDone! Scraped {len(products)} products.")


def list_products(args):
    """List all saved products"""
    products = get_all_products(category_slug=args.category)

    if not products:
        print("No products found.")
        return

    print(f"\n{'='*60}")
    print(f"Found {len(products)} products")
    print(f"{'='*60}\n")

    for p in products:
        print(f"[{p['category_name']}] {p['name'][:50]}...")
        print(f"  Price: RM{p['latest_price'] or 'N/A'}")
        print(f"  Platform: {p['platform_name']}")
        print(f"  URL: {p['url'][:60]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description='Scrap-RAM: Hardware Price Tracker')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Login command
    login_parser = subparsers.add_parser('login', help='Login to Shopee and save session')
    login_parser.set_defaults(func=login)

    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape products')
    scrape_parser.add_argument('keyword', help='Search keyword (e.g., "ddr5 ram")')
    scrape_parser.add_argument('-c', '--category', default='ram', help='Category slug (ram, gpu, ssd, etc.)')
    scrape_parser.add_argument('-p', '--pages', type=int, default=1, help='Number of pages to scrape')
    scrape_parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    scrape_parser.set_defaults(func=scrape)

    # List command
    list_parser = subparsers.add_parser('list', help='List saved products')
    list_parser.add_argument('-c', '--category', default=None, help='Filter by category')
    list_parser.set_defaults(func=list_products)

    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
