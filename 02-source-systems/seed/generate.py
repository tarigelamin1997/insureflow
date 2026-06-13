"""InsureFlow Phase 02 - parameterized scenario seed generator (CLI).

Builds a deterministic, scenario-composed dataset in memory and serialises it to three
per-instance SQL files under `02-source-systems/seed/output/` (gitignored):
`pms_seed.sql`, `cms_seed.sql`, `pfs_seed.sql`.

Determinism: a fixed `--seed` (default 42) yields byte-identical output across runs and
machines - all variety flows through one seeded `random.Random`; no clock, UUID, or global
RNG is used. Idempotency: each file begins with `TRUNCATE ... RESTART IDENTITY CASCADE` inside a
single transaction, so re-loading never duplicates or errors.

Usage:
    python 02-source-systems/seed/generate.py --scenarios S01,S02,S03,S04,S05
    python 02-source-systems/seed/generate.py --scenarios S01,S02,S03,S04,S05 --scale 0.02
    python 02-source-systems/seed/generate.py --scenarios all --scale 2 --seed 7

Scope: S01-S05 implemented; S06-S12 are architected but raise NotImplementedError if selected
(see seed/registry.py). `--scenarios all` runs only the implemented set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Direct-script execution (`python 02-source-systems/seed/generate.py`): the package dir
# name starts with a digit and contains a hyphen, so it cannot be imported as a dotted
# module. Put the `seed` package's parent on sys.path so absolute `seed.*` imports resolve
# whether this file is run as a script or imported as `seed.generate`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seed.builder import assert_seed_self_consistency, build_dataset
from seed.config import GenConfig
from seed.registry import ALL_SCENARIO_IDS, IMPLEMENTED
from seed.sql import INSTANCES, render_instance

_OUTPUT_DIR = Path(__file__).resolve().parent / "output"
_FILE_FOR = {"pms": "pms_seed.sql", "cms": "cms_seed.sql", "pfs": "pfs_seed.sql"}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="InsureFlow Phase 02 scenario seed generator.",
    )
    parser.add_argument(
        "--scenarios",
        default=",".join(IMPLEMENTED),
        help=(
            "Comma-separated scenario IDs (S01..S12) or 'all'. "
            f"Implemented: {', '.join(IMPLEMENTED)}. Default: the implemented set."
        ),
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Row-count multiplier for percentage-based volumes (default 1.0). "
        "Fixed-absolute injections (S02=50, S03=30) ignore this.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed for deterministic output (default 42).",
    )
    return parser.parse_args(argv)


def _scenario_list(raw: str) -> list[str]:
    """Split the --scenarios string into a normalised list."""
    if raw.strip().lower() == "all":
        return ["all"]
    return [token for token in (part.strip() for part in raw.split(",")) if token]


def run(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = _parse_args(argv)
    if args.scale <= 0:
        sys.stderr.write(f"error: --scale must be > 0 (got {args.scale})\n")
        return 2
    cfg = GenConfig(
        scenarios=_scenario_list(args.scenarios),
        scale=args.scale,
        seed=args.seed,
    )

    dataset = build_dataset(cfg)
    # Fail-fast: never write SQL for a dataset that violates its own invariants.
    assert_seed_self_consistency(dataset, cfg.scenarios)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for instance in INSTANCES:
        sql_text = render_instance(
            instance,
            dataset,
            scenarios=(IMPLEMENTED if cfg.scenarios == ["all"] else cfg.scenarios),
            scale=cfg.scale,
            seed=cfg.seed,
        )
        out_path = _OUTPUT_DIR / _FILE_FOR[instance]
        out_path.write_text(sql_text, encoding="utf-8", newline="\n")
        row_total = sum(len(getattr(dataset, t)) for t in INSTANCES[instance])
        sys.stdout.write(f"wrote {out_path} ({row_total} rows)\n")

    valid = ", ".join(ALL_SCENARIO_IDS)
    sys.stdout.write(
        f"seed generated: scenarios={cfg.scenarios} scale={cfg.scale} seed={cfg.seed} "
        f"(valid IDs: {valid}, or 'all')\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
