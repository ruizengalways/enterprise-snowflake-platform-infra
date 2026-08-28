variable "initial_admin_name" {
  description = "Initial SERVICE admin login created in each environment account. This is bootstrap-only and is not the long-term CI/CD identity."
  type        = string
  default     = "TF_BOOTSTRAP_ADMIN"
}

variable "initial_admin_email" {
  description = "Notification email for the initial account administrator. Supply outside source control."
  type        = string
  sensitive   = true
}

variable "initial_admin_rsa_public_key" {
  description = "RSA public key for the initial SERVICE administrator. Supply outside source control; never commit the private key."
  type        = string
  sensitive   = true
}
