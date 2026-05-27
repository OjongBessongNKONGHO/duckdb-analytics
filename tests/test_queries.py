"""
Unit tests for DuckDB analytical queries.
Uses sample data so no PostgreSQL connection is required.
"""
import pytest
import pandas as pd
import numpy as np
import duckdb
from datetime import datetime, timedelta


# ── Sample Data Fixture ───────────────────────────────────────────────

@pytest.fixture
def sample_df():
    """Generate sample weather data for testing."""
    records = []
    base_time = datetime.now()
    cities = [
        ("Paris", "FR", 15), ("London", "GB", 12),
        ("New York", "US", 18), ("Tokyo", "JP", 22),
        ("Douala", "CM", 28), ("Dubai", "AE", 35)
    ]
    for i in range(48):
        for city, country, base_temp in cities:
            records.append({
                "city": city,
                "country": country,
                "temperature": round(base_temp + np.random.normal(0, 2), 2),
                "feels_like": round(base_temp - 1 + np.random.normal(0, 1), 2),
                "humidity": int(np.clip(np.random.normal(65, 10), 0, 100)),
                "pressure": int(np.clip(np.random.normal(1013, 5), 800, 1100)),
                "weather_description": np.random.choice([
                    "clear sky", "few clouds", "light rain"
                ]),
                "wind_speed": round(abs(np.random.normal(5, 2)), 2),
                "visibility": 10000,
                "recorded_at": base_time - timedelta(hours=i),
            })
    return pd.DataFrame(records)


@pytest.fixture
def duckdb_conn(sample_df):
    """Create an in-memory DuckDB connection loaded with sample data."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE weather_data AS SELECT * FROM sample_df")
    return conn


# ── Query Tests ───────────────────────────────────────────────────────

def test_avg_temperature_per_city(duckdb_conn):
    """Test average temperature query returns one row per city."""
    result = duckdb_conn.execute("""
        SELECT city, ROUND(AVG(temperature), 2) AS avg_temperature
        FROM weather_data
        GROUP BY city
        ORDER BY avg_temperature DESC
    """).df()
    assert len(result) == 6
    assert "city" in result.columns
    assert "avg_temperature" in result.columns


def test_hottest_coldest_ranking(duckdb_conn):
    """Test that ranking query returns correct number of cities."""
    result = duckdb_conn.execute("""
        SELECT city, ROUND(AVG(temperature), 2) AS avg_temperature,
               RANK() OVER (ORDER BY AVG(temperature) DESC) AS hottest_rank
        FROM weather_data
        GROUP BY city
        ORDER BY hottest_rank
    """).df()
    assert len(result) == 6
    assert result["hottest_rank"].min() == 1


def test_humidity_trends(duckdb_conn):
    """Test humidity trends query returns results."""
    result = duckdb_conn.execute("""
        SELECT city, DATE_TRUNC('day', recorded_at) AS date,
               ROUND(AVG(humidity), 2) AS avg_humidity
        FROM weather_data
        GROUP BY city, DATE_TRUNC('day', recorded_at)
        ORDER BY city, date DESC
    """).df()
    assert len(result) > 0
    assert "avg_humidity" in result.columns


def test_wind_speed_distribution(duckdb_conn):
    """Test wind speed categories are correctly assigned."""
    result = duckdb_conn.execute("""
        SELECT city,
               CASE
                   WHEN wind_speed < 1.5  THEN 'Calm'
                   WHEN wind_speed < 5.5  THEN 'Light Breeze'
                   WHEN wind_speed < 10.7 THEN 'Moderate'
                   ELSE 'Strong'
               END AS wind_category,
               COUNT(*) AS occurrences
        FROM weather_data
        GROUP BY city, wind_category
        ORDER BY city, occurrences DESC
    """).df()
    assert len(result) > 0
    assert set(result["wind_category"].unique()).issubset(
        {"Calm", "Light Breeze", "Moderate", "Strong"}
    )


def test_weather_condition_frequency(duckdb_conn):
    """Test weather condition frequency query."""
    result = duckdb_conn.execute("""
        SELECT city, weather_description, COUNT(*) AS occurrences
        FROM weather_data
        GROUP BY city, weather_description
        ORDER BY city, occurrences DESC
    """).df()
    assert len(result) > 0
    assert "weather_description" in result.columns


def test_temperature_humidity_correlation(duckdb_conn):
    """Test correlation values are between -1 and 1."""
    result = duckdb_conn.execute("""
        SELECT city,
               ROUND(CORR(temperature, humidity), 4) AS correlation
        FROM weather_data
        GROUP BY city
    """).df()
    assert len(result) == 6
    assert result["correlation"].between(-1, 1).all()


def test_daily_temperature_range(duckdb_conn):
    """Test daily temperature range is non-negative."""
    result = duckdb_conn.execute("""
        SELECT city,
               DATE_TRUNC('day', recorded_at) AS date,
               ROUND(MAX(temperature) - MIN(temperature), 2) AS temp_range
        FROM weather_data
        GROUP BY city, DATE_TRUNC('day', recorded_at)
    """).df()
    assert len(result) > 0
    assert (result["temp_range"] >= 0).all()


def test_anomaly_detection(duckdb_conn):
    """Test anomaly detection query runs without errors."""
    result = duckdb_conn.execute("""
        WITH city_stats AS (
            SELECT city, AVG(temperature) AS mean_temp,
                   STDDEV(temperature) AS stddev_temp
            FROM weather_data GROUP BY city
        )
        SELECT w.city, w.temperature,
               ROUND(ABS(w.temperature - cs.mean_temp) /
                     NULLIF(cs.stddev_temp, 0), 2) AS z_score
        FROM weather_data w
        JOIN city_stats cs ON w.city = cs.city
        WHERE ABS(w.temperature - cs.mean_temp) > 2 * cs.stddev_temp
        ORDER BY z_score DESC
    """).df()
    assert "z_score" in result.columns


def test_record_count(duckdb_conn):
    """Test total record count matches expected."""
    result = duckdb_conn.execute(
        "SELECT COUNT(*) AS total FROM weather_data"
    ).df()
    assert result["total"][0] == 288


def test_all_cities_present(duckdb_conn):
    """Test all 6 cities are present in the dataset."""
    result = duckdb_conn.execute(
        "SELECT DISTINCT city FROM weather_data ORDER BY city"
    ).df()
    expected_cities = {"Paris", "London", "New York", "Tokyo", "Douala", "Dubai"}
    assert set(result["city"].tolist()) == expected_cities