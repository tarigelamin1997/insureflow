# Terraform owns IMAGE PROVISIONING + digest pinning — the offline staging layer.
# Compose owns the runtime substrate (network, volumes, services). See decisions/adr-001.
#
# `terraform apply` pulls and caches the digest-pinned image locally so every subsequent
# `docker compose up` runs fully offline against the exact image that was staged.
# Later phases add one docker_image resource per new service here.
resource "docker_image" "canary" {
  name = var.canary_image

  # Keep the pulled image on `terraform destroy` — destroy tears down the IaC record,
  # not the offline image cache the stack depends on.
  keep_locally = true
}
