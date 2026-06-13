"""S01 - Happy-path baseline.

Builds clean, fully-populated rows for all 17 tables across the three instances, with valid
intra-instance foreign keys and normal distributions. Covers all four insurance segments.

Conventions this baseline establishes (later scenarios mutate these):
- All business dates are emitted ISO-8601 here. S04 rewrites a deterministic 40% subset to
  the legacy `DD/MM/YYYY` format.
- All money currencies are SAR here. S05 flips a deterministic 15% of premium transactions to
  USD (and leaves some currency NULL, interpreted downstream as SAR).
- Every claim references a real (in-seed) policy/policyholder. S03 appends orphan claims whose
  `policy_id` was never allocated.
- Every NIC is unique here. S02 appends 50 duplicate-NIC policyholder rows.

Volumes come from `config.BASELINE` via `cfg.scaled(...)`, so the whole baseline scales with
`--scale` while keeping all relationships intact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seed import fields as fx
from seed.config import BASELINE
from seed.model import (
    Agent,
    Assessment,
    Cancellation,
    Claim,
    ClaimEvent,
    Dataset,
    Endorsement,
    GlSettlement,
    Ifrs17Data,
    Policy,
    Policyholder,
    PremiumTransaction,
    Product,
    ReinsuranceEntry,
    Renewal,
    Reserve,
    Settlement,
    ThirdPartyDetail,
)

if TYPE_CHECKING:
    import random

    from seed.config import GenConfig


def _build_pms(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Build the seven PMS tables with valid intra-PMS FKs."""
    agents_n = cfg.scaled(BASELINE.agents)
    a_ids = dataset.allocator("agents")
    for _ in range(agents_n):
        aid = a_ids.take()
        dataset.agents.append(
            Agent(
                agent_id=aid,
                agent_code=f"AG{aid:06d}",
                agent_name=fx.full_name(rng),
                branch=fx.city(rng),
                commission_rate=fx.rate(rng),
                is_active=rng.random() > 0.05,  # noqa: PLR2004 - 5% inactive, illustrative
            ),
        )

    p_ids = dataset.allocator("products")
    for _ in range(cfg.scaled(BASELINE.products)):
        pid = p_ids.take()
        dataset.products.append(
            Product(
                product_id=pid,
                product_code=f"PR{pid:05d}",
                product_name=f"Product {pid}",
                segment=rng.choice(fx.SEGMENTS),
                coverage_type=rng.choice(("comprehensive", "third-party", "basic")),
                base_premium=fx.money(rng, 500, 20_000),
                is_active=True,
            ),
        )

    ph_ids = dataset.allocator("policyholders")
    for _ in range(cfg.scaled(BASELINE.policyholders)):
        hid = ph_ids.take()
        name = fx.full_name(rng)
        dataset.policyholders.append(
            Policyholder(
                policyholder_id=hid,
                nic=fx.nic(rng),
                full_name=name,
                dob=fx.iso_date(fx.random_date(rng, 1950, 2005)),
                gender=rng.choice(fx.GENDERS),
                email=fx.email(rng, name, hid),
                phone=fx.phone(rng),
                address=f"{rng.randint(1, 999)} {fx.city(rng)} St",
                city=fx.city(rng),
                customer_tier=rng.choice(fx.CUSTOMER_TIERS),
            ),
        )

    pol_ids = dataset.allocator("policies")
    for _ in range(cfg.scaled(BASELINE.policies)):
        polid = pol_ids.take()
        sum_insured = fx.money(rng, 10_000, 5_000_000)
        start = fx.random_date(rng, 2021, 2024)
        end = fx.add_years(start, 1)
        dataset.policies.append(
            Policy(
                policy_id=polid,
                policy_number=f"POL{polid:08d}",
                policyholder_id=rng.choice(dataset.policyholders).policyholder_id,
                product_id=rng.choice(dataset.products).product_id,
                agent_id=(rng.choice(dataset.agents).agent_id if dataset.agents else None),
                policy_start_date=fx.iso_date(start),
                policy_end_date=fx.iso_date(end),
                sum_insured=sum_insured,
                premium_amount=fx.money(rng, 500, 50_000),
                policy_limit=sum_insured,
                currency="SAR",
                status=rng.choice(fx.POLICY_STATUS),
            ),
        )

    e_ids = dataset.allocator("endorsements")
    for _ in range(cfg.scaled(BASELINE.endorsements)):
        eid = e_ids.take()
        dataset.endorsements.append(
            Endorsement(
                endorsement_id=eid,
                policy_id=rng.choice(dataset.policies).policy_id,
                endorsement_type=rng.choice(("address-change", "coverage-increase", "add-driver")),
                effective_date=fx.iso_date(fx.random_date(rng, 2022, 2024)),
                premium_delta=fx.money(rng, 0, 5_000),
                sum_insured_delta=fx.money(rng, 0, 100_000),
            ),
        )

    r_ids = dataset.allocator("renewals")
    for _ in range(cfg.scaled(BASELINE.renewals)):
        rid = r_ids.take()
        dataset.renewals.append(
            Renewal(
                renewal_id=rid,
                policy_id=rng.choice(dataset.policies).policy_id,
                renewal_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                new_premium=fx.money(rng, 500, 50_000),
                renewed=rng.random() > 0.3,  # noqa: PLR2004 - ~70% renew, illustrative
            ),
        )

    c_ids = dataset.allocator("cancellations")
    for _ in range(cfg.scaled(BASELINE.cancellations)):
        cid = c_ids.take()
        dataset.cancellations.append(
            Cancellation(
                cancellation_id=cid,
                policy_id=rng.choice(dataset.policies).policy_id,
                cancellation_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                reason=rng.choice(("non-payment", "customer-request", "fraud")),
                refund_amount=fx.money(rng, 0, 10_000),
            ),
        )


