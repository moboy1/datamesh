"""
Synthetic Banking Data Generator
Produces realistic but entirely fictitious records for customer and deposits domains:
"""

import os
import random
import trino
from faker import Faker
from faker.providers import bank

fake = Faker("en_GB")
fake.add_provider(bank)

TRINO_HOST = os.getenv("TRINO_HOST", "localhost")
TRINO_PORT = int(os.getenv("TRINO_PORT", "8080"))
TRINO_USER = "admin"

NUM_CUSTOMERS    = 200
NUM_TRANSACTIONS = 500
NUM_ACCOUNTS     = 150


def get_conn():
    return trino.dbapi.connect(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        http_scheme="http",
    )


def insert_rows(cur, table: str, rows: list[dict], batch_size: int = 100):
    """Insert rows in batches using multi-row values to minimise round-trips."""
    if not rows:
        return
    cols = ", ".join(rows[0].keys())
    total = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        placeholders = ", ".join(
            "(" + ", ".join(["?" for _ in batch[0]]) + ")"
            for _ in batch
        )
        flat_values = [v for r in batch for v in r.values()]
        cur.execute(
            f"INSERT INTO {table} ({cols}) VALUES {placeholders}",
            flat_values,
        )
        total += len(batch)
    print(f"  Inserted {total} rows → {table}")


# Customer Domain

def generate_customer_records(n: int) -> list[dict]:
    rows = []
    for _ in range(n):
        rows.append({
            "customer_id":               fake.uuid4(),
            "full_name":                 fake.name(),
            "email":                     fake.email(),
            "phone":                     fake.phone_number(),
            "national_insurance_number": fake.bothify(text="??######?").upper(),
            "date_of_birth":             str(fake.date_of_birth(minimum_age=18, maximum_age=80)),
            "address":                   fake.address().replace("\n", ", "),
            "account_number":            fake.bban(),
            "sort_code":                 fake.bothify(text="##-##-##"),
            "risk_rating":               random.choice(["low", "medium", "high"]),
            "created_at":                str(fake.date_time_this_decade()),
        })
    return rows


def generate_transactions(n: int, customer_ids: list) -> list[dict]:
    rows = []
    for _ in range(n):
        rows.append({
            "transaction_id":   fake.uuid4(),
            "customer_id":      random.choice(customer_ids),
            "amount_gbp":       round(random.uniform(1.0, 50000.0), 2),
            "currency":         "GBP",
            "transaction_type": random.choice(["credit", "debit", "transfer"]),
            "merchant":         fake.company(),
            "timestamp":        str(fake.date_time_this_year()),
            "status":           random.choice(["completed", "pending", "failed"]),
        })
    return rows


# Deposits Domain

def generate_deposit_accounts(n: int) -> list[dict]:
    rows = []
    for _ in range(n):
        rows.append({
            "account_id":    fake.uuid4(),
            "account_number": fake.bban(),
            "account_type":  random.choice(["current", "savings", "isa", "fixed-term"]),
            "interest_rate": round(random.uniform(0.5, 5.5), 2),
            "balance_gbp":   round(random.uniform(0.0, 500000.0), 2),
            "currency":      "GBP",
            "opened_date":   str(fake.date_between(start_date="-10y", end_date="today")),
            "maturity_date": str(fake.date_between(start_date="today", end_date="+5y")),
            "risk_band":     random.choice(["A", "B", "C", "D"]),
            "domain":        "deposits",
        })
    return rows


def generate_balance_data(account_ids: list) -> list[dict]:
    rows = []
    for acct_id in account_ids:
        for _ in range(random.randint(1, 5)):
            rows.append({
                "snapshot_id":   fake.uuid4(),
                "account_id":    acct_id,
                "balance_gbp":   round(random.uniform(0.0, 500000.0), 2),
                "snapshot_date": str(fake.date_between(start_date="-1y", end_date="today")),
                "reported":      random.choice([True, False]),
            })
    return rows


# Main

def main():
    conn = get_conn()
    cur  = conn.cursor()

    print("\nCustomer Domain")
    customers = generate_customer_records(NUM_CUSTOMERS)
    insert_rows(cur, "customer.default.customer_records", customers)

    customer_ids = [r["customer_id"] for r in customers]
    transactions = generate_transactions(NUM_TRANSACTIONS, customer_ids)
    insert_rows(cur, "customer.default.transactions", transactions)

    print("\nDeposits Domain")
    accounts = generate_deposit_accounts(NUM_ACCOUNTS)
    insert_rows(cur, "deposits.default.deposit_accounts", accounts)

    account_ids = [r["account_id"] for r in accounts]
    balances = generate_balance_data(account_ids)
    insert_rows(cur, "deposits.default.balance_data", balances)

    cur.close()
    conn.close()
    print("\nDone. All synthetic data inserted via Trino.")


if __name__ == "__main__":
    main()
