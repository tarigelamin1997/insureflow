output "postgres_image_pinned" {
  description = "The digest-pinned Postgres image reference Terraform staged for offline use (shared by postgres-pms/cms/pfs)."
  value       = docker_image.postgres.name
}

output "postgres_image_id" {
  description = "Local image ID (sha256) of the staged Postgres image."
  value       = docker_image.postgres.image_id
}
