"""
Unit tests for the DataValidator class.
Tests all 8 validation checks with valid and invalid data.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.validators.data_validator import DataValidator, ValidationReport


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def valid_df():
    """Generate a clean valid weather DataFrame."""
    records = []
    base_time = datetime.now()
    cities = [
        ("Paris", "FR", 15.0),
        ("London", "GB", 12.0),
        ("Tokyo", "JP", 22.0),
        ("Douala", "CM", 28.0),
    ]
    for i in range(10):
        for city, country, temp in cities:
            records.append({
                "city": city,
                "country": country,
                "temperature": temp + i * 0.1,
                "feels_like": temp - 1.0,
                "humidity": 65,
                "pressure": 1013,
                "weather_description": "clear sky",
                "wind_speed": 5.0,
                "visibility": 10000,
                "recorded_at": base_time - timedelta(hours=i),
            })
    return pd.DataFrame(records)


@pytest.fixture
def empty_df():
    """Return an empty DataFrame."""
    return pd.DataFrame()


@pytest.fixture
def df_with_nulls(valid_df):
    """Return a DataFrame with null values in critical columns."""
    df = valid_df.copy()
    df.loc[0, "temperature"] = None
    df.loc[1, "city"] = None
    return df


@pytest.fixture
def df_with_invalid_temperature(valid_df):
    """Return a DataFrame with out of range temperatures."""
    df = valid_df.copy()
    df.loc[0, "temperature"] = 200.0
    df.loc[1, "temperature"] = -100.0
    return df


@pytest.fixture
def df_with_invalid_humidity(valid_df):
    """Return a DataFrame with out of range humidity."""
    df = valid_df.copy()
    df.loc[0, "humidity"] = 150
    df.loc[1, "humidity"] = -10
    return df


@pytest.fixture
def df_with_invalid_wind(valid_df):
    """Return a DataFrame with negative wind speed."""
    df = valid_df.copy()
    df.loc[0, "wind_speed"] = -5.0
    return df


@pytest.fixture
def df_with_duplicates(valid_df):
    """Return a DataFrame with duplicate city/recorded_at combinations."""
    df = valid_df.copy()
    duplicate = valid_df.iloc[0].copy()
    return pd.concat([df, pd.DataFrame([duplicate])], ignore_index=True)


@pytest.fixture
def df_with_invalid_pressure(valid_df):
    """Return a DataFrame with out of range pressure."""
    df = valid_df.copy()
    df.loc[0, "pressure"] = 500
    return df


# ── Tests ─────────────────────────────────────────────────────────────

def test_check_not_empty_passes(valid_df):
    """Valid DataFrame should pass the not_empty check."""
    validator = DataValidator(valid_df)
    result = validator.check_not_empty()
    assert result.passed is True


def test_check_not_empty_fails(empty_df):
    """Empty DataFrame should fail the not_empty check."""
    validator = DataValidator(empty_df)
    result = validator.check_not_empty()
    assert result.passed is False


def test_check_required_columns_passes(valid_df):
    """DataFrame with all required columns should pass."""
    validator = DataValidator(valid_df)
    result = validator.check_required_columns()
    assert result.passed is True


def test_check_required_columns_fails():
    """DataFrame missing required columns should fail."""
    df = pd.DataFrame({"city": ["Paris"], "temperature": [15.0]})
    validator = DataValidator(df)
    result = validator.check_required_columns()
    assert result.passed is False


def test_check_no_nulls_passes(valid_df):
    """Valid DataFrame with no nulls should pass."""
    validator = DataValidator(valid_df)
    result = validator.check_no_nulls()
    assert result.passed is True


def test_check_no_nulls_fails(df_with_nulls):
    """DataFrame with nulls in critical columns should fail."""
    validator = DataValidator(df_with_nulls)
    result = validator.check_no_nulls()
    assert result.passed is False
    assert result.failed_records > 0


def test_check_temperature_range_passes(valid_df):
    """Valid temperatures should pass range check."""
    validator = DataValidator(valid_df)
    result = validator.check_temperature_range()
    assert result.passed is True


def test_check_temperature_range_fails(df_with_invalid_temperature):
    """Out of range temperatures should fail."""
    validator = DataValidator(df_with_invalid_temperature)
    result = validator.check_temperature_range()
    assert result.passed is False
    assert result.failed_records == 2


def test_check_humidity_range_passes(valid_df):
    """Valid humidity values should pass range check."""
    validator = DataValidator(valid_df)
    result = validator.check_humidity_range()
    assert result.passed is True


def test_check_humidity_range_fails(df_with_invalid_humidity):
    """Out of range humidity should fail."""
    validator = DataValidator(df_with_invalid_humidity)
    result = validator.check_humidity_range()
    assert result.passed is False


def test_check_wind_speed_range_passes(valid_df):
    """Valid wind speeds should pass range check."""
    validator = DataValidator(valid_df)
    result = validator.check_wind_speed_range()
    assert result.passed is True


def test_check_wind_speed_range_fails(df_with_invalid_wind):
    """Negative wind speed should fail."""
    validator = DataValidator(df_with_invalid_wind)
    result = validator.check_wind_speed_range()
    assert result.passed is False
    assert result.failed_records == 1


def test_check_no_duplicates_passes(valid_df):
    """DataFrame with no duplicates should pass."""
    validator = DataValidator(valid_df)
    result = validator.check_no_duplicates()
    assert result.passed is True


def test_check_no_duplicates_fails(df_with_duplicates):
    """DataFrame with duplicates should fail."""
    validator = DataValidator(df_with_duplicates)
    result = validator.check_no_duplicates()
    assert result.passed is False


def test_check_pressure_range_passes(valid_df):
    """Valid pressure values should pass range check."""
    validator = DataValidator(valid_df)
    result = validator.check_pressure_range()
    assert result.passed is True


def test_check_pressure_range_fails(df_with_invalid_pressure):
    """Out of range pressure should fail."""
    validator = DataValidator(df_with_invalid_pressure)
    result = validator.check_pressure_range()
    assert result.passed is False


def test_run_all_passes_on_valid_data(valid_df):
    """All 8 checks should pass on valid data."""
    validator = DataValidator(valid_df)
    report = validator.run_all()
    assert report.passed is True
    assert len(report.results) == 8
    assert len(report.failed_checks) == 0


def test_run_all_fails_on_invalid_data(df_with_invalid_temperature):
    """Run all should detect failures on invalid data."""
    validator = DataValidator(df_with_invalid_temperature)
    report = validator.run_all()
    assert report.passed is False
    assert len(report.failed_checks) > 0


def test_validation_report_summary(valid_df):
    """Validation report summary should show correct counts."""
    validator = DataValidator(valid_df)
    report = validator.run_all()
    assert "8/8" in report.summary