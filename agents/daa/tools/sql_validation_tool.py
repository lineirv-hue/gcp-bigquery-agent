"""
sql_validation_tool — BigQuery SQL validation and execution tools for the DAA.

These tools allow the Data Analyst Agent to verify SQL correctness before
running queries, estimate costs, and return results safely.
"""
import os
import re
from typing import Any

from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig
from functools import lru_cache

load_dotenv()

_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
_DATASET_ID = os.environ.get("BQ_DATASET_ID", "retail_analytics")
_MAX_RESULT_ROWS = 100
_MAX_BYTES_BILLED = 100 * 1024 * 1024  # 100 MB safety cap


@lru_cache(maxsize=1)
def _bq_client() -> bigquery.Client:
    return bigquery.Client(project=_PROJECT_ID)


def _is_write_statement(sql: str) -> bool:
    """Reject DML/DDL that could mutate data."""
    normalized = re.sub(r"--[^\n]*", "", sql).upper().strip()
    dangerous = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "TRUNCATE", "MERGE", "ALTER")
    return any(normalized.startswith(kw) for kw in dangerous)


def validate_sql_syntax(sql: str) -> dict[str, Any]:
    """
    Validate a BigQuery SQL query for syntax errors using a dry-run job.
    Does NOT execute the query or consume any data quota.

    Args:
        sql: The SQL query string to validate.

    Returns:
        A dict with:
          - valid: bool
          - bytes_processed: estimated bytes that would be scanned (if valid)
          - errors: list of error messages (if invalid)
    """
    if _is_write_statement(sql):
        return {
            "valid": False,
            "bytes_processed": 0,
            "errors": ["Write statements (INSERT/UPDATE/DELETE/DROP/etc.) are not allowed."],
        }

    client = _bq_client()
    job_config = QueryJobConfig(dry_run=True, use_query_cache=False)
    try:
        job = client.query(sql, job_config=job_config)
        return {
            "valid": True,
            "bytes_processed": job.total_bytes_processed,
            "bytes_processed_human": _human_bytes(job.total_bytes_processed),
            "errors": [],
        }
    except Exception as exc:
        return {
            "valid": False,
            "bytes_processed": 0,
            "errors": [str(exc)],
        }


def execute_sql_query(sql: str, max_rows: int = 20) -> dict[str, Any]:
    """
    Execute a read-only BigQuery SQL query and return results.
    Capped at 100 MB scanned and 100 rows returned for safety.

    Args:
        sql: The SELECT query to run.
        max_rows: Maximum rows to return (default 20, max 100).

    Returns:
        A dict with:
          - success: bool
          - columns: list of column names
          - rows: list of row dicts
          - total_rows: total rows in result set (may exceed max_rows)
          - bytes_processed: bytes scanned
          - error: error message if success is False
    """
    if _is_write_statement(sql):
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "bytes_processed": 0,
            "error": "Write statements are not allowed.",
        }

    # Validate first
    validation = validate_sql_syntax(sql)
    if not validation["valid"]:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "bytes_processed": 0,
            "error": "; ".join(validation["errors"]),
        }

    max_rows = min(int(max_rows), _MAX_RESULT_ROWS)
    client = _bq_client()
    job_config = QueryJobConfig(maximum_bytes_billed=_MAX_BYTES_BILLED)

    try:
        job = client.query(sql, job_config=job_config)
        result = job.result()
        rows = []
        total = 0
        for row in result:
            total += 1
            if len(rows) < max_rows:
                rows.append({k: _serialize(v) for k, v in dict(row).items()})

        columns = list(rows[0].keys()) if rows else []
        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "total_rows": total,
            "bytes_processed": job.total_bytes_processed,
            "bytes_processed_human": _human_bytes(job.total_bytes_processed or 0),
            "error": None,
        }
    except Exception as exc:
        return {
            "success": False,
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "bytes_processed": 0,
            "error": str(exc),
        }


def explain_query_plan(sql: str) -> dict[str, Any]:
    """
    Return a simplified explanation of how BigQuery will execute a query,
    including which tables are scanned and join strategies used.

    Args:
        sql: The SQL query to explain.

    Returns:
        A dict with:
          - valid: bool
          - query_plan: list of stage descriptions (simplified)
          - bytes_processed: estimated bytes
          - error: error message if invalid
    """
    validation = validate_sql_syntax(sql)
    if not validation["valid"]:
        return {
            "valid": False,
            "query_plan": [],
            "bytes_processed": 0,
            "error": "; ".join(validation["errors"]),
        }

    client = _bq_client()
    try:
        job = client.query(sql)
        job.result()
        plan = []
        if job.query_plan:
            for stage in job.query_plan:
                plan.append(
                    {
                        "name": stage.name,
                        "status": stage.status,
                        "records_read": stage.records_read,
                        "records_written": stage.records_written,
                        "shuffle_output_bytes": stage.shuffle_output_bytes,
                    }
                )
        return {
            "valid": True,
            "query_plan": plan,
            "bytes_processed": job.total_bytes_processed,
            "bytes_processed_human": _human_bytes(job.total_bytes_processed or 0),
            "error": None,
        }
    except Exception as exc:
        return {"valid": False, "query_plan": [], "bytes_processed": 0, "error": str(exc)}


def get_query_cost_estimate(sql: str) -> dict[str, Any]:
    """
    Estimate the cost of running a BigQuery SQL query without executing it.
    Uses BigQuery on-demand pricing ($6.25 per TB scanned).

    Args:
        sql: The SQL query to estimate cost for.

    Returns:
        A dict with:
          - valid: bool
          - bytes_processed: bytes that would be scanned
          - estimated_cost_usd: estimated cost in USD
          - recommendation: advice on whether to proceed
          - errors: list of error messages
    """
    validation = validate_sql_syntax(sql)
    if not validation["valid"]:
        return {
            "valid": False,
            "bytes_processed": 0,
            "estimated_cost_usd": 0.0,
            "recommendation": "Fix syntax errors before estimating cost.",
            "errors": validation["errors"],
        }

    bytes_processed = validation["bytes_processed"]
    tb_processed = bytes_processed / (1024 ** 4)
    cost_usd = round(tb_processed * 6.25, 6)

    if cost_usd < 0.001:
        recommendation = "Safe to run — cost is negligible."
    elif cost_usd < 1.0:
        recommendation = "Low cost query. Safe to run."
    elif cost_usd < 10.0:
        recommendation = "Moderate cost. Consider adding filters or partitioning."
    else:
        recommendation = "High cost. Review query and add WHERE clauses or use partitioned tables."

    return {
        "valid": True,
        "bytes_processed": bytes_processed,
        "bytes_processed_human": _human_bytes(bytes_processed),
        "estimated_cost_usd": cost_usd,
        "recommendation": recommendation,
        "errors": [],
    }


def _human_bytes(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _serialize(value: Any) -> Any:
    """Convert non-JSON-serializable BQ types to strings."""
    import datetime
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
