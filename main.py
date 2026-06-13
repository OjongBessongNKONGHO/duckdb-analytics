"""
DuckDB Weather Analytics — Entry Point
CLI interface for running analytical queries on weather data.
"""
import logging
import click
import pandas as pd
from datetime import datetime
from config import LOG_LEVEL, LOG_FILE, TRACKED_CITIES
from src.connectors.postgres_connector import PostgresConnector
from src.queries.weather_queries import WeatherQueries
from src.exporters.parquet_exporter import ParquetExporter
from src.validators.data_validator import DataValidator


# ── Logging Setup ─────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE),
    ]
)
logger = logging.getLogger(__name__)


def get_sample_data() -> pd.DataFrame:
    """
    Generate sample weather data for testing when PostgreSQL is unavailable.
    Mirrors the schema from Projects 1 and 2.
    """
    import numpy as np
    from datetime import timedelta

    records = []
    base_time = datetime.now()
    city_temps = {
        "Paris": 15, "London": 12, "New York": 18,
        "Tokyo": 22, "Douala": 28, "Berlin": 13,
        "Lagos": 30, "Sydney": 20, "Nairobi": 24,
        "São Paulo": 25, "Dubai": 35, "Mumbai": 32
    }
    city_countries = {
        "Paris": "FR", "London": "GB", "New York": "US",
        "Tokyo": "JP", "Douala": "CM", "Berlin": "DE",
        "Lagos": "NG", "Sydney": "AU", "Nairobi": "KE",
        "São Paulo": "BR", "Dubai": "AE", "Mumbai": "IN"
    }

    for i in range(240):
        for city, base_temp in city_temps.items():
            records.append({
                "city": city,
                "country": city_countries[city],
                "temperature": round(base_temp + np.random.normal(0, 3), 2),
                "feels_like": round(base_temp + np.random.normal(-1, 2), 2),
                "humidity": int(np.clip(np.random.normal(65, 15), 0, 100)),
                "pressure": int(np.clip(np.random.normal(1013, 10), 800, 1100)),
                "weather_description": np.random.choice([
                    "clear sky", "few clouds", "light rain",
                    "overcast clouds", "moderate rain"
                ]),
                "wind_speed": round(abs(np.random.normal(5, 3)), 2),
                "visibility": int(np.random.normal(10000, 2000)),
                "recorded_at": base_time - pd.Timedelta(hours=i),
            })

    return pd.DataFrame(records)


@click.group()
def cli():
    """DuckDB Weather Analytics — analytical layer for weather pipeline data."""
    pass


@cli.command()
@click.option("--use-sample", is_flag=True, default=False,
              help="Use sample data instead of PostgreSQL")
@click.option("--export", is_flag=True, default=False,
              help="Export results to Parquet files")
@click.option("--incremental", is_flag=True, default=False,
              help="Only load new records since the last run (append instead of full reload)")
def analyse(use_sample, export, incremental):
    """Run all 10 analytical queries on weather data."""
    logger.info("Starting weather analytics")

    with PostgresConnector() as connector:
        if use_sample:
            logger.info("Using sample data")
            df = get_sample_data()
            connector.load_from_dataframe(df)
        elif incremental:
            logger.info("Loading data incrementally from PostgreSQL")
            new_df = connector.load_incremental()
            connector.append_to_table(new_df)
            df = connector.execute_query("SELECT * FROM weather_data ORDER BY recorded_at DESC")
        else:
            logger.info("Loading data from PostgreSQL")
            df = connector.load_weather_data()
            connector.load_from_dataframe(df)

        # Validate data quality
        validator = DataValidator(df)
        report = validator.run_all()
        click.echo(f"\nData Quality: {report.summary}")

        if not report.passed:
            click.echo("WARNING: Some validation checks failed:")
            for check in report.failed_checks:
                click.echo(f"  FAIL {check.check_name}: {check.message}")

        # Run queries
        queries = WeatherQueries(connector)
        results = queries.run_all()

        # Display results
        for name, df_result in results.items():
            click.echo(f"\n{'='*60}")
            click.echo(f"Query: {name}")
            click.echo(f"{'='*60}")
            if not df_result.empty:
                click.echo(df_result.to_string(index=False))
            else:
                click.echo("No results returned.")

        # Export to Parquet
        if export:
            exporter = ParquetExporter()
            exported = exporter.export_all(results)
            click.echo(f"\nExported {len(exported)} files to Parquet.")

    logger.info("Analytics complete")


@cli.command()
@click.option("--use-sample", is_flag=True, default=False,
              help="Use sample data instead of PostgreSQL")
def validate(use_sample):
    """Run data quality validation checks."""
    logger.info("Starting data validation")

    with PostgresConnector() as connector:
        if use_sample:
            df = get_sample_data()
        else:
            df = connector.load_weather_data()

        validator = DataValidator(df)
        report = validator.run_all()

        click.echo(f"\nValidation Report — {report.summary}")
        for result in report.results:
            status = "PASS" if result.passed else "FAIL"
            click.echo(f"  [{status}] {result.check_name}: {result.message}")

    logger.info("Validation complete")


@cli.command()
def list_exports():
    """List all exported Parquet files."""
    exporter = ParquetExporter()
    files = exporter.list_exports()
    if files:
        click.echo(f"\nFound {len(files)} Parquet files:")
        for f in files:
            click.echo(f"  {f}")
    else:
        click.echo("No Parquet files found.")


if __name__ == "__main__":
    cli()