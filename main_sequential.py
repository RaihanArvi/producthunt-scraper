"""
ProductHunt scraper entrypoint (sequential version - no concurrency).

Loads config, sets up logging/BigQuery/JSON output/checkpointing, runs the main
async loop (dates → products → BigQuery and optional JSON), and ensures
graceful shutdown (browser.close on exit or interrupt).
"""
import os
import asyncio
import yaml
from tqdm import tqdm
from pyvirtualdisplay import Display
from producthunt_scraper.core.bigquery import *
from producthunt_scraper.core.json_output import JsonOutput
from producthunt_scraper.core.script import *
from datetime import datetime, timedelta


# ----------------------------
# Config File
# ----------------------------
yaml_file = "config.yaml"

BIGQUERY_JSON = None
TABLE_ID = ""
PROXY_IP = None
PROXY_URL = None
CONCURRENCY_LIMIT = 0

DISPLAY_EMULATION = False
JSON_OUTPUT = False

START_YEAR = 0
START_MONTH = 0
START_DAY = 0
try:
    with open(yaml_file, "r") as f:
        config = yaml.safe_load(f)
    BIGQUERY_JSON = config["BIGQUERY_JSON"]
    TABLE_ID = config["BIGQUERY_TABLE_ID"]
    PROXY_IP = config.get("PROXY_IP")
    PROXY_URL = config.get("PROXY_URL")
    CONCURRENCY_LIMIT = config.get("CONCURRENCY_LIMIT")

    DISPLAY_EMULATION = config.get("DISPLAY_EMULATION")
    JSON_OUTPUT = config.get("JSON_OUTPUT", False)

    START_YEAR = config.get("START_YEAR")
    START_MONTH = config.get("START_MONTH")
    START_DAY = config.get("START_DAY")
except FileNotFoundError:
    raise FileNotFoundError(f"YAML config file '{yaml_file}' not found.")
except yaml.YAMLError as e:
    raise ValueError(f"Error parsing YAML file '{yaml_file}': {e}")