def _build_cms(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Build the six CMS tables. Claims reference real (in-seed) PMS policies."""
    cl_ids = dataset.allocator("claims")
    for _ in range(cfg.scaled(BASELINE.claims)):
        clid = cl_ids.take()
        policy = rng.choice(dataset.policies)
        loss = fx.random_date(rng, 2022, 2024)
        dataset.claims.append(
            Claim(
                claim_id=clid,
                claim_number=f"CLM{clid:08d}",
                policy_id=policy.policy_id,
                policyholder_id=policy.policyholder_id,
                loss_date=fx.iso_date(loss),
                report_date=fx.iso_date(loss),
                claim_amount=fx.money(rng, 100, 500_000),
                claim_type=rng.choice(("collision", "theft", "medical", "fire")),
                status=rng.choice(fx.CLAIM_STATUS),
            ),
        )

    ce_ids = dataset.allocator("claim_events")
    for _ in range(cfg.scaled(BASELINE.claim_events)):
        ceid = ce_ids.take()
        dataset.claim_events.append(
            ClaimEvent(
                claim_event_id=ceid,
                claim_id=rng.choice(dataset.claims).claim_id,
                event_type=rng.choice(("opened", "assessed", "approved", "paid")),
                event_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                event_payload='{"channel":"web"}',
            ),
        )

    as_ids = dataset.allocator("assessments")
    for _ in range(cfg.scaled(BASELINE.assessments)):
        asid = as_ids.take()
        dataset.assessments.append(
            Assessment(
                assessment_id=asid,
                claim_id=rng.choice(dataset.claims).claim_id,
                assessor_name=fx.full_name(rng),
                assessed_amount=fx.money(rng, 100, 400_000),
                assessment_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                outcome=rng.choice(fx.ASSESSMENT_OUTCOME),
            ),
        )

    st_ids = dataset.allocator("settlements")
    for _ in range(cfg.scaled(BASELINE.settlements)):
        stid = st_ids.take()
        dataset.settlements.append(
            Settlement(
                settlement_id=stid,
                claim_id=rng.choice(dataset.claims).claim_id,
                settlement_amount=fx.money(rng, 100, 400_000),
                currency="SAR",
                settlement_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                payment_method=rng.choice(("bank-transfer", "cheque")),
            ),
        )

    re_ids = dataset.allocator("reserves")
    for _ in range(cfg.scaled(BASELINE.reserves)):
        reid = re_ids.take()
        dataset.reserves.append(
            Reserve(
                reserve_id=reid,
                claim_id=rng.choice(dataset.claims).claim_id,
                reserve_type=rng.choice(fx.RESERVE_TYPE),
                reserve_amount=fx.money(rng, 100, 500_000),
                currency="SAR",
                as_of_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
            ),
        )

    tp_ids = dataset.allocator("third_party_details")
    for _ in range(cfg.scaled(BASELINE.third_party_details)):
        tpid = tp_ids.take()
        dataset.third_party_details.append(
            ThirdPartyDetail(
                third_party_id=tpid,
                claim_id=rng.choice(dataset.claims).claim_id,
                party_name=fx.full_name(rng),
                party_nic=fx.nic(rng),
                liability_pct=(fx.money(rng, 0, 100)),
                recovery_amount=fx.money(rng, 0, 200_000),
            ),
        )


def _build_pfs(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Build the four PFS tables. Cross-instance policy refs point at real PMS policies."""
    pt_ids = dataset.allocator("premium_transactions")
    for _ in range(cfg.scaled(BASELINE.premium_transactions)):
        ptid = pt_ids.take()
        dataset.premium_transactions.append(
            PremiumTransaction(
                transaction_id=ptid,
                policy_id=rng.choice(dataset.policies).policy_id,
                transaction_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                amount=fx.money(rng, 100, 80_000),
                currency="SAR",
                transaction_type=rng.choice(("premium", "instalment", "adjustment")),
                payment_status=rng.choice(("paid", "pending", "failed")),
            ),
        )

    ri_ids = dataset.allocator("reinsurance_entries")
    for _ in range(cfg.scaled(BASELINE.reinsurance_entries)):
        riid = ri_ids.take()
        dataset.reinsurance_entries.append(
            ReinsuranceEntry(
                reinsurance_id=riid,
                policy_id=rng.choice(dataset.policies).policy_id,
                treaty_type=rng.choice(("quota-share", "excess-of-loss", "surplus")),
                retention_threshold=fx.money(rng, 100_000, 5_000_000),
                ceded_amount=fx.money(rng, 0, 1_000_000),
                recovery_amount=fx.money(rng, 0, 1_000_000),
                currency="SAR",
                entry_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
            ),
        )

    gl_ids = dataset.allocator("gl_settlements")
    for _ in range(cfg.scaled(BASELINE.gl_settlements)):
        glid = gl_ids.take()
        txn = (
            rng.choice(dataset.premium_transactions).transaction_id
            if dataset.premium_transactions and rng.random() > 0.1  # noqa: PLR2004
            else None
        )
        dataset.gl_settlements.append(
            GlSettlement(
                gl_settlement_id=glid,
                gl_account=f"GL{rng.randint(1000, 9999)}",
                transaction_id=txn,
                posting_date=fx.iso_date(fx.random_date(rng, 2022, 2025)),
                debit_amount=fx.money(rng, 0, 80_000),
                credit_amount=fx.money(rng, 0, 80_000),
                currency="SAR",
                fiscal_period=f"{rng.randint(2022, 2025)}-Q{rng.randint(1, 4)}",
            ),
        )

    if_ids = dataset.allocator("ifrs17_data")
    for _ in range(cfg.scaled(BASELINE.ifrs17_data)):
        ifid = if_ids.take()
        start = fx.random_date(rng, 2022, 2024)
        end = fx.add_years(start, 1)
        dataset.ifrs17_data.append(
            Ifrs17Data(
                ifrs17_id=ifid,
                policy_id=rng.choice(dataset.policies).policy_id,
                contract_group=f"CG-{rng.choice(fx.SEGMENTS).split()[0]}-{rng.randint(1, 50)}",
                measurement_model=rng.choice(fx.MEASUREMENT_MODEL),
                csm=fx.money(rng, 0, 1_000_000),
                risk_adjustment=fx.money(rng, 0, 200_000),
                coverage_start_date=fx.iso_date(start),
                coverage_end_date=fx.iso_date(end),
                fulfilment_cash_flows=fx.money(rng, 0, 2_000_000),
                loss_component=fx.money(rng, 0, 100_000),
                currency="SAR",
                reporting_period=f"{start.year}-Q{((start.month - 1) // 3) + 1}",
            ),
        )


def build(dataset: Dataset, cfg: GenConfig, rng: random.Random) -> None:
    """Populate the full happy-path baseline across PMS, CMS, and PFS."""
    _build_pms(dataset, cfg, rng)
    _build_cms(dataset, cfg, rng)
    _build_pfs(dataset, cfg, rng)
