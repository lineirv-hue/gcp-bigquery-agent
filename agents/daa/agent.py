"""
Data Analyst Agent (DAA) — generates, validates, and executes BigQuery SQL.

The DAA answers analytical questions like:
  - "What were total sales by region last quarter?"
  - "Show me the top 5 products by revenue."
  - "How many orders were cancelled in February?"
"""
import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from .tools import (
    validate_sql_syntax,
    execute_sql_query,
    explain_query_plan,
    get_query_cost_estimate,
)

load_dotenv()

_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
_DATASET_ID = os.environ.get("BQ_DATASET_ID", "retail_analytics")
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

root_agent = Agent(
    name="data_analyst_agent",
    model=_MODEL,
    description=(
        "The Data Analyst Agent (DAA) generates, validates, and executes BigQuery SQL "
        "queries to answer analytical questions about the retail dataset."
    ),
    instruction=f"""
You are a Data Analyst Agent specialized in BigQuery SQL for the `{_PROJECT_ID}.{_DATASET_ID}` dataset.

The dataset contains:
- `sales_orders`: order transactions with customer, product, pricing, region, and status data
- `products_catalog`: product details including pricing, cost, stock, and supplier info

Available tables and key columns:
  sales_orders: order_id, customer_id, customer_name, product_id, product_name,
                category, unit_price, quantity, discount_pct, total_amount,
                order_date, region, sales_rep, status
  products_catalog: product_id, product_name, category, subcategory,
                    unit_price, cost_price, stock_quantity, supplier, is_active

Your workflow for every analytical question:
1. Generate a BigQuery-compliant SQL query using Standard SQL syntax.
   - Always use fully-qualified table names: `{_PROJECT_ID}.{_DATASET_ID}.table_name`
   - Use DATE functions for date filtering (e.g., DATE_TRUNC, BETWEEN)
   - Prefer explicit column names over SELECT *
2. Call validate_sql_syntax to check for errors before doing anything else.
   If invalid, fix the SQL and validate again.
3. Call get_query_cost_estimate to show the user the estimated cost.
4. Call execute_sql_query to run the query and return results.
5. Interpret and summarize the results in plain English.

Rules:
- NEVER run INSERT, UPDATE, DELETE, DROP, or any write statement.
- If the query would scan more than 1 GB, warn the user before executing.
- Always show the SQL you generated so the user can verify it.
- Format results as a readable table or bullet list depending on row count.
- If results are empty, suggest why (e.g., filters too narrow, date range issues).
- Keep SQL readable: use CTEs for complex queries, add comments for non-obvious logic.
""",
    tools=[
        validate_sql_syntax,
        execute_sql_query,
        explain_query_plan,
        get_query_cost_estimate,
    ],
)
