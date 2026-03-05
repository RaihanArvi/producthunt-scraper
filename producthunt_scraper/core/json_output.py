"""
Memory-efficient JSON output for scraped products.

Uses JSONL (JSON Lines) format: one JSON object per line, append-only.
This avoids loading the entire file into memory and allows efficient appending.
"""
import json
import logging
import asyncio
from pathlib import Path
from producthunt_scraper.core.model import Product


class JsonOutput:
    """
    Manages a JSONL file for scraped products. Appends one product per line.
    Memory-efficient: does not load existing products into memory.
    """

    def __init__(self, filepath: str, logger: logging.Logger):
        """
        Initialize with output file path and logger.
        Creates file if it doesn't exist; does not load existing data into memory.
        """
        self.filepath = Path(filepath)
        self.logger = logger
        self._lock = asyncio.Lock()
        self._file_handle = None
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the output directory exists and file is ready for appending."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        # Just ensure file exists, don't load it
        if not self.filepath.exists():
            self.filepath.touch()
            self.logger.info(f"[JSON] Created new JSONL file: {self.filepath}")
        else:
            # Count existing lines to log progress (optional, doesn't load data)
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                self.logger.info(f"[JSON] Appending to existing JSONL file: {self.filepath} ({line_count} products)")
            except Exception as e:
                self.logger.warning(f"[JSON] Could not read existing file {self.filepath}: {e}")

    async def add_product(self, product: Product) -> None:
        """
        Append one product as a JSON line (JSONL format).
        Memory-efficient: appends directly to file without loading existing data.
        """
        async with self._lock:
            product_dict = product.model_dump(mode="json")
            # Append mode: write one JSON object per line
            with open(self.filepath, "a", encoding="utf-8") as f:
                json.dump(product_dict, f, ensure_ascii=False)
                f.write("\n")  # JSONL: one JSON object per line
        self.logger.debug(f"[JSON] Appended product {product.name!r} to {self.filepath}")
