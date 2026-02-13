import nodriver as nd
import random
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

MIN_HTML_LENGTH = 200
MAX_ATTEMPTS = 5

RET_MULTIPLIER = 1
RET_MIN = 1
RET_MAX = 5

class BadHTML(Exception):
    pass

def return_empty_soup(retry_state):
    print(f"Failed after {retry_state.attempt_number} attempts. Returning empty soup.")
    return BeautifulSoup("", "html.parser")

@retry(
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=RET_MULTIPLIER, min=RET_MIN, max=RET_MAX),
    retry=retry_if_exception_type(Exception), # retry on any exception.
    retry_error_callback=return_empty_soup,
)
async def get_list_of_product_soups(browser: nd.Browser, link) -> BeautifulSoup:
    page = None
    try:
        page = await browser.get(link)

        # wait until loaded
        await page.wait_for('[data-test="leaderboard-title"]')
        await page.wait(random.uniform(0.2, 0.7))

        html = await page.get_content()
        if not html or len(html.strip()) < MIN_HTML_LENGTH:
            print(f"Failed. Retrying...")
            raise BadHTML("HTML too small/empty")
        if 'leaderboard-title' not in html:
            print(f"Failed. Retrying...")
            raise BadHTML("Required element missing")

        soup = BeautifulSoup(html, "html.parser")
        return soup

    finally:
        try:
            if page:
                await page.close()
        except Exception:
            pass


@retry(
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=RET_MULTIPLIER, min=RET_MIN, max=RET_MAX),
    retry=retry_if_exception_type(Exception), # retry on any exception.
    retry_error_callback=return_empty_soup,
)
async def get_single_product_soup(browser: nd.Browser, link, selector) -> BeautifulSoup:
    """
    :param browser:
    :param link:
    :param selector: need to pass the selector of the product page for wait_for to work.
    :return: BS4 object.
    """
    page = None
    try:
        page = await browser.get(link, new_tab=True)

        # wait until loaded
        await page.wait_for(selector=selector, timeout=5)
        await page.wait(random.uniform(0.2, 0.7))

        html = await page.get_content()
        if not html or len(html.strip()) < MIN_HTML_LENGTH:
            print(f"Failed. Retrying...")
            raise BadHTML("HTML too small/empty")

        soup = BeautifulSoup(html, "html.parser")
        return soup

    finally:
        try:
            if page:
                await page.close()
        except Exception:
            pass
