# ProductHunt Scraper

Scrapes Product Hunt daily leaderboard data backwards from a given start date until today. For each date, fetches the product list, then for each product fetches full details (overview, makers, built-with) and sends results to BigQuery and optionally to a local JSON file.

## Features

- **Date range**: Scrapes from `START_YEAR/MONTH/DAY` (config) up to today.
- **Checkpointing**: Saves progress per date in `checkpoint.json`; resume from last processed date on restart.
- **Rolling today**: If the script runs across midnight, the end date extends to the new day.
- **Concurrency**: Configurable semaphore limits concurrent product scrapes per date.
- **Outputs**: BigQuery (required); optional single JSON file (`JSON_OUTPUT = True`).
- **Graceful shutdown**: Browser is closed on normal exit, Ctrl+C, or unhandled exception.

## Setup

1. Copy `config.yaml.example` to `config.yaml` and fill in values.
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure `BIGQUERY_JSON` points to a valid Google Cloud service account key and `BIGQUERY_TABLE_ID` is set.

## Config (`config.yaml`)

| Key | Description |
|-----|-------------|
| `BIGQUERY_JSON` | Path to GCP service account JSON key file. |
| `BIGQUERY_TABLE_ID` | BigQuery table ID (e.g. `project.dataset.table`). |
| `PROXY_IP` | (Optional) Proxy IP. |
| `PROXY_URL` | (Optional) Proxy URL. |
| `CONCURRENCY_LIMIT` | Max concurrent product scrapes per date (default 1 if 0 or missing). |
| `START_YEAR`, `START_MONTH`, `START_DAY` | Start date for scraping (e.g. 2013, 11, 21). |
| `DISPLAY_EMULATION` | If true, run browser in virtual display. |
| `JSON_OUTPUT` | If true, append each product to `output/products.json`. |

## Usage

```bash
python main.py
```

Logs go to `log/scraper_<timestamp>.log` and stdout. Checkpoint file: `checkpoint.json`.

## Project layout

- **`main.py`** — Config load, logging, checkpoint helpers, main async loop (dates → products → BigQuery/JSON), graceful shutdown.
- **`producthunt_scraper/core/model.py`** — Pydantic models: `Link`, `TeamPage`, `TeamMember`, `BuiltWithProduct`, `BuiltWithGroup`, `ProductPage`, `Product`.
- **`producthunt_scraper/core/script.py`** — Scraping orchestration: `scrape_products(date)`, `scrape_single_product(product)`.
- **`producthunt_scraper/core/bigquery.py`** — `BigQueryClient`: insert one product as JSON per call.
- **`producthunt_scraper/core/json_output.py`** — `JsonOutput`: single JSON file, append and save after each product.
- **`producthunt_scraper/scraper/base_scraper.py`** — Browser helpers: `get_list_of_product_soups`, `get_single_product_soup`.
- **`producthunt_scraper/scraper/parser.py`** — Parsers: `parse_products`, `parse_page`, `parse_teams`, `parse_team_page`, `parse_built_with_page`.

## Scraping Process

- `process_date()`: This is the main function wrappers that process all products in a single date.
- `scrape_products()`: Scrapes all products from a single date leaderboard page. Results in a list of `Product` objects.
- `scrape_single_product()`: Scrapes a single product page and sends it to BigQuery.

Leaderboard Page -> `script.scrape_products()` -> `base_scraper.get_list_of_product_soups()` -> `parser.parse_products()` -> Products.

Product Page -> `script.scrape_single_product()` -> `base_scraper.get_single_product_soup()` -> `parser.parse_page()` -> Product.
