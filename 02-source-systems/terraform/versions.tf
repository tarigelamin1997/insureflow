# Terraform + provider version pins for Phase 02 image provisioning. Mirrors the
# Phase 01 Terraform pattern: the Docker provider talks to the local daemon, no
# remote backend (local, offline infrastructure).
terraform {
  required_version = ">= 1.6"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}
