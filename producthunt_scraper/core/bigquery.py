import json
import logging
from google.cloud import bigquery
from typing import List
from producthunt_scraper.model.models import ProductInfo


class BigQueryClient:
    def __init__(self, table_id: str, logger: logging.Logger, bigquery_client: bigquery.Client):
        self.table_id = table_id
        self.logger = logger
        self.bq_client = bigquery_client

    def insert_row(self, index: int, date: str, products: List[ProductInfo]):
        try:
            if not products:
                self.logger.info(f"[BQ] No products to insert for date={date}")
                return

            print(f"[BQ] Inserting idx={index} date={date} with {len(products)} products")

            # Prepare a list of flattened rows
            rows_to_insert = []
            for p in products:
                # model_dump(mode="json") handles the Optional ProductDetail
                # and the List[str] for topics automatically.
                p_dict = p.model_dump(mode="json")

                row = {
                    "index": index,
                    "date": date,
                    **p_dict  # Flattens product_name, url, topics, etc. into the top level
                }
                rows_to_insert.append(row)

            errors = self.bq_client.insert_rows_json(self.table_id, rows_to_insert)

            if errors:
                self.logger.error(f"[BQ ERROR] idx={index} insert failed: {errors}")
                raise Exception(f"Failed to insert row: {errors}")
            else:
                print(f"[BQ] Successfully inserted {len(rows_to_insert)} products")

        except Exception as e:
            self.logger.error(f"[BQ EXCEPTION] idx={index} {e}", exc_info=True)

        except Exception as e:
            print(f"[BQ EXCEPTION] idx={index} Error: {e}")
            self.logger.error(f"[BQ EXCEPTION] idx={index} {e}", exc_info=True)