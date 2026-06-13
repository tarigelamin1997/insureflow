"""Typed in-memory model of the seed dataset.

The generator builds a fully-typed `Dataset` in memory (one list of row dataclasses
per table), then serialises it to per-instance SQL. Keeping the dataset typed - rather
than emitting SQL strings directly from each scenario - means:

- `mypy --strict` checks every column assignment against the schema-mirroring dataclass,
  so a column/type mismatch with the C2 DDL is a type error, not a runtime SQL error.
- Scenarios compose: each scenario mutates/extends the same `Dataset`, in registry order,
  so S02 (duplicate policyholders) and S03 (orphan claims) layer cleanly on the S01 baseline.
- The self-assertion tests (`tests/unit/test_seed_scenarios.py`) inspect the typed dataset
  directly, with no SQL parsing.

Primary keys are `BIGINT GENERATED ALWAYS AS IDENTITY` in the C2 schema. The seed assigns
explicit, deterministic surrogate IDs (counter-allocated from `IdAllocator`) so intra-seed
FKs resolve, and the emitted INSERTs use `OVERRIDING SYSTEM VALUE` to honour those IDs
against an `ALWAYS` identity column (see `sql.py`).

Every field name here MUST match the corresponding column in
`02-source-systems/schema/{pms,cms,pfs}/01-schema.sql` exactly. `created_at` / `updated_at`
are DB defaults (`now()`) and are intentionally NOT modelled - the seed lets the schema
default populate them, which keeps the seed deterministic (no wall-clock in the output).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal


class IdAllocator:
    """Hands out monotonically increasing surrogate IDs, deterministically.

    One allocator per table keeps PK sequences independent and reproducible: the Nth
    row of a table always gets the same ID regardless of `--scale` ordering effects,
    because allocation order is fixed by the build sequence.
    """

    def __init__(self, start: int = 1) -> None:
        """Initialise the allocator at `start` (default 1, matching IDENTITY)."""
        self._next = start

    def take(self) -> int:
        """Return the next ID and advance the counter."""
        value = self._next
        self._next += 1
        return value


# --- PMS -------------------------------------------------------------------------------


@dataclass
class Agent:
    """Mirrors PMS.agents."""

    agent_id: int
    agent_code: str
    agent_name: str
    branch: str | None
    commission_rate: Decimal | None
    is_active: bool


@dataclass
class Product:
    """Mirrors PMS.products."""

    product_id: int
    product_code: str
    product_name: str
    segment: str
    coverage_type: str | None
    base_premium: Decimal | None
    is_active: bool


@dataclass
class Policyholder:
    """Mirrors PMS.policyholders. `nic` is deliberately non-unique (S02)."""

    policyholder_id: int
    nic: str
    full_name: str
    dob: str | None
    gender: str | None
    email: str | None
    phone: str | None
    address: str | None
    city: str | None
    customer_tier: str | None


@dataclass
class Policy:
    """Mirrors PMS.policies. Date columns are TEXT (raw mixed formats, S04)."""

    policy_id: int
    policy_number: str
    policyholder_id: int
    product_id: int
    agent_id: int | None
    policy_start_date: str | None
    policy_end_date: str | None
    sum_insured: Decimal | None
    premium_amount: Decimal | None
    policy_limit: Decimal | None
    currency: str | None
    status: str


@dataclass
class Endorsement:
    """Mirrors PMS.endorsements."""

    endorsement_id: int
    policy_id: int
    endorsement_type: str
    effective_date: str | None
    premium_delta: Decimal | None
    sum_insured_delta: Decimal | None


@dataclass
class Renewal:
    """Mirrors PMS.renewals."""

    renewal_id: int
    policy_id: int
    renewal_date: str | None
    new_premium: Decimal | None
    renewed: bool


@dataclass
class Cancellation:
    """Mirrors PMS.cancellations."""

    cancellation_id: int
    policy_id: int
    cancellation_date: str | None
    reason: str | None
    refund_amount: Decimal | None


# --- CMS -------------------------------------------------------------------------------


@dataclass
class Claim:
    """Mirrors CMS.claims. policy_id / policyholder_id are cross-instance refs (no FK)."""

    claim_id: int
    claim_number: str
    policy_id: int | None
    policyholder_id: int | None
    loss_date: str | None
    report_date: str | None
    claim_amount: Decimal | None
    claim_type: str | None
    status: str


@dataclass
class ClaimEvent:
    """Mirrors CMS.claim_events."""

    claim_event_id: int
    claim_id: int
    event_type: str
    event_date: str | None
    event_payload: str | None  # JSONB - emitted as a JSON string literal


@dataclass
class Assessment:
    """Mirrors CMS.assessments."""

    assessment_id: int
    claim_id: int
    assessor_name: str | None
    assessed_amount: Decimal | None
    assessment_date: str | None
    outcome: str | None


@dataclass
class Settlement:
    """Mirrors CMS.settlements."""

    settlement_id: int
    claim_id: int
    settlement_amount: Decimal | None
    currency: str | None
    settlement_date: str | None
    payment_method: str | None


@dataclass
class Reserve:
    """Mirrors CMS.reserves."""

    reserve_id: int
    claim_id: int
    reserve_type: str
    reserve_amount: Decimal | None
    currency: str | None
    as_of_date: str | None


@dataclass
class ThirdPartyDetail:
    """Mirrors CMS.third_party_details."""

    third_party_id: int
    claim_id: int
    party_name: str | None
    party_nic: str | None
    liability_pct: Decimal | None
    recovery_amount: Decimal | None


# --- PFS -------------------------------------------------------------------------------


@dataclass
class PremiumTransaction:
    """Mirrors PFS.premium_transactions. `amount` NOT NULL; `currency` nullable (S05)."""

    transaction_id: int
    policy_id: int | None
    transaction_date: str | None
    amount: Decimal
    currency: str | None
    transaction_type: str
    payment_status: str | None


@dataclass
class ReinsuranceEntry:
    """Mirrors PFS.reinsurance_entries."""

    reinsurance_id: int
    policy_id: int | None
    treaty_type: str | None
    retention_threshold: Decimal | None
    ceded_amount: Decimal | None
    recovery_amount: Decimal | None
    currency: str | None
    entry_date: str | None


@dataclass
class GlSettlement:
    """Mirrors PFS.gl_settlements. transaction_id -> premium_transactions (intra-PFS FK)."""

    gl_settlement_id: int
    gl_account: str
    transaction_id: int | None
    posting_date: str | None
    debit_amount: Decimal | None
    credit_amount: Decimal | None
    currency: str | None
    fiscal_period: str | None


@dataclass
class Ifrs17Data:
    """Mirrors PFS.ifrs17_data."""

    ifrs17_id: int
    policy_id: int | None
    contract_group: str
    measurement_model: str
    csm: Decimal | None
    risk_adjustment: Decimal | None
    coverage_start_date: str | None
    coverage_end_date: str | None
    fulfilment_cash_flows: Decimal | None
    loss_component: Decimal | None
    currency: str | None
    reporting_period: str | None


# --- Dataset ---------------------------------------------------------------------------


@dataclass
class Dataset:
    """The full in-memory seed: one list per table, plus per-table ID allocators.

    Scenarios receive the same `Dataset` instance and append to / mutate these lists
    in registry order. The allocators guarantee deterministic, collision-free surrogate
    keys across scenarios (e.g. S03 orphan claims allocate real claim IDs but reference
    policy IDs that were never allocated).
    """

    # PMS
    agents: list[Agent] = field(default_factory=list)
    products: list[Product] = field(default_factory=list)
    policyholders: list[Policyholder] = field(default_factory=list)
    policies: list[Policy] = field(default_factory=list)
    endorsements: list[Endorsement] = field(default_factory=list)
    renewals: list[Renewal] = field(default_factory=list)
    cancellations: list[Cancellation] = field(default_factory=list)
    # CMS
    claims: list[Claim] = field(default_factory=list)
    claim_events: list[ClaimEvent] = field(default_factory=list)
    assessments: list[Assessment] = field(default_factory=list)
    settlements: list[Settlement] = field(default_factory=list)
    reserves: list[Reserve] = field(default_factory=list)
    third_party_details: list[ThirdPartyDetail] = field(default_factory=list)
    # PFS
    premium_transactions: list[PremiumTransaction] = field(default_factory=list)
    reinsurance_entries: list[ReinsuranceEntry] = field(default_factory=list)
    gl_settlements: list[GlSettlement] = field(default_factory=list)
    ifrs17_data: list[Ifrs17Data] = field(default_factory=list)

    # ID allocators (one per table with a surrogate PK).
    ids: dict[str, IdAllocator] = field(default_factory=dict)

    def allocator(self, table: str) -> IdAllocator:
        """Return (creating on first use) the ID allocator for `table`."""
        if table not in self.ids:
            self.ids[table] = IdAllocator()
        return self.ids[table]