# ----------------------------
# Logging and Setup
# ----------------------------
start_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Set up logging
os.makedirs("log", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'log/scraper_{start_str}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ----------------------------
# Virtual Display
# ----------------------------
display = None
if DISPLAY_EMULATION:
    display = Display(visible=False, size=(800, 600))
    display.start()

# ----------------------------
# BigQuery Client
# ----------------------------
bq_client = bigquery.Client.from_service_account_json(BIGQUERY_JSON)
bigq = BigQueryClient(table_id=TABLE_ID, logger=logger, bigquery_client=bq_client)

# ----------------------------
# JSON Output (optional)
# ----------------------------
json_output: JsonOutput | None = None
if JSON_OUTPUT:
    json_output = JsonOutput(filepath="output/products.json", logger=logger)
    logger.info("JSON output enabled: output/products.json")


# ----------------------------
# Checkpoint
# ----------------------------
CHECKPOINT_FILE = "checkpoint.json"

def load_checkpoint():
    """Load the last processed date from checkpoint file. Returns None if missing or invalid."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint_data = json.load(f)
                checkpoint_date = datetime.fromisoformat(checkpoint_data.get('last_date', ''))
                last_index = checkpoint_data.get('last_index', 0)  # Load it
                logger.info(f"Loaded checkpoint: Last processed date = {checkpoint_date.date()}")
                return checkpoint_date, last_index
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}. Starting from beginning.")
    return None

def save_checkpoint(date: datetime, last_index: int):
    """Save the last processed date to checkpoint file (CHECKPOINT_FILE)."""
    try:
        checkpoint_data = {
            'last_date': date.isoformat(),
            'last_index': last_index,  # Save the index
            'last_updated': datetime.now().isoformat(),
        }
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        logger.debug(f"Checkpoint saved: {date.date()}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")


# ----------------------------
# Main Processing Function
# ----------------------------
async def process_one_product(browser, product, date_str: str, global_index: int) -> int:
    """
    Scrape a single product, set date, send to BigQuery (and optional JSON). Returns 1 on success.

    Processes products sequentially (no concurrency). Calls scrape_single_product, then bigq.insert_product(index, product)
    and optionally json_output.add_product. global_index is the row index (0 = first product at start date).
    """
    try:
        full = await scrape_single_product(browser, product)
        full.date = date_str
        bigq.insert_product(date_str, global_index, full)
        if json_output is not None:
            await json_output.add_product(full)
        return 1
    except Exception as e:
        logger.error(f"Error processing product {product.name!r}: {e}")
        return 0


async def process_date(browser, date_index: int, date: datetime, base_index: int) -> tuple[int, datetime, int]:
    """
    Scrape all products for a date; for each product scrape details and send to BigQuery.

    Returns (date_index, date, processed_count). base_index is the global row index for the first product of this date.
    Processes products sequentially (no concurrency).
    """
    date_str = date.strftime("%Y-%m-%d")
    logger.info(f"Processing date {date_str} (date_index={date_index})")
    products = await scrape_products(browser, date)
    if not products:
        logger.info(f"No products for date {date_str}")
        return (date_index, date, 0)
    
    processed = 0
    for i, product in enumerate(products):
        result = await process_one_product(browser, product, date_str, base_index + i)
        processed += result
    
    if processed < len(products):
        failed = len(products) - processed
        logger.warning(f"Date {date_str}: {processed} sent to BQ, {failed} failed")
    else:
        logger.info(f"Date {date_str}: {processed} products sent to BigQuery")
    return (date_index, date, processed)


async def main():
    """
    Main async entry: start browser, load checkpoint, loop over dates from start_dt to today,
    process each date (scrape products → BigQuery/JSON), save checkpoint, rolling today.
    Browser cleanup is handled automatically by nodriver.
    """
    try:
        browser = await nd.start()
        if not browser:
            logger.error("Failed to start browser. Exiting.")
            return
        logger.info("Browser started successfully")
    except Exception as e:
        logger.error(f"Failed to start browser: {e}. Exiting.")
        return

    try:
        base_start = datetime(START_YEAR, START_MONTH, START_DAY)

        start_dt = base_start
        base_index = 0  # Global row index for BigQuery (0 = first product at start date)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Load checkpoint every time script is run
        checkpoint_data = load_checkpoint()
        if checkpoint_data is not None:
            ckpt_date, ckpt_index = checkpoint_data
            start_dt = ckpt_date + timedelta(days=1)
            base_index = ckpt_index  # Resume index count
            logger.info(f"Resuming from {start_dt.date()}")

        if start_dt > today:
            logger.info("Start date is after today; nothing to process.")
            return

        current_date = start_dt
        total_processed = 0

        with tqdm(desc="Processing dates", unit="date") as pbar:
            while current_date <= today:

                idx = (current_date - base_start).days
                _, _, count = await process_date(browser, idx, current_date, base_index)
                base_index += count
                total_processed += count

                # Save checkpoint after each date processed
                save_checkpoint(current_date, base_index)
                logger.info(f"Checkpoint saved: {current_date.date()} ({count} products this date)")

                current_date += timedelta(days=1)
                pbar.update(1)

                # Rolling today: if calendar advanced, extend range
                new_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                if new_today > today:
                    extra_days = (new_today - today).days
                    if extra_days > 0:
                        logger.info(f"Rolling today: {today.date()} -> {new_today.date()} (+{extra_days} day(s))")
                    today = new_today

        logger.info(f"Done. Total products sent to BigQuery: {total_processed}")
    finally:
        logger.info("Processing complete. Browser will be cleaned up automatically.")


def run_main():
    """Run asyncio main(); handles KeyboardInterrupt and logs fatal errors. Re-raises after logging."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user (SIGINT).")
        raise
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    run_main()
