"""Fitness function: every docker-compose service declares a non-trivial healthcheck.

Property: every service block in the root docker-compose.yml carries a `healthcheck`
          with a non-empty `test`. (Root Global Build Standard: "Every service in
          docker-compose.yml has a healthcheck.")
Phase: 01 — Infrastructure
Fails when: a service is added to docker-compose.yml without a healthcheck, or with an
            empty / placeholder `test`.
"""

from pathlib import Path
from typing import Any

import yaml

_COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"


def test_every_service_has_healthcheck() -> None:
    """Every service in docker-compose.yml has a healthcheck with a non-empty test."""
    model = yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))
    services: dict[str, Any] = model["services"]

    offenders = [
        name for name, svc in services.items() if not (svc.get("healthcheck") or {}).get("test")
    ]

    assert (
        not offenders
    ), f"services missing a healthcheck.test (root Global Build Standard): {offenders}"
