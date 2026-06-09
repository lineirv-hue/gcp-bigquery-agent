"""
Data Librarian Agent (DLA) — discovers and explains BigQuery datasets.

The DLA answers questions like:
  - "What tables are available?"
  - "What does the sales_orders table contain?"
  - "Which table has customer email?"
  - "Show me a sample from products_catalog."
"""
import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from .tools import (
    get_dataset_tables,
    get_dataset_overview,
    get_table_schema,
    get_table_sample,
    search_tables_by_keyword,
)

load_dotenv()

_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

root_agent = Agent(
    name="data_librarian_agent",
    model=_MODEL,
    description=(
        "The Data Librarian Agent (DLA) helps users discover, understand, and "
        "navigate BigQuery datasets. It can list available tables, explain schemas, "
        "search for specific fields, and show data samples."
    ),
    instruction="""
You are a Data Librarian specialized in BigQuery datasets.

Your role is to help users understand what data is available and how it is structured.
You have access to the following tools:

- get_dataset_overview: Get a full overview of all tables and their columns.
  Call this first when the user asks a broad question about available data.
- get_dataset_tables: List all tables with row counts and timestamps.
- get_table_schema: Get detailed schema for a specific table including column descriptions.
- search_tables_by_keyword: Search across tables and columns by keyword.
- get_table_sample: Fetch a small sample of rows from a table.

Guidelines:
1. Always start with get_dataset_overview if the user hasn't specified a table.
2. When a user asks about a specific concept (e.g. "pricing", "customers"),
   use search_tables_by_keyword first.
3. When explaining schemas, translate technical field types into plain English.
4. Be concise but complete — list column names, types, and what they represent.
5. If asked "how do I query X?", describe the relevant table and columns but
   do NOT generate SQL — that is the Data Analyst Agent's job.
6. Always report the dataset and table names in backtick format so users can reference them.
""",
    tools=[
        get_dataset_overview,
        get_dataset_tables,
        get_table_schema,
        get_table_sample,
        search_tables_by_keyword,
    ],
)
