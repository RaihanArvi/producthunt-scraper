"""
BigQuery client for inserting scraped Product rows as JSON.

Uses google.cloud.bigquery; one row per product via insert_rows_json.
Each row has two columns: index (INT64) and product (JSON).
"""
import json
import logging
from xmlrpc.client import DateTime
from datetime import datetime

from google.cloud import bigquery
from producthunt_scraper.core.model import Product


class BigQueryClient:
    """Client to insert Product rows into a BigQuery table as JSON."""

    def __init__(self, table_id: str, logger: logging.Logger, bigquery_client: bigquery.Client):
        """Initialize with table_id, logger, and google.cloud.bigquery.Client."""
        self.table_id = table_id
        self.logger = logger
        self.bq_client = bigquery_client

    def insert_product(self, date: str, index: int, product: Product, ) -> None:
        """
        Insert one row: index (INT64) and product (JSON). Product must have date set (YYYY-MM-DD).
        
        Table must have exactly two columns:
        - index: INT64
        - product: JSON
        
        Use the DDL in bigquery_create_table.txt to create the table.
        """
        try:
            product_json = json.dumps(product.model_dump(mode="json"))
            row = {"date": date, "index": index, "product": product_json}
            errors = self.bq_client.insert_rows_json(self.table_id, [row])
            if errors:
                self.logger.error(f"[BQ] Insert failed for product {product.name!r}: {errors}")
            else:
                self.logger.debug(f"[BQ] Inserted product {product.name!r} date={product.date}")
        except Exception as e:
            self.logger.error(f"[BQ EXCEPTION] product={getattr(product, 'name', '?')} {e}", exc_info=True)