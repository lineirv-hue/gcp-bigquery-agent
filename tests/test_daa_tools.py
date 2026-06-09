"""
Integration tests for DAA sql_validation_tool.
Requires live BigQuery credentials and the dataset to be set up.
Run: pytest tests/test_daa_tools.py -v
"""
import os
import pytest
from agents.daa.tools.sql_validation_tool import (
    validate_sql_syntax,
    execute_sql_query,
    get_query_cost_estimate,
)

PROJECT = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
DATASET = os.environ.get("BQ_DATASET_ID", "retail_analytics")
TABLE = f"`{PROJECT}.{DATASET}.sales_orders`"


def test_validate_valid_sql():
    sql = f"SELECT order_id, total_amount FROM {TABLE} LIMIT 5"
    result = validate_sql_syntax(sql)
    assert result["valid"] is True
    assert result["errors"] == []
    assert result["bytes_processed"] >= 0


def test_validate_invalid_sql():
    sql = "SELECT * FROM nonexistent_table_xyz WHERE foo = bar BAD SYNTAX"
    result = validate_sql_syntax(sql)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


def test_validate_blocks_write_statement():
    sql = f"DELETE FROM {TABLE} WHERE 1=1"
    result = validate_sql_syntax(sql)
    assert result["valid"] is False
    assert "Write statements" in result["errors"][0]


def test_execute_sql_query_returns_rows():
    sql = f"SELECT category, COUNT(*) as order_count FROM {TABLE} GROUP BY category ORDER BY order_count DESC"
    result = execute_sql_query(sql, max_rows=10)
    assert result["success"] is True
    assert len(result["rows"]) > 0
    assert "category" in result["columns"]
    assert "order_count" in result["columns"]


def test_execute_sql_query_blocks_write():
    sql = f"INSERT INTO {TABLE} VALUES (1, 2, 3)"
    result = execute_sql_query(sql)
    assert result["success"] is False
    assert "not allowed" in result["error"]


def test_execute_sql_max_rows_cap():
    sql = f"SELECT * FROM {TABLE}"
    result = execute_sql_query(sql, max_rows=200)  # Over the cap
    assert result["success"] is True
    assert len(result["rows"]) <= 100  # Hard cap


def test_cost_estimate_valid():
    sql = f"SELECT * FROM {TABLE}"
    result = get_query_cost_estimate(sql)
    assert result["valid"] is True
    assert "estimated_cost_usd" in result
    assert result["estimated_cost_usd"] >= 0.0
    assert result["recommendation"] != ""


def test_cost_estimate_invalid_sql():
    sql = "SELECT FROM WHERE"
    result = get_query_cost_estimate(sql)
    assert result["valid"] is False
    assert len(result["errors"]) > 0
