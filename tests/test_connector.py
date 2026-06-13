"""
Unit tests for PostgresConnector incremental loading methods.
Uses an in-memory DuckDB connection — no PostgreSQL required.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.connectors.postgres_connector import PostgresConnector


# ── Sample Data Fixtures ───────────────────────────────────────────────
@pytest.fixture
def sample_df():
    """Generate a small sample weather DataFrame for testing."""
    base_time = datetime(2026, 6, 1, 12, 0, 0)
    records = []
    for i in range(5):
        records.append({
            "city": "Paris",
            "country": "FR",
            "temperature": 15.0 + i,
            "feels_like": 14.0 + i,
            "humidity": 60,
            "pressure": 1013,
            "weather_description": "clear sky",
            "wind_speed": 3.5,
            "visibility": 10000,
            "recorded_at": base_time - timedelta(hours=i),
        })
    return pd.DataFrame(records)


@pytest.fixture
def connector(tmp_path):
    """Create a PostgresConnector backed by a temporary DuckDB file."""
    db_path = str(tmp_path / "test_weather.duckdb")
    import duckdb
    conn_wrapper = PostgresConnector.__new__(PostgresConnector)
    conn_wrapper.max_retries = 3
    conn_wrapper.retry_delay = 0
    conn_wrapper.conn = duckdb.connect(db_path)
    yield conn_wrapper
    conn_wrapper.close()


# ── get_last_loaded_timestamp ──────────────────────────────────────────
def test_get_last_loaded_timestamp_no_table(connector):
    """Returns None when the table does not exist yet."""
    assert connector.get_last_loaded_timestamp("weather_data") is None


def test_get_last_loaded_timestamp_with_data(connector, sample_df):
    """Returns the max recorded_at once data is loaded."""
    connector.load_from_dataframe(sample_df)
    last_loaded = connector.get_last_loaded_timestamp("weather_data")
    assert last_loaded is not None
    assert pd.Timestamp(last_loaded) == sample_df["recorded_at"].max()


# ── append_to_table ─────────────────────────────────────────────────────
def test_append_to_table_creates_table_if_missing(connector, sample_df):
    """append_to_table creates the table on first call."""
    connector.append_to_table(sample_df)
    result = connector.execute_query("SELECT COUNT(*) AS n FROM weather_data")
    assert result["n"].iloc[0] == len(sample_df)


def test_append_to_table_appends_without_dropping(connector, sample_df):
    """Calling append_to_table twice accumulates rows rather than replacing them."""
    connector.append_to_table(sample_df)

    new_rows = pd.DataFrame([{
        "city": "Paris",
        "country": "FR",
        "temperature": 20.0,
        "feels_like": 19.0,
        "humidity": 55,
        "pressure": 1015,
        "weather_description": "few clouds",
        "wind_speed": 4.0,
        "visibility": 10000,
        "recorded_at": sample_df["recorded_at"].max() + timedelta(hours=1),
    }])
    connector.append_to_table(new_rows)

    result = connector.execute_query("SELECT COUNT(*) AS n FROM weather_data")
    assert result["n"].iloc[0] == len(sample_df) + 1


def test_append_to_table_noop_on_empty_dataframe(connector, sample_df):
    """An empty DataFrame is a no-op and does not error."""
    connector.append_to_table(sample_df)
    empty_df = sample_df.iloc[0:0]
    connector.append_to_table(empty_df)
    result = connector.execute_query("SELECT COUNT(*) AS n FROM weather_data")
    assert result["n"].iloc[0] == len(sample_df)


# ── Incremental flow integration ────────────────────────────────────────
def test_incremental_flow_preserves_existing_rows(connector, sample_df):
    """
    Simulates an incremental load: existing rows in DuckDB are preserved,
    and newly appended rows extend the table without a full reload.
    """
    connector.append_to_table(sample_df)
    initial_count = connector.execute_query(
        "SELECT COUNT(*) AS n FROM weather_data"
    )["n"].iloc[0]
    assert initial_count == len(sample_df)

    last_loaded = connector.get_last_loaded_timestamp("weather_data")

    new_row = pd.DataFrame([{
        "city": "London",
        "country": "GB",
        "temperature": 12.0,
        "feels_like": 11.0,
        "humidity": 70,
        "pressure": 1010,
        "weather_description": "overcast clouds",
        "wind_speed": 5.0,
        "visibility": 9000,
        "recorded_at": pd.Timestamp(last_loaded) + timedelta(hours=1),
    }])
    connector.append_to_table(new_row)

    final_count = connector.execute_query(
        "SELECT COUNT(*) AS n FROM weather_data"
    )["n"].iloc[0]
    assert final_count == initial_count + 1

    new_last_loaded = connector.get_last_loaded_timestamp("weather_data")
    assert pd.Timestamp(new_last_loaded) > pd.Timestamp(last_loaded)