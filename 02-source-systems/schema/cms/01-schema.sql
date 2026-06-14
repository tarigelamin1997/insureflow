-- =============================================================================
-- Phase 02 — CMS (Claims Management System) schema DDL.
--
-- Runs ONCE on first init of postgres-cms, AFTER 00-replication-role.sh
-- (entrypoint executes /docker-entrypoint-initdb.d/ files in FILENAME order).
--
-- DESIGN CONTRACT (approved Chunk-2 schema spec) — see pms/01-schema.sql header
-- for the shared rules (surrogate IDENTITY PK, created_at/updated_at TIMESTAMPTZ,
-- all business/event dates as TEXT, GRANT coupling). CMS-specific points:
--
--   - CROSS-INSTANCE refs are PLAIN columns with NO foreign key. claims.policy_id
--     and claims.policyholder_id point at PMS (a SEPARATE Postgres instance, ADR-002),
--     so an FK is impossible by construction — and that is the point: it lets
--     scenario S03 seed orphan claims (a claim whose policy_id has no PMS policy).
--   - Intra-CMS FKs (everything → claims) ARE enforced.
--   - REPLICA IDENTITY FULL on claims, claim_events, reserves (full before-images
--     for S10 out-of-order claim+event dedup and reserve revaluation). assessments,
--     settlements, third_party_details declare DEFAULT EXPLICITLY to limit WAL —
--     every table states its identity in DDL, none relies on the implicit default.
--     See ADR-003.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- claims — one row per claim. The CMS root entity; everything else FKs to it.
--   policy_id / policyholder_id are CROSS-INSTANCE logical refs to PMS — NO FK.
--   This is what makes S03 orphan claims (policy_id with no PMS policy) possible.
-- -----------------------------------------------------------------------------
CREATE TABLE claims (
    claim_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_number    VARCHAR(30) NOT NULL UNIQUE,
    policy_id       BIGINT,        -- cross-instance logical ref → PMS.policies; NO FK (enables S03 orphans)
    policyholder_id BIGINT,        -- cross-instance logical ref → PMS.policyholders; NO FK
    loss_date       TEXT,          -- TEXT: raw mixed date formats (S04)
    report_date     TEXT,          -- TEXT: raw mixed date formats (S04)
    claim_amount    NUMERIC(14,2),
    claim_type      VARCHAR(30),
    status          VARCHAR(20) NOT NULL CHECK (status IN ('open', 'assessing', 'settled', 'rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY FULL: S10 out-of-order claim/event dedup needs the full row
-- before-image on UPDATE/DELETE (DEFAULT emits PK only). See ADR-003.
ALTER TABLE claims REPLICA IDENTITY FULL;

-- -----------------------------------------------------------------------------
-- claim_events — one row per lifecycle event on a claim. Intra-CMS FK→claims.
-- -----------------------------------------------------------------------------
CREATE TABLE claim_events (
    claim_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id       BIGINT NOT NULL REFERENCES claims (claim_id),
    event_type     VARCHAR(30) NOT NULL,
    event_date     TEXT,          -- TEXT: raw mixed date formats (S04)
    event_payload  JSONB,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY FULL: out-of-order event dedup (S10) needs full before-images. See ADR-003.
ALTER TABLE claim_events REPLICA IDENTITY FULL;

-- -----------------------------------------------------------------------------
-- assessments — one row per claim assessment. Intra-CMS FK→claims.
-- -----------------------------------------------------------------------------
CREATE TABLE assessments (
    assessment_id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id        BIGINT NOT NULL REFERENCES claims (claim_id),
    assessor_name   TEXT,
    assessed_amount NUMERIC(14,2),
    assessment_date TEXT,          -- TEXT: raw mixed date formats (S04)
    outcome         VARCHAR(20) CHECK (outcome IN ('approved', 'partial', 'rejected')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (explicit).
ALTER TABLE assessments REPLICA IDENTITY DEFAULT;

-- -----------------------------------------------------------------------------
-- settlements — one row per claim settlement (payout). Intra-CMS FK→claims.
-- -----------------------------------------------------------------------------
CREATE TABLE settlements (
    settlement_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id          BIGINT NOT NULL REFERENCES claims (claim_id),
    settlement_amount NUMERIC(14,2),
    currency          VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    settlement_date   TEXT,        -- TEXT: raw mixed date formats (S04)
    payment_method    VARCHAR(20),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (explicit).
ALTER TABLE settlements REPLICA IDENTITY DEFAULT;

-- -----------------------------------------------------------------------------
-- reserves — one row per reserve valuation on a claim. Intra-CMS FK→claims.
-- -----------------------------------------------------------------------------
CREATE TABLE reserves (
    reserve_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id       BIGINT NOT NULL REFERENCES claims (claim_id),
    reserve_type   VARCHAR(20) NOT NULL CHECK (reserve_type IN ('case', 'IBNR')),
    reserve_amount NUMERIC(14,2),
    currency       VARCHAR(3) CHECK (currency IN ('SAR', 'USD')),
    as_of_date     TEXT,          -- TEXT: raw mixed date formats (S04)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY FULL: reserve revaluation needs the before-image (prior amount)
-- on UPDATE, which DEFAULT (PK only) does not emit. See ADR-003.
ALTER TABLE reserves REPLICA IDENTITY FULL;

-- -----------------------------------------------------------------------------
-- third_party_details — one row per third party on a claim. Intra-CMS FK→claims.
-- -----------------------------------------------------------------------------
CREATE TABLE third_party_details (
    third_party_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    claim_id        BIGINT NOT NULL REFERENCES claims (claim_id),
    party_name      TEXT,
    party_nic       VARCHAR(15),
    liability_pct   NUMERIC(5,2),
    recovery_amount NUMERIC(14,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- REPLICA IDENTITY DEFAULT (explicit).
ALTER TABLE third_party_details REPLICA IDENTITY DEFAULT;

-- Table SELECT for the replication role is granted by 02-grant-select.sh, which
-- runs after this schema and is parameterized on $POSTGRES_REPLICATION_USER — no
-- hardcoded role name here (00-replication-role.sh granted CONNECT).
