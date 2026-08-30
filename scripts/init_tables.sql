CREATE SCHEMA IF NOT EXISTS customer.default;

DROP TABLE IF EXISTS customer.default.customer_records;
CREATE TABLE customer.default.customer_records (
    customer_id              VARCHAR,
    full_name                VARCHAR,
    email                    VARCHAR,
    phone                    VARCHAR,
    national_insurance_number VARCHAR,
    date_of_birth            VARCHAR,
    address                  VARCHAR,
    account_number           VARCHAR,
    sort_code                VARCHAR,
    risk_rating              VARCHAR,
    created_at               VARCHAR
)
WITH (format = 'PARQUET');

DROP TABLE IF EXISTS customer.default.transactions;
CREATE TABLE customer.default.transactions (
    transaction_id   VARCHAR,
    customer_id      VARCHAR,
    amount_gbp       DOUBLE,
    currency         VARCHAR,
    transaction_type VARCHAR,
    merchant         VARCHAR,
    timestamp        VARCHAR,
    status           VARCHAR
)
WITH (format = 'PARQUET');

CREATE SCHEMA IF NOT EXISTS deposits.default;

DROP TABLE IF EXISTS deposits.default.deposit_accounts;
CREATE TABLE deposits.default.deposit_accounts (
    account_id    VARCHAR,
    account_number VARCHAR,
    account_type  VARCHAR,
    interest_rate DOUBLE,
    balance_gbp   DOUBLE,
    currency      VARCHAR,
    opened_date   VARCHAR,
    maturity_date VARCHAR,
    risk_band     VARCHAR,
    domain        VARCHAR
)
WITH (format = 'PARQUET');

DROP TABLE IF EXISTS deposits.default.balance_data;
CREATE TABLE deposits.default.balance_data (
    snapshot_id   VARCHAR,
    account_id    VARCHAR,
    balance_gbp   DOUBLE,
    snapshot_date VARCHAR,
    reported      BOOLEAN
)
WITH (format = 'PARQUET');
