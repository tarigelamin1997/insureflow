"""Deterministic synthetic-field helpers shared by the scenario modules.

Every function takes an explicit `random.Random` so there is no hidden global state - the
caller's seeded RNG drives all variety. Date helpers emit the two formats S04 needs:
`iso_date` (ISO-8601 `YYYY-MM-DD`) and `legacy_date` (`DD/MM/YYYY`), both as TEXT, because
the C2 schema stores all business dates as TEXT (raw fidelity for Silver to normalise).
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import random

# Closed enum domains - MUST match the CHECK constraints in the C2 schema exactly.
SEGMENTS: tuple[str, ...] = ("Motor", "Healthcare", "Property & Casualty", "Protection & Savings")
GENDERS: tuple[str, ...] = ("M", "F")
CUSTOMER_TIERS: tuple[str, ...] = ("Bronze", "Silver", "Gold", "Platinum")
POLICY_STATUS: tuple[str, ...] = ("active", "lapsed", "cancelled")
CLAIM_STATUS: tuple[str, ...] = ("open", "assessing", "settled", "rejected")
ASSESSMENT_OUTCOME: tuple[str, ...] = ("approved", "partial", "rejected")
RESERVE_TYPE: tuple[str, ...] = ("case", "IBNR")
MEASUREMENT_MODEL: tuple[str, ...] = ("GMM", "PAA", "VFA")
CURRENCIES: tuple[str, ...] = ("SAR", "USD")

_FIRST_NAMES: tuple[str, ...] = (
    "Mohammed",
    "Ahmed",
    "Fatima",
    "Aisha",
    "Omar",
    "Khalid",
    "Noura",
    "Sara",
    "Abdullah",
    "Yousef",
    "Layla",
    "Hana",
    "Faisal",
    "Reem",
    "Tariq",
    "Maha",
)
_FAMILY_NAMES: tuple[str, ...] = (
    "Al-Saud",
    "Al-Qahtani",
    "Al-Ghamdi",
    "Al-Harbi",
    "Al-Shammari",
    "Al-Otaibi",
    "Al-Dossari",
    "Al-Mutairi",
    "Al-Zahrani",
    "Al-Subaie",
    "Al-Rashid",
    "Al-Anazi",
)
_CITIES: tuple[str, ...] = (
    "Riyadh",
    "Jeddah",
    "Dammam",
    "Mecca",
    "Medina",
    "Khobar",
    "Tabuk",
    "Abha",
)

_EPOCH = dt.date(1970, 1, 1)


def iso_date(d: dt.date) -> str:
    """Render a date as ISO-8601 `YYYY-MM-DD` (the modern-system format)."""
    return d.isoformat()


def legacy_date(d: dt.date) -> str:
    """Render a date as legacy `DD/MM/YYYY` (the pre-acquisition format, S04)."""
    return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"


def random_date(rng: random.Random, start_year: int, end_year: int) -> dt.date:
    """Pick a deterministic date within `[start_year, end_year]` inclusive."""
    start = dt.date(start_year, 1, 1).toordinal()
    end = dt.date(end_year, 12, 31).toordinal()
    return dt.date.fromordinal(rng.randint(start, end))


def add_years(d: dt.date, years: int) -> dt.date:
    """Add `years` to a date, clamping Feb 29 to Feb 28 in non-leap years.

    `date.replace(year=...)` raises on Feb 29 -> non-leap; this helper makes the +1-year
    end-date computation total so a leap-day start cannot break generation.
    """
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def full_name(rng: random.Random) -> str:
    """Generate a deterministic full name."""
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_FAMILY_NAMES)}"


def city(rng: random.Random) -> str:
    """Pick a deterministic city."""
    return rng.choice(_CITIES)


def nic(rng: random.Random) -> str:
    """Generate a 10-digit KSA-style national ID string (within VARCHAR(15))."""
    return f"{rng.randint(1, 2)}{rng.randint(0, 999_999_999):09d}"


def email(rng: random.Random, name: str, key: int) -> str:
    """Derive a deterministic email from a name and a unique key."""
    handle = name.lower().replace(" ", ".").replace("-", "")
    domain = rng.choice(("example.com", "mail.test", "insure.test"))
    return f"{handle}.{key}@{domain}"


def phone(rng: random.Random) -> str:
    """Generate a deterministic KSA-format mobile number."""
    return f"+9665{rng.randint(0, 99_999_999):08d}"


def money(rng: random.Random, low: int, high: int) -> Decimal:
    """Generate a deterministic 2-dp money Decimal in `[low, high]`."""
    cents = rng.randint(low * 100, high * 100)
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percent(rng: random.Random, low: int = 0, high: int = 100) -> Decimal:
    """Generate a deterministic 2-dp percentage-point Decimal in `[low, high]`.

    Units are percentage points (0-100), not a fraction (0-1), matching the
    NUMERIC(5,2) `liability_pct` column. Draws the same single `rng.randint` as
    `money(rng, low, high)`, so swapping `money` for `percent` is value-identical
    and keeps the seed deterministic — this exists purely to make units explicit.
    """
    hundredths = rng.randint(low * 100, high * 100)
    return (Decimal(hundredths) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rate(rng: random.Random) -> Decimal:
    """Generate a deterministic 4-dp commission rate in [0.0100, 0.2000]."""
    return (Decimal(rng.randint(100, 2000)) / Decimal(10_000)).quantize(Decimal("0.0001"))
