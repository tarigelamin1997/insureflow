-- =============================================================================
-- Phase 02 — PMS (Policy Management System) schema DDL.
--
-- Runs ONCE on first init of postgres-pms, AFTER 00-replication-role.sh (the
-- official postgres:16 entrypoint executes files in /docker-entrypoint-initdb.d/
-- directly, in FILENAME order: 00- role first, 01- schema second).
--
-- DESIGN CONTRACT (approved Chunk-2 schema spec):
--   - Every table: surrogate BIGINT GENERATED ALWAYS AS IDENTITY PK (NOT NULL),
--     plus created_at / updated_at TIMESTAMPTZ NOT NULL DEFAULT now().
--   - ALL business / event date columns are TEXT — the source preserves the raw,
--     mixed date formats (scenario S04). Only created_at/updated_at are real
--     TIMESTAMPTZ. Casting/normalisation is a Silver-layer (Phase 05) concern.
--   - Intra-PMS foreign keys are ENFORCED. There are NO cross-instance FKs in PMS
--     (every reference here is local). CMS/PFS hold the cross-instance logical refs.
--   - REPLICA IDENTITY FULL on policyholders (Silver dedups on non-PK nic and
--     tracks SCD on address/customer_tier — needs full before-images). All other
--     PMS tables keep DEFAULT (PK-only before-image) to limit WAL. See ADR-003.
--   - Minimal CHECK enums only where the spec pins a closed domain.
--
-- GRANT: 00-replication-role.sh granted CONNECT only. Debezium also needs
-- table-level SELECT to capture rows, so each schema file grants SELECT on ALL
-- TABLES to the replication role. The role name is the literal `replicator`,
-- coupled to .env POSTGRES_REPLICATION_USER (the postgres entrypoint runs *.sql
-- files without psql --set, so the env var is not available as a :'var' here —
-- the coupling is documented in .env.example and 00-replication-role.sh).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- agents — one row per sales/servicing agent. Referenced by policies (intra-PMS FK).
-- Defined before policies so the FK target exists at creation time.
-- -----------------------------------------------------------------------------
CREATE TABLE agents (
    agent_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    agent_code      VARCHAR(20) NOT NULL UNIQUE,
    agent_name      TEXT NOT NULL,
    branch          VARCHAR(50),
    commission_rate NUMERIC(5,4),
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit): PK-only before-image is sufficient — no
-- downstream dedup/SCD on agents. Stated for the record; not emitted.

-- -----------------------------------------------------------------------------
-- products — one row per insurance product. Referenced by policies (intra-PMS FK).
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    product_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_code  VARCHAR(20) NOT NULL UNIQUE,
    product_name  TEXT NOT NULL,
    segment       VARCHAR(20) NOT NULL
                  CHECK (segment IN ('Motor', 'Healthcare', 'Property & Casualty', 'Protection & Savings')),
    coverage_type VARCHAR(40),
    base_premium  NUMERIC(12,2),
    is_active     BOOLEAN NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- policyholders — one row per policyholder (the insured party).
--   nic is NOT UNIQUE on purpose: scenario S02 seeds duplicate-NIC pairs to test
--   Silver dedup. A UNIQUE constraint here would make that scenario impossible.
-- -----------------------------------------------------------------------------
CREATE TABLE policyholders (
    policyholder_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nic             VARCHAR(15) NOT NULL,   -- NOT UNIQUE (S02 duplicate-NIC scenario)
    full_name       TEXT NOT NULL,
    dob             TEXT,                   -- TEXT: raw mixed date formats (S04)
    gender          VARCHAR(6) CHECK (gender IN ('M', 'F')),
    email           TEXT,
    phone           VARCHAR(20),
    address         TEXT,
    city            VARCHAR(50),
    customer_tier   VARCHAR(20) CHECK (customer_tier IN ('Bronze', 'Silver', 'Gold', 'Platinum')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY FULL: Silver dedups on non-PK nic and tracks SCD Type 2 on
-- address/customer_tier — both need the full row before-image on UPDATE/DELETE,
-- which DEFAULT (PK only) does not emit. See ADR-003.
ALTER TABLE policyholders REPLICA IDENTITY FULL;

-- -----------------------------------------------------------------------------
-- policies — one row per policy. Intra-PMS FKs to policyholders, products, agents.
-- -----------------------------------------------------------------------------
CREATE TABLE policies (
    policy_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_number     VARCHAR(30) NOT NULL UNIQUE,
    policyholder_id   BIGINT NOT NULL REFERENCES policyholders (policyholder_id),
    product_id        BIGINT NOT NULL REFERENCES products (product_id),
    agent_id          BIGINT REFERENCES agents (agent_id),
    policy_start_date TEXT,                 -- TEXT: raw mixed date formats (S04)
    policy_end_date   TEXT,                 -- TEXT: raw mixed date formats (S04)
    sum_insured       NUMERIC(14,2),
    premium_amount    NUMERIC(12,2),
    policy_limit      NUMERIC(14,2),
    currency          VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    status            VARCHAR(20) NOT NULL CHECK (status IN ('active', 'lapsed', 'cancelled')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- endorsements — one row per policy endorsement (mid-term change). FK→policies.
-- -----------------------------------------------------------------------------
CREATE TABLE endorsements (
    endorsement_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id         BIGINT NOT NULL REFERENCES policies (policy_id),
    endorsement_type  VARCHAR(30) NOT NULL,
    effective_date    TEXT,                 -- TEXT: raw mixed date formats (S04)
    premium_delta     NUMERIC(12,2),
    sum_insured_delta NUMERIC(14,2),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- renewals — one row per policy renewal cycle. FK→policies.
-- -----------------------------------------------------------------------------
CREATE TABLE renewals (
    renewal_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id    BIGINT NOT NULL REFERENCES policies (policy_id),
    renewal_date TEXT,                      -- TEXT: raw mixed date formats (S04)
    new_premium  NUMERIC(12,2),
    renewed      BOOLEAN NOT NULL DEFAULT false,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- cancellations — one row per policy cancellation. FK→policies.
-- -----------------------------------------------------------------------------
CREATE TABLE cancellations (
    cancellation_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id         BIGINT NOT NULL REFERENCES policies (policy_id),
    cancellation_date TEXT,                 -- TEXT: raw mixed date formats (S04)
    reason            VARCHAR(50),
    refund_amount     NUMERIC(12,2),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (implicit).

-- -----------------------------------------------------------------------------
-- Debezium (replication role) needs table SELECT to capture rows. CONNECT was
-- granted by 00-replication-role.sh; this completes the grant for all PMS tables.
-- Literal role `replicator` is coupled to .env POSTGRES_REPLICATION_USER.
-- -----------------------------------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA public TO replicator;
