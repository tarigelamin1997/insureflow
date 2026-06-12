output "canary_image_pinned" {
  description = "The digest-pinned canary image reference Terraform staged for offline use."
  value       = docker_image.canary.name
}

output "canary_image_id" {
  description = "Local image ID (sha256) of the staged canary image."
  value       = docker_image.canary.image_id
}
