# Terraform + provider version pins. The Docker provider talks to the local daemon;
# no remote backend (this is local, offline infrastructure).
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
