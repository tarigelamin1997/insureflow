# The Postgres image is supplied from the SAME single source as Compose: the
# POSTGRES_IMAGE entry in .env(.example), passed here as TF_VAR_postgres_image. There is
# deliberately no default — the digest lives in exactly one committed place (.env.example),
# so Compose and Terraform can never drift to different images.
#
# ONE shared image variable for all three source DBs (PMS/CMS/PFS), not three (ADR-001):
# they are the same RDBMS at the same version; per-system identity is DB name + role +
# volume + port, not the image. One variable + one docker_image resource = one digest to
# audit, re-pin, and keep in lockstep with Compose.
variable "postgres_image" {
  type        = string
  description = "Digest-pinned Postgres 16 image, e.g. postgres@sha256:<64-hex>. Sourced from POSTGRES_IMAGE in .env via TF_VAR_postgres_image. Shared by postgres-pms/cms/pfs."

  # NOTE: this enforces digest FORMAT only — it cannot distinguish a multi-arch index digest from a
  # per-platform one. Multi-arch correctness comes from the documented acquisition step in .env.example
  # (`docker buildx imagetools inspect postgres:16 --format '{{.Manifest.Digest}}'`).
  validation {
    # Reject any floating tag — image provisioning must be pinned to a digest for offline reproducibility.
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.postgres_image))
    error_message = "postgres_image must be digest-pinned (…@sha256:<64 hex chars>), never a floating tag."
  }
}
