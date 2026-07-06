"""
Analytical SQL queries for weather data using DuckDB.
All queries run against the weather_data table loaded from PostgreSQL.
"""

import logging
import pandas as pd
from src.connectors.postgres_connector import PostgresConnector

logger = logging.getLogger(__name__)


class WeatherQueries:
    """
    Collection of analytical queries for weather data.
    Uses DuckDB for fast OLAP-style analysis.
    """

    def __init__(self, connector: PostgresConnector):
        self.connector = connector

    def avg_temperature_per_city(self) -> pd.DataFrame:
        """
        Query 1: Average temperature per city over the lookback period.
        Shows which cities are warmest and coldest on average.
        """
        logger.info("Running: avg_temperature_per_city")
        return self.connector.execute_query(
            """
            SELECT
                city,
                country,
                ROUND(AVG(temperature), 2)      AS avg_temperature,
                ROUND(MIN(temperature), 2)      AS min_temperature,
                ROUND(MAX(temperature), 2)      AS max_temperature,
                ROUND(STDDEV(temperature), 2)   AS temperature_stddev,
                COUNT(*)                        AS record_count
            FROM weather_data
            GROUP BY city, country
            ORDER BY avg_temperature DESC
        """
        )

    def hottest_coldest_ranking(self) -> pd.DataFrame:
        """
        Query 2: Rank cities from hottest to coldest.
        Uses window functions for ranking.
        """
        logger.info("Running: hottest_coldest_ranking")
        return self.connector.execute_query(
            """
            SELECT
                city,
                country,
                ROUND(AVG(temperature), 2) AS avg_temperature,
                RANK() OVER (ORDER BY AVG(temperature) DESC) AS hottest_rank,
                RANK() OVER (ORDER BY AVG(temperature) ASC)  AS coldest_rank
            FROM weather_data
            GROUP BY city, country
            ORDER BY hottest_rank
        """
        )

    def humidity_trends(self) -> pd.DataFrame:
        """
        Query 3: Humidity trends over time per city.
        Shows how humidity changes day by day.
        """
        logger.info("Running: humidity_trends")
        return self.connector.execute_query(
            """
            SELECT
                city,
                DATE_TRUNC('day', recorded_at)  AS date,
                ROUND(AVG(humidity), 2)         AS avg_humidity,
                ROUND(MIN(humidity), 2)         AS min_humidity,
                ROUND(MAX(humidity), 2)         AS max_humidity
            FROM weather_data
            GROUP BY city, DATE_TRUNC('day', recorded_at)
            ORDER BY city, date DESC
        """
        )

    def wind_speed_distribution(self) -> pd.DataFrame:
        """
        Query 4: Wind speed distribution per city.
        Categorises wind into calm, breeze, moderate, strong.
        """
        logger.info("Running: wind_speed_distribution")
        return self.connector.execute_query(
            """
            SELECT
                city,
                CASE
                    WHEN wind_speed < 1.5  THEN 'Calm'
                    WHEN wind_speed < 5.5  THEN 'Light Breeze'
                    WHEN wind_speed < 10.7 THEN 'Moderate'
                    ELSE 'Strong'
                END AS wind_category,
                COUNT(*) AS occurrences,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY city), 2) AS percentage
            FROM weather_data
            GROUP BY city, wind_category
            ORDER BY city, occurrences DESC
        """
        )

    def weather_condition_frequency(self) -> pd.DataFrame:
        """
        Query 5: Most common weather conditions per city.
        Shows what weather each city experiences most.
        """
        logger.info("Running: weather_condition_frequency")
        return self.connector.execute_query(
            """
            SELECT
                city,
                weather_description,
                COUNT(*) AS occurrences,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY city), 2) AS percentage
            FROM weather_data
            GROUP BY city, weather_description
            ORDER BY city, occurrences DESC
        """
        )

    def temperature_humidity_correlation(self) -> pd.DataFrame:
        """
        Query 6: Correlation between temperature and humidity per city.
        Shows if higher temperatures mean lower humidity.
        """
        logger.info("Running: temperature_humidity_correlation")
        return self.connector.execute_query(
            """
            SELECT
                city,
                ROUND(CORR(temperature, humidity), 4) AS temp_humidity_correlation,
                ROUND(AVG(temperature), 2)            AS avg_temperature,
                ROUND(AVG(humidity), 2)               AS avg_humidity
            FROM weather_data
            GROUP BY city
            ORDER BY temp_humidity_correlation DESC
        """
        )

    def daily_temperature_range(self) -> pd.DataFrame:
        """
        Query 7: Daily min/max temperature range per city.
        Shows temperature variability throughout each day.
        """
        logger.info("Running: daily_temperature_range")
        return self.connector.execute_query(
            """
            SELECT
                city,
                DATE_TRUNC('day', recorded_at)                      AS date,
                ROUND(MIN(temperature), 2)                          AS min_temp,
                ROUND(MAX(temperature), 2)                          AS max_temp,
                ROUND(MAX(temperature) - MIN(temperature), 2)       AS temp_range,
                ROUND(AVG(temperature), 2)                          AS avg_temp
            FROM weather_data
            GROUP BY city, DATE_TRUNC('day', recorded_at)
            ORDER BY city, date DESC
        """
        )

    def anomaly_detection(self, std_threshold: float = 2.0) -> pd.DataFrame:
        """
        Query 8: Detect temperature anomalies.
        Flags records where temperature is more than std_threshold
        standard deviations from the city mean.
        """
        logger.info(f"Running: anomaly_detection (threshold={std_threshold})")
        return self.connector.execute_query(
            f"""
            WITH city_stats AS (
                SELECT
                    city,
                    AVG(temperature)    AS mean_temp,
                    STDDEV(temperature) AS stddev_temp
                FROM weather_data
                GROUP BY city
            )
            SELECT
                w.city,
                w.temperature,
                w.recorded_at,
                ROUND(cs.mean_temp, 2)   AS city_mean,
                ROUND(cs.stddev_temp, 2) AS city_stddev,
                ROUND(ABS(w.temperature - cs.mean_temp) / NULLIF(cs.stddev_temp, 0), 2) AS z_score,
                CASE
                    WHEN ABS(w.temperature - cs.mean_temp) > {std_threshold} * cs.stddev_temp
                    THEN TRUE ELSE FALSE
                END AS is_anomaly
            FROM weather_data w
            JOIN city_stats cs ON w.city = cs.city
            WHERE ABS(w.temperature - cs.mean_temp) > {std_threshold} * cs.stddev_temp
            ORDER BY z_score DESC
            LIMIT 50
        """
        )

    def pressure_trends(self) -> pd.DataFrame:
        """
        Query 9: Atmospheric pressure trends per city over time.
        Falling pressure indicates incoming storms, rising pressure
        indicates improving weather — useful for forecasting.
        """
        logger.info("Running: pressure_trends")
        return self.connector.execute_query(
            """
            SELECT
                city,
                DATE_TRUNC('day', recorded_at)          AS date,
                ROUND(AVG(pressure), 2)                 AS avg_pressure,
                ROUND(MIN(pressure), 2)                 AS min_pressure,
                ROUND(MAX(pressure), 2)                 AS max_pressure,
                ROUND(MAX(pressure) - MIN(pressure), 2) AS pressure_range
            FROM weather_data
            GROUP BY city, DATE_TRUNC('day', recorded_at)
            ORDER BY city, date DESC
        """
        )

    def feels_like_gap(self) -> pd.DataFrame:
        """
        Query 10: Gap between actual temperature and feels-like per city.
        Large negative gaps mean wind chill makes it feel much colder.
        Large positive gaps mean humidity makes it feel much hotter.
        """
        logger.info("Running: feels_like_gap")
        return self.connector.execute_query(
            """
            SELECT
                city,
                ROUND(AVG(temperature), 2)              AS avg_actual_temp,
                ROUND(AVG(feels_like), 2)               AS avg_feels_like,
                ROUND(AVG(feels_like - temperature), 2) AS avg_gap,
                ROUND(MIN(feels_like - temperature), 2) AS min_gap,
                ROUND(MAX(feels_like - temperature), 2) AS max_gap
            FROM weather_data
            GROUP BY city
            ORDER BY avg_gap DESC
        """
        )

    def visibility_impact(self) -> pd.DataFrame:
        """
        Query 11: Visibility conditions per city and their association
        with weather description. Low visibility (fog, heavy rain) has
        direct operational impact for transport and logistics planning.
        """
        logger.info("Running: visibility_impact")
        return self.connector.execute_query(
            """
            SELECT
                city,
                weather_description,
                ROUND(AVG(visibility), 2)  AS avg_visibility,
                ROUND(MIN(visibility), 2)  AS min_visibility,
                COUNT(*)                   AS occurrences,
                CASE
                    WHEN AVG(visibility) < 1000 THEN 'Severe'
                    WHEN AVG(visibility) < 4000 THEN 'Reduced'
                    ELSE 'Clear'
                END AS visibility_category
            FROM weather_data
            GROUP BY city, weather_description
            HAVING AVG(visibility) < 10000
            ORDER BY avg_visibility ASC
        """
        )

    def hourly_weather_pattern(self) -> pd.DataFrame:
        """
        Query 12: Average conditions by hour of day across all cities.
        Reveals diurnal patterns — temperature typically peaks mid-
        afternoon and troughs before dawn. Distinct from the daily
        queries above, which group by date rather than time of day.
        """
        logger.info("Running: hourly_weather_pattern")
        return self.connector.execute_query(
            """
            SELECT
                EXTRACT(HOUR FROM recorded_at)  AS hour_of_day,
                ROUND(AVG(temperature), 2)      AS avg_temperature,
                ROUND(AVG(humidity), 2)         AS avg_humidity,
                ROUND(AVG(wind_speed), 2)       AS avg_wind_speed,
                COUNT(*)                        AS record_count
            FROM weather_data
            GROUP BY EXTRACT(HOUR FROM recorded_at)
            ORDER BY hour_of_day
        """
        )
    def data_freshness_per_city(self) -> pd.DataFrame:
        """
        Query 13: Time since the most recent reading per city.
        Flags cities whose data pipeline may be stalled or lagging,
        since a stale feed silently skews every aggregate query above.
        """
        logger.info("Running: data_freshness_per_city")
        return self.connector.execute_query(
            """
            SELECT
                city,
                MAX(recorded_at)                                        AS last_recorded_at,
                COUNT(*)                                                AS total_records,
                DATE_DIFF('hour', MAX(recorded_at), CURRENT_TIMESTAMP)  AS hours_since_last_record,
                CASE
                    WHEN DATE_DIFF('hour', MAX(recorded_at), CURRENT_TIMESTAMP) > 24 THEN 'Stale'
                    WHEN DATE_DIFF('hour', MAX(recorded_at), CURRENT_TIMESTAMP) > 6  THEN 'Delayed'
                    ELSE 'Fresh'
                END AS freshness_status
            FROM weather_data
            GROUP BY city
            ORDER BY hours_since_last_record DESC
        """
        )

    def monthly_temperature_trend(self) -> pd.DataFrame:
        """
        Query 14: Month-over-month average temperature per city.
        Uses LAG to compute the change from the previous month, showing
        whether each city is warming or cooling over the collection period.
        """
        logger.info("Running: monthly_temperature_trend")
        return self.connector.execute_query(
            """
            SELECT
                city,
                DATE_TRUNC('month', recorded_at)                                    AS month,
                ROUND(AVG(temperature), 2)                                          AS avg_temperature,
                ROUND(
                    AVG(temperature) - LAG(AVG(temperature)) OVER (
                        PARTITION BY city ORDER BY DATE_TRUNC('month', recorded_at)
                    ), 2
                )                                                                    AS change_from_previous_month
            FROM weather_data
            GROUP BY city, DATE_TRUNC('month', recorded_at)
            ORDER BY city, month
        """
        )

    def run_all(self) -> dict:
        """
        Run all 14 analytical queries and return results as a dictionary.
        """
        logger.info("Running all 14 analytical queries")
        results = {}
        queries = {
            "avg_temperature_per_city": self.avg_temperature_per_city,
            "hottest_coldest_ranking": self.hottest_coldest_ranking,
            "humidity_trends": self.humidity_trends,
            "wind_speed_distribution": self.wind_speed_distribution,
            "weather_condition_frequency": self.weather_condition_frequency,
            "temperature_humidity_correlation": self.temperature_humidity_correlation,
            "daily_temperature_range": self.daily_temperature_range,
            "anomaly_detection": self.anomaly_detection,
            "pressure_trends": self.pressure_trends,
            "feels_like_gap": self.feels_like_gap,
            "visibility_impact": self.visibility_impact,
            "hourly_weather_pattern": self.hourly_weather_pattern,
            "data_freshness_per_city": self.data_freshness_per_city,
            "monthly_temperature_trend": self.monthly_temperature_trend,
        }
        for name, query_fn in queries.items():
            try:
                results[name] = query_fn()
                logger.info(f"Query '{name}' completed — {len(results[name])} rows")
            except Exception as e:
                logger.error(f"Query '{name}' failed: {e}")
                results[name] = pd.DataFrame()
        return results
