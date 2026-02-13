"""
Parse BeautifulSoup into Product Hunt models.

parse_built_with_page — Built With section → list of BuiltWithGroup.
parse_page — product overview → ProductPage.
parse_teams — makers section → list of TeamMember.
parse_team_page — maker about/links → TeamPage.
parse_products — leaderboard sections → list of Product.
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from producthunt_scraper.core.model import *


async def parse_built_with_page(soup: BeautifulSoup) -> List[BuiltWithGroup]:
    """Parse Built With details groups into list of BuiltWithGroup (group_name + products)."""
    groups: List[BuiltWithGroup] = []

    # Iterate through the groups (details tags)
    for details in soup.select("details.group"):
        try:
            summary = details.select_one("summary")
            group_name = summary.get_text(" ", strip=True) if summary else ""

            products: List[BuiltWithProduct] = []

            for item in details.select("div[data-test^='alternative-item-']"):
                try:
                    # Name & Tagline
                    name_tag = item.select_one("span.text-16")
                    name = name_tag.get_text(strip=True) if name_tag else ""

                    tagline_tag = item.select_one("span.text-secondary")
                    tagline = tagline_tag.get_text(strip=True) if tagline_tag else ""

                    # Link
                    a_tag = item.select_one("a[data-grid-span='1']") or item.select_one("a[href]")
                    href = a_tag.get("href", "") if a_tag else ""
                    ph_link = urljoin("https://www.producthunt.com/", href)

                    # Categories
                    categories = []
                    cat_container_class = "flex max-h-[1lh] flex-wrap items-center gap-2 overflow-hidden text-14 z-10 overflow-hidden whitespace-nowrap"

                    cat_container = item.find("div", class_=cat_container_class)

                    if cat_container:
                        for cat in cat_container.find_all("a"):
                            categories.append(cat.get_text(strip=True))

                    # Append to list
                    products.append(
                        BuiltWithProduct(
                            name=name,
                            tagline=tagline,
                            categories=categories,
                            ph_link=ph_link,
                        )
                    )

                except Exception:
                    continue

            groups.append(
                BuiltWithGroup(
                    group_name=group_name,
                    products=products,
                )
            )

        except Exception as e:
            print(f"Error: parse_built_with_page(): {e}")
            continue

    return groups


async def parse_page(soup: BeautifulSoup) -> ProductPage:
    """Parse product overview soup into ProductPage (name, description, categories, website_link)."""
    try:
        product_name = soup.select_one("h1").text.strip()

        description = soup.select_one(
        "#root-container > div.pt-header > div > main > div.flex.flex-col.gap-3 > div.relative.text-16.font-normal.text-gray-700 > div > span").text.strip()

        container_cat = soup.select_one(
        r"#root-container > div.pt-header > div > main > div.flex.flex-col.gap-3 > div.flex.max-h-\[1lh\].flex-wrap.items-center.gap-2.overflow-hidden.text-14")
        categories = [
            a.get_text(strip=True)
            for a in container_cat.select("a[href^='/categories/']")
        ]

        website = soup.select_one(
        r"#root-container > div.pt-header > div > main > "
        r"div.flex.flex-col.gap-3 > "
        r"div.flex.flex-col.gap-4.sm\:flex-row.sm\:items-center > "
        r"div.my-auto.flex.flex-row.items-center.gap-3.sm\:ml-auto > a")["href"]


        product_page = ProductPage(product_name=product_name,
                                   product_description=description,
                                   categories=categories,
                                   website_link=website,

                                   team_members=None,
                                   built_with=None)
        return product_page
    except Exception as e:
        print(f"Error: parse_page(): {e}")
        return ProductPage(product_name="", product_description="", categories=[], website_link="", team_members=None, built_with=None)


async def parse_teams(soup: BeautifulSoup) -> List[TeamMember]:
    """Parse makers section into list of TeamMember (name, role, href)."""
    try:
        team = []

        for section in soup.select("section[data-test^='maker-card']"):
            name_el = section.select_one("a.text-16.font-semibold.text-gray-900")
            role_el = section.select_one("a.text-14.text-gray-700")

            if not name_el or not role_el:
                continue

            team.append(
                TeamMember(
                    name=name_el.get_text(strip=True),
                    role=role_el.get_text(strip=True),
                    href=name_el["href"],

                    team_page=None,
                )
            )

        return team

    except Exception as e:
        print(f"Error: parse_teams(): {e}")
        return []


async def parse_team_page(soup: BeautifulSoup) -> TeamPage:
    """Parse maker about/links into TeamPage (about, links)."""
    try:
        about = soup.select_one("#root-container > div.pt-header > div > main > div > div:nth-child(1) > p").text.strip()

        links = []
        container = soup.select_one(
            "#root-container > div.pt-header > div > main > div > div:nth-child(2) > div"
        )
        if container:
            for a in container.select("a[data-test='user-link']"):
                label = a.get_text(strip=True).lower()
                href = a.get("href")

                if not href:
                    continue

                links.append(
                    Link(
                        type=label,
                        href=href
                    )
                )

        team_page = TeamPage(about=about, links=links)
        return team_page

    except Exception as e:
        print(f"Error: parse_team_page(): {e}")
        return TeamPage(
            about="",
            links=[])


async def parse_products(soup: BeautifulSoup) -> List[Product]:
    """Parse leaderboard post-item sections into list of Product (name, tagline, topics, ph_url; product_page None)."""
    try:
        products = []

        sections = soup.select('section[data-test^="post-item-"]')

        for section in sections:
            name_el = section.select_one('span[data-test^="post-name"] a')
            tagline_el = section.select_one("span.text-secondary")
            topic_els = section.select('a[href^="/topics/"]')
            ph_url = name_el.get('href')

            if not name_el or not tagline_el:
                continue

            products.append(
                Product(
                    name=name_el.get_text(strip=True),
                    tagline=tagline_el.get_text(strip=True),
                    topics=[t.get_text(strip=True) for t in topic_els],
                    ph_url=ph_url,

                    product_page=None,
                )
            )

        return products
    except Exception as e:
        print(f"Error: parse_products(): {e}. Returning empty List[Product].")
        return []
