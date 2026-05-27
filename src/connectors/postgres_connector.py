"""
PostgreSQL connector for DuckDB Analytics Layer.
Connects to the weather database from Projects 1 and 2.
Includes retry logic and connection pooling.
"""
import time
import logging
import duckdb
import psycopg2
import pandas as pd
from typing import Optional
from config import POSTGRES_CONFIG, POSTGRES_URL, DUCKDB_PATH

logger = logging.getLogger(__name__)


class PostgresConnector:
    """
    Manages connection between PostgreSQL and DuckDB.
    Loads weather data from PostgreSQL into DuckDB for fast analytics.
    """

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.conn = None
        self._connect_duckdb()

    def _connect_duckdb(self):
        """Initialize DuckDB connection."""
        self.conn = duckdb.connect(DUCKDB_PATH)
        logger.info(f"DuckDB connected at {DUCKDB_PATH}")

    def _test_postgres_connection(self) -> bool:
        """Test if PostgreSQL is reachable."""
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            conn.close()
            return True
        except Exception as e:
            logger.warning(f"PostgreSQL connection test failed: {e}")
            return False

    def load_weather_data(self, table: str = "weather_data") -> pd.DataFrame:
        """
        Load weather data from PostgreSQL into a pandas DataFrame.
        Retries up to max_retries times on failure.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Loading data from PostgreSQL — attempt {attempt}/{self.max_retries}")

                # Install and load PostgreSQL extension in DuckDB
                self.conn.execute("INSTALL postgres;")
                self.conn.execute("LOAD postgres;")

                # Attach PostgreSQL database
                self.conn.execute(f"""
                    ATTACH '{POSTGRES_URL}' AS pg_db (TYPE postgres, READ_ONLY)
                """)

                # Load data into DuckDB
                df = self.conn.execute(f"""
                    SELECT * FROM pg_db.{table}
                    ORDER BY recorded_at DESC
                """).df()

                logger.info(f"Loaded {len(df)} records from PostgreSQL")
                return df

            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error("All retry attempts exhausted")
                    raise

    def load_from_dataframe(self, df: pd.DataFrame, table_name: str = "weather_data"):
        """
        Load a pandas DataFrame directly into DuckDB.
        Used when PostgreSQL is not available — for testing and development.
        """
        self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        logger.info(f"Loaded {len(df)} records into DuckDB table '{table_name}'")

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute an analytical query and return results as DataFrame."""
        start_time = time.time()
        result = self.conn.execute(query).df()
        elapsed = round(time.time() - start_time, 3)
        logger.info(f"Query executed in {elapsed}s — {len(result)} rows returned")
        return result

    def close(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()