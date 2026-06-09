"""
One-time setup: creates the BigQuery dataset and loads sample CSV data.
Run: python scripts/setup_bigquery.py
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "dev-country-229003")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "retail_analytics")
LOCATION = os.environ.get("GCP_LOCATION", "US")
DATA_DIR = Path(__file__).parent.parent / "data"

TABLES = {
    "sales_orders": {
        "file": "sales_data.csv",
        "schema": [
            bigquery.SchemaField("order_id", "STRING", description="Unique order identifier"),
            bigquery.SchemaField("customer_id", "STRING", description="Customer identifier"),
            bigquery.SchemaField("customer_name", "STRING", description="Full name of the customer"),
            bigquery.SchemaField("customer_email", "STRING", description="Customer email address"),
            bigquery.SchemaField("product_id", "STRING", description="Product identifier"),
            bigquery.SchemaField("product_name", "STRING", description="Name of the product ordered"),
            bigquery.SchemaField("category", "STRING", description="Product category (Electronics, Furniture, Apparel)"),
            bigquery.SchemaField("unit_price", "FLOAT64", description="Price per unit in USD"),
            bigquery.SchemaField("quantity", "INTEGER", description="Number of units ordered"),
            bigquery.SchemaField("discount_pct", "FLOAT64", description="Discount applied as a decimal (0.10 = 10%)"),
            bigquery.SchemaField("total_amount", "FLOAT64", description="Final order total in USD after discount"),
            bigquery.SchemaField("order_date", "DATE", description="Date the order was placed"),
            bigquery.SchemaField("region", "STRING", description="Sales region (North, South, East, West)"),
            bigquery.SchemaField("sales_rep", "STRING", description="Name of the sales representative"),
            bigquery.SchemaField("status", "STRING", description="Order status (Completed, Shipped, Cancelled)"),
        ],
    },
    "products_catalog": {
        "file": "products_catalog.csv",
        "schema": [
            bigquery.SchemaField("product_id", "STRING", description="Unique product identifier"),
            bigquery.SchemaField("product_name", "STRING", description="Display name of the product"),
            bigquery.SchemaField("category", "STRING", description="Top-level category"),
            bigquery.SchemaField("subcategory", "STRING", description="Product subcategory"),
            bigquery.SchemaField("unit_price", "FLOAT64", description="Retail price in USD"),
            bigquery.SchemaField("cost_price", "FLOAT64", description="Cost of goods sold in USD"),
            bigquery.SchemaField("stock_quantity", "INTEGER", description="Current units in stock"),
            bigquery.SchemaField("supplier", "STRING", description="Supplier name"),
            bigquery.SchemaField("sku", "STRING", description="Stock keeping unit code"),
            bigquery.SchemaField("description", "STRING", description="Product description"),
            bigquery.SchemaField("is_active", "BOOL", description="Whether the product is currently sold"),
            bigquery.SchemaField("created_date", "DATE", description="Date the product was added to catalog"),
        ],
    },
}


def create_dataset(client: bigquery.Client) -> None:
    dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = LOCATION
    dataset_ref.description = "Retail analytics dataset — sales orders and product catalog"
    client.create_dataset(dataset_ref, exists_ok=True)
    print(f"Dataset '{PROJECT_ID}.{DATASET_ID}' ready.")


def load_table(client: bigquery.Client, table_name: str, config: dict) -> None:
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    csv_path = DATA_DIR / config["file"]

    job_config = bigquery.LoadJobConfig(
        schema=config["schema"],
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with open(csv_path, "rb") as f:
        job = client.load_table_from_file(f, table_id, job_config=job_config)

    job.result()
    table = client.get_table(table_id)
    print(f"  Loaded {table.num_rows} rows into '{table_id}'.")


def main() -> None:
    client = bigquery.Client(project=PROJECT_ID)
    print(f"Setting up BigQuery for project: {PROJECT_ID}")
    create_dataset(client)
    for table_name, config in TABLES.items():
        print(f"Loading table '{table_name}'...")
        load_table(client, table_name, config)
    print("\nSetup complete. Tables in dataset:")
    for table in client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"):
        print(f"  - {table.table_id}")


if __name__ == "__main__":
    main()
