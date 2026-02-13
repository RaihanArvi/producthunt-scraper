"""
Scraping orchestration: daily leaderboard list and full product detail.

scrape_products(browser, date) → list of Product (leaderboard only).
scrape_single_product(browser, product) → Product with product_page filled (overview, makers, built-with).
"""
import nodriver as nd
from typing import List
from urllib.parse import urljoin
from datetime import datetime
from producthunt_scraper.core.model import Product
from producthunt_scraper.scraper.base_scraper import get_list_of_product_soups, get_single_product_soup
from producthunt_scraper.scraper.parser import parse_page, parse_teams, parse_team_page, parse_built_with_page, parse_products


async def scrape_products(browser: nd.Browser, date: datetime) -> List[Product]:
    """Fetch daily leaderboard page for date; parse and return list of Product (product_page None)."""
    main_url = "https://www.producthunt.com/leaderboard/daily/"
    date_href = date.strftime("%Y/%m/%d")
    page_url = urljoin(main_url, date_href)

    print(f"Scraping {page_url} | Date: {date.strftime('%Y-%m-%d')}")

    soup = await get_list_of_product_soups(browser, page_url)
    products = await parse_products(soup)
    print(products)
    return products


async def scrape_single_product(browser: nd.Browser, product: Product) -> Product:
    """Fetch product overview, makers, and built-with pages; attach product_page to product and return it."""
    product_href = product.ph_url

    main_url = "https://www.producthunt.com/"
    base_url = "https://www.producthunt.com/products/"
    built_with_href = "built-with"
    makers_href = "makers"

    product_url = urljoin(base_url, product_href) + "/"

    # Product Page (Overview)
    pp_selector = 'main h2'
    pp_soup = await get_single_product_soup(browser, product_url, pp_selector)

    product_page = await parse_page(pp_soup)

    # Team Page
    tp_url = urljoin(product_url, makers_href)
    tp_selector = 'main h2'
    tp_soup = await get_single_product_soup(browser, tp_url, tp_selector)

    print(f"Opening {tp_url}...")

    teams = await parse_teams(tp_soup)

    # Loop over Team Members' Page + Update TeamPage
    maker_links = [maker.href for maker in teams]
    maker_pages_parsed = []
    for maker_link in maker_links:
        ml_url = urljoin(main_url, maker_link)
        ml_selector = 'main h2'
        ml_soup = await get_single_product_soup(browser, ml_url, ml_selector)

        print(f"Opening {ml_url}...")

        parsed_page = await parse_team_page(ml_soup)
        maker_pages_parsed.append(parsed_page)

    # Built With
    bw_url = urljoin(product_url, built_with_href)
    bw_selector = 'main h2'
    bw_soup = await get_single_product_soup(browser, bw_url, bw_selector)

    print(f"Opening {bw_url}...")

    # parse
    built_with = await parse_built_with_page(bw_soup)

    # Update each Maker with their respective TeamPage
    for team, team_page in zip(teams, maker_pages_parsed):
        team.team_page = team_page

    # Update ProductPage
    product_page.team_members = teams
    product_page.website_link = product_url
    product_page.built_with = built_with

    # Combine into a Product Object
    product.product_page = product_page

    return product