import nodriver as nd
from bs4 import BeautifulSoup

async def get_list_of_product_soups(browser: nd.Browser, link) -> BeautifulSoup:
    try:
        page = await browser.get(link)

        # wait until loaded
        await page.wait_for('[data-test="leaderboard-title"]')

        html = await page.get_content()
        soup = BeautifulSoup(html, "html.parser")
        await page.close()

        return soup
    except Exception as e:
        print(f"Error: get_list_of_product_soups(): {e}. Returning empty BeautifulSoup.")
        for tab in browser.tabs:
            await tab.close()
        return BeautifulSoup("", "html.parser")


async def get_single_product_soup(browser: nd.Browser, link, selector) -> BeautifulSoup:
    """
    :param browser:
    :param link:
    :param selector: need to pass the selector of the product page for wait_for to work.
    :return: BS4 object.
    """
    try:
        page = await browser.get(link, new_tab=True)

        # wait until loaded
        await page.wait_for(selector=selector, timeout=5)

        html = await page.get_content()
        soup = BeautifulSoup(html, "html.parser")

        await page.close()

        return soup
    except Exception as e:
        print(f"Error: get_single_product_soup(): {e}. Returning empty BeautifulSoup.")
        for tab in browser.tabs:
            await tab.close()
        return BeautifulSoup("", "html.parser")