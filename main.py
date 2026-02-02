import os
import json
import logging
import asyncio
import yaml
import nodriver as nd
from tqdm import tqdm
from pyvirtualdisplay import Display
from google.cloud import bigquery
from producthunt_scraper.scraper.parser import *
from producthunt_scraper.scraper.base_scraper import *
from producthunt_scraper.core.model import *
from producthunt_scraper.core.bigquery import *
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
    display = Display(visible=0, size=800, 600))
    display.start()

# ----------------------------
# BigQuery Client
# ----------------------------
bq_client = bigquery.Client.from_service_account_json(BIGQUERY_JSON)
bigq = BigQueryClient(table_id=TABLE_ID, logger=logger, bigquery_client=bq_client)


# ----------------------------
# Browser
# ----------------------------
browser = await nd.start()

# ----------------------------
# Main Processing Function
# ----------------------------
async def process_date(index: int, date: datetime):
    products = await scrape_products(browser, date)

# ----------------------------
# Concurrency Control
# ----------------------------
# Note: Proxy rotation is handled automatically by the proxy service on each request
sem = asyncio.Semaphore(CONCURRENCY_LIMIT)

async def process_date_with_semaphore(index: int, date: datetime):
    """Wrapper to apply semaphore for concurrency control."""
    async with sem:
        return await process_date(index, date)


# ----------------------------
# Checkpoint
# ----------------------------
CHECKPOINT_FILE = "checkpoint.json"

def load_checkpoint():
    """Load the last processed date from checkpoint file."""
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r') as f:
                checkpoint_data = json.load(f)
                checkpoint_date = datetime.fromisoformat(checkpoint_data.get('last_date', ''))
                processed_products = checkpoint_data.get('processed_products', 0)
                logger.info(f"Loaded checkpoint: Last processed date = {checkpoint_date.date()}")
                return checkpoint_date, processed_products
        except Exception as e:
            logger.warning(f"Error loading checkpoint: {e}. Starting from beginning.")
    return None

def save_checkpoint(date: datetime, total_products: int, processed_products: int):
    """Save the last processed date to checkpoint file."""
    try:
        checkpoint_data = {
            'last_date': date.isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_products': total_products,
            'processed_products': processed_products,
        }
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        logger.debug(f"Checkpoint saved: {date.date()}")
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")


async def main():

    # Set start time
    start_dt = datetime(START_YEAR, START_MONTH, START_DAY)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Load checkpoint if exists
    checkpoint_date = load_checkpoint()
    if checkpoint_date:
        # Start from the day after the checkpoint
        start_dt = checkpoint_date + timedelta(days=1)

    # Generate list of dates to process
    dates_to_process = []
    current = start_dt
    index = 0

    # Calculate index offset based on start date
    base_start = datetime(START_YEAR, START_MONTH, START_DAY)
    while current <= today:
        # Calculate index: days since base start date
        days_diff = (current - base_start).days
        dates_to_process.append((days_diff, current))
        current += timedelta(days=1)

    if not dates_to_process:
        return

    # Process dates with concurrency control
    # Proxy rotation is handled automatically by the proxy service on each request
    tasks = []
    for index, date in dates_to_process:
        task = asyncio.create_task(
            process_date_with_semaphore(index, date)
        )
        tasks.append(task)

    # Process with progress bar
    completed_count = 0
    total_products = 0

    for completed_task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing dates"):
        try:
            index, date, product_count = await completed_task
            completed_count += 1
            total_products += product_count
        except Exception as e:
            pass


if __name__ == "__main__":
    asyncio.run(main())