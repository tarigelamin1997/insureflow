# Terraform owns IMAGE PROVISIONING + digest pinning — the offline staging layer.
# Compose owns the runtime substrate (network, volumes, services). See 01-infrastructure/
# decisions/adr-001 and 02-source-systems/decisions/adr-001.
#
# `terraform apply` pulls and caches the digest-pinned image locally so every subsequent
# `docker compose up` runs fully offline against the exact image that was staged.
#
# ONE resource for the shared Postgres image (ADR-001): all three source DBs
# (postgres-pms / postgres-cms / postgres-pfs) reference the same digest in Compose, so
# Terraform stages it exactly once. Three image vars + three resources would stage the
# same bits three times for no benefit.
resource "docker_image" "postgres" {
  name = var.postgres_image

  # Keep the pulled image on `terraform destroy` — destroy tears down the IaC record,
  # not the offline image cache the stack depends on.
  keep_locally = true
}
