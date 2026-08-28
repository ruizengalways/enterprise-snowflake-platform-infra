variable "database_name" {
  description = "Platform control database name."
  type        = string
}

variable "schemas" {
  description = "Structural PLATFORM_CONTROL schemas."
  type        = set(string)
}

variable "retention_days" {
  description = "Time Travel retention in days for the control database and schemas."
  type        = number
  default     = 1

  validation {
    condition     = var.retention_days >= 0 && var.retention_days <= 90
    error_message = "retention_days must be between 0 and 90."
  }
}
