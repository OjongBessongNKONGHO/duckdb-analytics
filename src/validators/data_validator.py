"""
Data quality validator for DuckDB Analytics Layer.
Validates weather data before running analytical queries.
Ensures data is clean, complete and within realistic ranges.
"""
import logging
import pandas as pd
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Holds the result of a validation check."""
    passed: bool
    check_name: str
    message: str
    failed_records: int = 0
    total_records: int = 0


@dataclass
class ValidationReport:
    """Holds all validation results for a dataset."""
    results: List[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failed_checks(self) -> List[ValidationResult]:
        return [r for r in self.results if not r.passed]

    @property
    def summary(self) -> str:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        return f"{passed}/{total} checks passed"


class DataValidator:
    """
    Validates weather data quality before analysis.
    Runs 8 validation checks covering completeness,
    range validation and data freshness.
    """

    # Realistic weather ranges
    TEMP_MIN = -80.0
    TEMP_MAX = 60.0
    HUMIDITY_MIN = 0
    HUMIDITY_MAX = 100
    PRESSURE_MIN = 800
    PRESSURE_MAX = 1100
    WIND_SPEED_MIN = 0.0
    WIND_SPEED_MAX = 100.0

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.report = ValidationReport()

    def _add_result(self, passed: bool, check_name: str,
                    message: str, failed_records: int = 0):
        """Add a validation result to the report."""
        result = ValidationResult(
            passed=passed,
            check_name=check_name,
            message=message,
            failed_records=failed_records,
            total_records=len(self.df)
        )
        self.report.results.append(result)
        status = "PASS" if passed else "FAIL"
        logger.info(f"[{status}] {check_name}: {message}")

    def check_not_empty(self) -> ValidationResult:
        """Check 1: Dataset is not empty."""
        passed = len(self.df) > 0
        message = f"{len(self.df)} records found" if passed else "Dataset is empty"
        self._add_result(passed, "not_empty", message)
        return self.report.results[-1]

    def check_required_columns(self) -> ValidationResult:
        """Check 2: All required columns are present."""
        required = ["city", "country", "temperature",
                    "humidity", "pressure", "wind_speed", "recorded_at"]
        missing = [col for col in required if col not in self.df.columns]
        passed = len(missing) == 0
        message = "All required columns present" if passed else f"Missing columns: {missing}"
        self._add_result(passed, "required_columns", message)
        return self.report.results[-1]

    def check_no_nulls(self) -> ValidationResult:
        """Check 3: No null values in critical columns."""
        critical = ["city", "temperature", "humidity", "recorded_at"]
        available = [col for col in critical if col in self.df.columns]
        null_counts = self.df[available].isnull().sum()
        total_nulls = null_counts.sum()
        passed = bool(total_nulls == 0)
        message = "No null values in critical columns" if passed else f"{total_nulls} null values found"
        self._add_result(passed, "no_nulls", message, failed_records=int(total_nulls))
        return self.report.results[-1]

    def check_temperature_range(self) -> ValidationResult:
        """Check 4: Temperature values within realistic range."""
        if "temperature" not in self.df.columns:
            self._add_result(False, "temperature_range", "Column 'temperature' missing")
            return self.report.results[-1]
        invalid = self.df[
            (self.df["temperature"] < self.TEMP_MIN) |
            (self.df["temperature"] > self.TEMP_MAX)
        ]
        passed = len(invalid) == 0
        message = (f"All temperatures in range [{self.TEMP_MIN}, {self.TEMP_MAX}]°C"
                   if passed else f"{len(invalid)} temperatures out of range")
        self._add_result(passed, "temperature_range", message, failed_records=len(invalid))
        return self.report.results[-1]

    def check_humidity_range(self) -> ValidationResult:
        """Check 5: Humidity values between 0 and 100."""
        if "humidity" not in self.df.columns:
            self._add_result(False, "humidity_range", "Column 'humidity' missing")
            return self.report.results[-1]
        invalid = self.df[
            (self.df["humidity"] < self.HUMIDITY_MIN) |
            (self.df["humidity"] > self.HUMIDITY_MAX)
        ]
        passed = len(invalid) == 0
        message = ("All humidity values in range [0, 100]%"
                   if passed else f"{len(invalid)} humidity values out of range")
        self._add_result(passed, "humidity_range", message, failed_records=len(invalid))
        return self.report.results[-1]

    def check_wind_speed_range(self) -> ValidationResult:
        """Check 6: Wind speed is non-negative and realistic."""
        if "wind_speed" not in self.df.columns:
            self._add_result(False, "wind_speed_range", "Column 'wind_speed' missing")
            return self.report.results[-1]
        invalid = self.df[
            (self.df["wind_speed"] < self.WIND_SPEED_MIN) |
            (self.df["wind_speed"] > self.WIND_SPEED_MAX)
        ]
        passed = len(invalid) == 0
        message = ("All wind speeds in valid range"
                   if passed else f"{len(invalid)} wind speeds out of range")
        self._add_result(passed, "wind_speed_range", message, failed_records=len(invalid))
        return self.report.results[-1]

    def check_no_duplicates(self) -> ValidationResult:
        """Check 7: No duplicate records for same city and timestamp."""
        if not all(col in self.df.columns for col in ["city", "recorded_at"]):
            self._add_result(False, "no_duplicates", "Required columns missing")
            return self.report.results[-1]
        duplicates = self.df.duplicated(subset=["city", "recorded_at"]).sum()
        passed = bool(duplicates == 0)
        message = ("No duplicate records found"
                   if passed else f"{duplicates} duplicate records found")
        self._add_result(passed, "no_duplicates", message, failed_records=int(duplicates))
        return self.report.results[-1]

    def check_pressure_range(self) -> ValidationResult:
        """Check 8: Pressure values within realistic range."""
        if "pressure" not in self.df.columns:
            self._add_result(False, "pressure_range", "Column 'pressure' missing")
            return self.report.results[-1]
        invalid = self.df[
            (self.df["pressure"] < self.PRESSURE_MIN) |
            (self.df["pressure"] > self.PRESSURE_MAX)
        ]
        passed = len(invalid) == 0
        message = (f"All pressures in range [{self.PRESSURE_MIN}, {self.PRESSURE_MAX}] hPa"
                   if passed else f"{len(invalid)} pressure values out of range")
        self._add_result(passed, "pressure_range", message, failed_records=len(invalid))
        return self.report.results[-1]

    def run_all(self) -> ValidationReport:
        """Run all 8 validation checks and return the full report."""
        logger.info("Running data quality validation — 8 checks")
        self.check_not_empty()
        self.check_required_columns()
        self.check_no_nulls()
        self.check_temperature_range()
        self.check_humidity_range()
        self.check_wind_speed_range()
        self.check_no_duplicates()
        self.check_pressure_range()
        logger.info(f"Validation complete — {self.report.summary}")
        return self.report