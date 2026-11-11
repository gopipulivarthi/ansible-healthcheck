terraform {
  required_version = ">= 1.4.0"
}

variable "lab_generation" {
  description = "Change this value only when you intentionally want Terraform to destroy and recreate the Vagrant lab."
  type        = string
  default     = "v1"
}

# VirtualBox itself is driven through Vagrant. terraform_data is a built-in
# Terraform resource, so no third-party VirtualBox provider is required.
resource "terraform_data" "vagrant_lab" {
  triggers_replace = [var.lab_generation]

  provisioner "local-exec" {
    command     = "vagrant up --provider=virtualbox"
    working_dir = "${path.module}/.."
  }

  provisioner "local-exec" {
    when        = destroy
    command     = "vagrant destroy -f"
    working_dir = "${path.module}/.."
  }
}

output "controller_url" {
  value = "http://192.168.56.10:8080 (Jenkins) and http://192.168.56.10:5000 (Dashboard)"
}
