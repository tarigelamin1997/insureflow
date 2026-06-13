-- =============================================================================
-- Phase 02 — PFS (Premium & Finance System) schema DDL.
--
-- Runs ONCE on first init of postgres-pfs, AFTER 00-replication-role.sh
-- (entrypoint executes /docker-entrypoint-initdb.d/ files in FILENAME order).
--
-- DESIGN CONTRACT (approved Chunk-2 schema spec) — see pms/01-schema.sql header
-- for the shared rules. PFS-specific points:
--
--   - CROSS-INSTANCE refs are PLAIN columns with NO foreign key: policy_id on
--     premium_transactions, reinsurance_entries, and ifrs17_data all point at PMS
--     (a separate instance, ADR-002) — no FK is possible or wanted.
--   - The ONLY intra-PFS FK is gl_settlements.transaction_id → premium_transactions
--     (nullable: a GL line may exist without a linked premium transaction).
--   - premium_transactions.amount is NOT NULL (a transaction must carry an amount).
--   - premium_transactions.currency is NULLABLE on purpose: scenario S05 seeds NULL
--     currency, interpreted downstream as SAR. The CHECK still constrains non-null
--     values to {SAR, USD}; a CHECK passes on NULL, so NULL remains valid.
--   - No PFS table needs REPLICA IDENTITY FULL — all keep DEFAULT (PK-only
--     before-image) to limit WAL. See ADR-003.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- premium_transactions — one row per premium transaction.
--   policy_id is a CROSS-INSTANCE logical ref → PMS.policies; NO FK.
--   Referenced by gl_settlements (the one intra-PFS FK), so defined first.
-- -----------------------------------------------------------------------------
CREATE TABLE premium_transactions (
    transaction_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id        BIGINT,        -- cross-instance logical ref → PMS.policies; NO FK
    transaction_date TEXT,          -- TEXT: raw mixed date formats (S04)
    amount           NUMERIC(14,2) NOT NULL,
    currency         VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),  -- NULLABLE: NULL ⇒ SAR (S05)
    transaction_type VARCHAR(20) NOT NULL,
    payment_status   VARCHAR(20),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- reinsurance_entries — one row per reinsurance treaty entry.
--   policy_id is a CROSS-INSTANCE logical ref → PMS.policies; NO FK.
-- -----------------------------------------------------------------------------
CREATE TABLE reinsurance_entries (
    reinsurance_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id           BIGINT,    -- cross-instance logical ref → PMS.policies; NO FK
    treaty_type         VARCHAR(30),
    retention_threshold NUMERIC(14,2),
    ceded_amount        NUMERIC(14,2),
    recovery_amount     NUMERIC(14,2),
    currency            VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    entry_date          TEXT,      -- TEXT: raw mixed date formats (S04)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- gl_settlements — one row per general-ledger settlement line.
--   transaction_id → premium_transactions is the ONLY intra-PFS FK (nullable).
-- -----------------------------------------------------------------------------
CREATE TABLE gl_settlements (
    gl_settlement_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gl_account       VARCHAR(20) NOT NULL,
    transaction_id   BIGINT REFERENCES premium_transactions (transaction_id),  -- intra-PFS FK, nullable
    posting_date     TEXT,          -- TEXT: raw mixed date formats (S04)
    debit_amount     NUMERIC(14,2),
    credit_amount    NUMERIC(14,2),
    currency         VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    fiscal_period    VARCHAR(7),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- ifrs17_data — one row per IFRS 17 measurement record.
--   policy_id is a CROSS-INSTANCE logical ref → PMS.policies; NO FK.
-- -----------------------------------------------------------------------------
CREATE TABLE ifrs17_data (
    ifrs17_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id             BIGINT,  -- cross-instance logical ref → PMS.policies; NO FK
    contract_group        VARCHAR(40) NOT NULL,
    measurement_model     VARCHAR(10) NOT NULL CHECK (measurement_model IN ('GMM', 'PAA', 'VFA')),
    csm                   NUMERIC(16,2),
    risk_adjustment       NUMERIC(16,2),
    coverage_start_date   TEXT,    -- TEXT: raw mixed date formats (S04)
    coverage_end_date     TEXT,    -- TEXT: raw mixed date formats (S04)
    fulfilment_cash_flows NUMERIC(16,2),
    loss_component        NUMERIC(16,2),
    currency              VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    reporting_period      VARCHAR(7),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- Table SELECT for the replication role (CONNECT granted by 00-replication-role.sh).
-- Literal role `replicator` coupled to .env POSTGRES_REPLICATION_USER.
-- -----------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;
