# The canary image is supplied from the SAME single source as Compose: the
# CANARY_IMAGE entry in .env(.example), passed here as TF_VAR_canary_image. There is
# deliberately no default — the digest lives in exactly one committed place (.env.example),
# so Compose and Terraform can never drift to different images.
variable "canary_image" {
  type        = string
  description = "Digest-pinned canary image, e.g. nginx@sha256:<64-hex>. Sourced from CANARY_IMAGE in .env via TF_VAR_canary_image."

  # NOTE: this enforces digest FORMAT only — it cannot distinguish a multi-arch index digest from a
  # per-platform one. Multi-arch correctness comes from the documented acquisition step in .env.example
  # (`docker buildx imagetools inspect <image> --format '{{.Manifest.Digest}}'`).
  validation {
    # Reject any floating tag — image provisioning must be pinned to a digest for offline reproducibility.
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.canary_image))
    error_message = "canary_image must be digest-pinned (…@sha256:<64 hex chars>), never a floating tag."
  }
}
