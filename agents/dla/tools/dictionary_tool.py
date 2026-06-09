"""
dictionary_tool — BigQuery metadata tools for the Data Librarian Agent.

Each function is a standalone ADK tool that the DLA agent can call to
discover, inspect, and search tables in the configured dataset.
"""
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
_DATASET_ID = os.environ.get("BQ_DATASET_ID", "retail_analytics")


@lru_cache(maxsize=1)
def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=_PROJECT_ID)


def get_dataset_tables() -> dict[str, Any]:
    """
    List all tables in the configured BigQuery dataset with row counts and
    creation timestamps.

    Returns:
        A dict with keys:
          - dataset: fully-qualified dataset name
          - tables: list of {table_id, full_id, num_rows, created}
    """
    client = _bq_client()
    tables = []
    for tbl in client.list_tables(f"{_PROJECT_ID}.{_DATASET_ID}"):
        full_ref = client.get_table(tbl.reference)
        tables.append(
            {
                "table_id": tbl.table_id,
                "full_id": f"{_PROJECT_ID}.{_DATASET_ID}.{tbl.table_id}",
                "num_rows": full_ref.num_rows,
                "created": str(full_ref.created),
                "description": full_ref.description or "",
            }
        )
    return {"dataset": f"{_PROJECT_ID}.{_DATASET_ID}", "tables": tables}


def get_table_schema(table_id: str) -> dict[str, Any]:
    """
    Return the schema (columns, types, descriptions) of a BigQuery table.

    Args:
        table_id: The table name (e.g. 'sales_orders') or full id
                  (e.g. 'project.dataset.table').

    Returns:
        A dict with keys:
          - table: full table id
          - description: table-level description
          - columns: list of {name, field_type, mode, description}
    """
    client = _bq_client()
    if "." not in table_id:
        table_id = f"{_PROJECT_ID}.{_DATASET_ID}.{table_id}"
    tbl = client.get_table(table_id)
    columns = [
        {
            "name": f.name,
            "field_type": f.field_type,
            "mode": f.mode,
            "description": f.description or "",
        }
        for f in tbl.schema
    ]
    return {
        "table": table_id,
        "description": tbl.description or "",
        "num_rows": tbl.num_rows,
        "columns": columns,
    }


def search_tables_by_keyword(keyword: str) -> dict[str, Any]:
    """
    Search all tables in the dataset for tables or columns whose name or
    description contains the given keyword (case-insensitive).

    Args:
        keyword: The term to search for (e.g. 'price', 'customer', 'date').

    Returns:
        A dict with:
          - keyword: the search term used
          - matches: list of {table_id, match_type, matched_on, description}
    """
    client = _bq_client()
    kw = keyword.lower()
    matches = []

    for tbl in client.list_tables(f"{_PROJECT_ID}.{_DATASET_ID}"):
        full_tbl = client.get_table(tbl.reference)
        # Match on table name / description
        if kw in tbl.table_id.lower() or kw in (full_tbl.description or "").lower():
            matches.append(
                {
                    "table_id": tbl.table_id,
                    "match_type": "table",
                    "matched_on": tbl.table_id,
                    "description": full_tbl.description or "",
                }
            )
        # Match on column names / descriptions
        for field in full_tbl.schema:
            if kw in field.name.lower() or kw in (field.description or "").lower():
                matches.append(
                    {
                        "table_id": tbl.table_id,
                        "match_type": "column",
                        "matched_on": field.name,
                        "description": field.description or "",
                    }
                )

    return {"keyword": keyword, "matches": matches}


def get_table_sample(table_id: str, limit: int = 5) -> dict[str, Any]:
    """
    Return a small sample of rows from a table for quick data inspection.

    Args:
        table_id: The table name (e.g. 'sales_orders') or full id.
        limit: Maximum number of rows to return (default 5, max 20).

    Returns:
        A dict with keys:
          - table: full table id
          - columns: list of column names
          - rows: list of row dicts
    """
    client = _bq_client()
    if "." not in table_id:
        full_id = f"{_PROJECT_ID}.{_DATASET_ID}.{table_id}"
    else:
        full_id = table_id

    limit = min(int(limit), 20)
    query = f"SELECT * FROM `{full_id}` LIMIT {limit}"
    rows = list(client.query(query).result())

    if not rows:
        return {"table": full_id, "columns": [], "rows": []}

    columns = list(rows[0].keys())
    return {
        "table": full_id,
        "columns": columns,
        "rows": [dict(r) for r in rows],
    }


def get_dataset_overview() -> dict[str, Any]:
    """
    Return a high-level overview of the entire dataset: tables, row counts,
    and all column names grouped by table.  Useful as a first call to
    understand what data is available.

    Returns:
        A dict with:
          - project: GCP project id
          - dataset: dataset id
          - tables: list of {table_id, num_rows, columns: [name, field_type]}
    """
    client = _bq_client()
    overview = []
    for tbl in client.list_tables(f"{_PROJECT_ID}.{_DATASET_ID}"):
        full_tbl = client.get_table(tbl.reference)
        overview.append(
            {
                "table_id": tbl.table_id,
                "description": full_tbl.description or "",
                "num_rows": full_tbl.num_rows,
                "columns": [
                    {"name": f.name, "field_type": f.field_type}
                    for f in full_tbl.schema
                ],
            }
        )
    return {
        "project": _PROJECT_ID,
        "dataset": _DATASET_ID,
        "tables": overview,
    }
