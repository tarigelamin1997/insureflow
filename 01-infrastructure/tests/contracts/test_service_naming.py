"""Fitness function: docker-compose service names conform to the Global Naming Convention.

Property: every service name is lowercase kebab-case, and any service whose role maps to a
          root CLAUDE.md "Global Naming Conventions" entry uses that exact name. The Phase 01
          `canary` fixture is the only allow-listed non-catalog service.
Phase: 01 — Infrastructure
Fails when: a service is named with uppercase/underscores (e.g. `Postgres_PMS`) or a catalog
            service is misspelled (e.g. `kafka-broker` instead of `kafka`).
"""

import re
from pathlib import Path
from typing import Any

import yaml

_COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.yml"

# Sanctioned Docker service names — root CLAUDE.md → Global Naming Conventions.
_SANCTIONED = {
    "kafka",
    "schema-registry",
    "postgres-pms",
    "postgres-cms",
    "postgres-pfs",
    "debezium",
    "minio",
    "airflow",
    "openmetadata",
    "marquez",
    "qdrant",
    "ollama",
    "prometheus",
    "grafana",
    "superset",
    "fastapi",
}
# Non-catalog services legitimately introduced by infrastructure phases.
_ALLOWLIST = {"canary"}
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_service_naming() -> None:
    """Every compose service name matches the Global Naming Convention."""
    model = yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))
    services: dict[str, Any] = model["services"]
    names = list(services)

    bad_format = [n for n in names if not _KEBAB.match(n)]
    unsanctioned = [n for n in names if n not in _SANCTIONED and n not in _ALLOWLIST]

    assert not bad_format, f"service names are not lowercase kebab-case: {bad_format}"
    assert (
        not unsanctioned
    ), f"service names not in the sanctioned set or allow-list: {unsanctioned}"
