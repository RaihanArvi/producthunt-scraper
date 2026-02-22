"""
Single JSON file output for scraped products.

Maintains one JSON array file; appends one product (as JSON) and rewrites the file after each add_product.
"""
import json
import logging
import asyncio
from pathlib import Path
from producthunt_scraper.core.model import Product


class JsonOutput:
    """Manages a single JSON file for all scraped products. Appends and saves after every product."""

    def __init__(self, filepath: str, logger: logging.Logger):
        """Initialize with output file path and logger; loads existing file if present."""
        self.filepath = Path(filepath)
        self.logger = logger
        self._lock = asyncio.Lock()
        self._products: list[dict] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Load existing products from file if it exists. On error, start with empty list."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._products = data if isinstance(data, list) else []
            except Exception as e:
                self.logger.warning(f"[JSON] Could not load existing {self.filepath}: {e}. Starting fresh.")
                self._products = []

    def _write_file(self) -> None:
        """Write current _products list to file. Caller must hold _lock."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._products, f, indent=2, ensure_ascii=False)

    async def add_product(self, product: Product) -> None:
        """Append one product (model_dump mode=json) and rewrite the full file immediately."""
        async with self._lock:
            self._products.append(product.model_dump(mode="json"))
            self._write_file()
        self.logger.debug(f"[JSON] Appended product {product.name!r} to {self.filepath}")
