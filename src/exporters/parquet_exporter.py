"""
Parquet exporter for DuckDB Analytics Layer.
Exports analytical results to Parquet format for the data lake.
Parquet is the industry standard columnar format for analytical workloads.
"""
import os
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from pathlib import Path
from config import PARQUET_OUTPUT_DIR

logger = logging.getLogger(__name__)


class ParquetExporter:
    """
    Exports analytical query results to Parquet files.
    Each export is timestamped and partitioned by query name.
    """

    def __init__(self, output_dir: str = PARQUET_OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"ParquetExporter initialized — output dir: {self.output_dir}")

    def export(self, df: pd.DataFrame, query_name: str) -> str:
        """
        Export a DataFrame to a Parquet file.
        Returns the path of the exported file.
        """
        if df.empty:
            logger.warning(f"Skipping export for '{query_name}' — DataFrame is empty")
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{query_name}_{timestamp}.parquet"
        filepath = self.output_dir / filename

        try:
            table = pa.Table.from_pandas(df)
            pq.write_table(table, filepath, compression="snappy")
            size_kb = round(os.path.getsize(filepath) / 1024, 2)
            logger.info(f"Exported '{query_name}' to {filepath} ({size_kb} KB)")
            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export '{query_name}': {e}")
            raise

    def export_all(self, results: dict) -> dict:
        """
        Export all analytical results to Parquet files.
        Returns a dictionary of query_name -> file_path.
        """
        exported = {}
        logger.info(f"Exporting {len(results)} query results to Parquet")

        for query_name, df in results.items():
            try:
                filepath = self.export(df, query_name)
                if filepath:
                    exported[query_name] = filepath
            except Exception as e:
                logger.error(f"Export failed for '{query_name}': {e}")
                exported[query_name] = ""

        successful = sum(1 for p in exported.values() if p)
        logger.info(f"Export complete — {successful}/{len(results)} files exported")
        return exported

    def read_parquet(self, filepath: str) -> pd.DataFrame:
        """
        Read a Parquet file back into a DataFrame.
        Useful for loading previously exported results.
        """
        try:
            df = pd.read_parquet(filepath)
            logger.info(f"Read {len(df)} rows from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Failed to read Parquet file '{filepath}': {e}")
            raise

    def list_exports(self) -> list:
        """List all Parquet files in the output directory."""
        files = sorted(self.output_dir.glob("*.parquet"))
        logger.info(f"Found {len(files)} Parquet files in {self.output_dir}")
        return [str(f) for f in files]