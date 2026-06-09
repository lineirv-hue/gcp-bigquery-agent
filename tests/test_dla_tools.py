"""
Integration tests for DLA dictionary_tool.
Requires live BigQuery credentials and the dataset to be set up.
Run: pytest tests/test_dla_tools.py -v
"""
import pytest
from agents.dla.tools.dictionary_tool import (
    get_dataset_tables,
    get_table_schema,
    get_table_sample,
    get_dataset_overview,
    search_tables_by_keyword,
)


def test_get_dataset_tables():
    result = get_dataset_tables()
    assert "tables" in result
    assert len(result["tables"]) >= 2
    table_ids = [t["table_id"] for t in result["tables"]]
    assert "sales_orders" in table_ids
    assert "products_catalog" in table_ids


def test_get_table_schema_sales_orders():
    result = get_table_schema("sales_orders")
    assert result["table"].endswith("sales_orders")
    column_names = [c["name"] for c in result["columns"]]
    assert "order_id" in column_names
    assert "total_amount" in column_names
    assert "status" in column_names


def test_get_table_schema_fully_qualified():
    import os
    project = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
    dataset = os.environ.get("BQ_DATASET_ID", "retail_analytics")
    result = get_table_schema(f"{project}.{dataset}.products_catalog")
    assert "columns" in result
    assert len(result["columns"]) > 0


def test_get_table_sample():
    result = get_table_sample("sales_orders", limit=3)
    assert "rows" in result
    assert len(result["rows"]) <= 3
    assert "order_id" in result["columns"]


def test_search_tables_by_keyword_price():
    result = search_tables_by_keyword("price")
    assert result["keyword"] == "price"
    matched_columns = [m["matched_on"] for m in result["matches"] if m["match_type"] == "column"]
    assert any("price" in c.lower() for c in matched_columns)


def test_search_tables_by_keyword_no_match():
    result = search_tables_by_keyword("nonexistentxyz123")
    assert result["matches"] == []


def test_get_dataset_overview():
    result = get_dataset_overview()
    assert "tables" in result
    assert result["dataset"] == "retail_analytics"
    for tbl in result["tables"]:
        assert "columns" in tbl
        assert len(tbl["columns"]) > 0
