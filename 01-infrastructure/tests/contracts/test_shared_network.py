"""Fitness function: every docker-compose service attaches to the shared `insureflow` network.

Property: a single user-defined bridge network `insureflow` is declared, and every service lists
          it under `networks`. No service is left on the implicit default bridge — inter-service
          DNS resolution across all later phases depends on this.
Phase: 01 — Infrastructure
Fails when: a service omits `networks:` (falls back to the default bridge) or the shared network
            is renamed/removed.
"""

from pathlib import Path
from typing import Any

import yaml

_COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"


def test_shared_network() -> None:
    """Every service attaches to the shared `insureflow` network; none on the default bridge."""
    model = yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))

    networks: dict[str, Any] = model.get("networks") or {}
    assert "insureflow" in networks, "top-level `insureflow` network is not declared"

    services: dict[str, Any] = model["services"]
    offenders = [
        name for name, svc in services.items() if "insureflow" not in (svc.get("networks") or [])
    ]

    assert not offenders, f"services not attached to the shared `insureflow` network: {offenders}"
