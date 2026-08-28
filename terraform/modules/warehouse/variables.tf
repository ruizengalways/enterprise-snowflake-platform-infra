variable "name" {
  description = "Warehouse name."
  type        = string
}

variable "warehouse_size" {
  description = "Snowflake warehouse size."
  type        = string
  default     = "XSMALL"
}

variable "auto_suspend_seconds" {
  description = "Seconds of inactivity before automatic suspension."
  type        = number
  default     = 60

  validation {
    condition     = var.auto_suspend_seconds >= 60
    error_message = "auto_suspend_seconds must be at least 60 seconds."
  }
}

variable "statement_timeout_seconds" {
  description = "Maximum running statement duration before cancellation."
  type        = number
  default     = 3600

  validation {
    condition     = var.statement_timeout_seconds > 0
    error_message = "statement_timeout_seconds must be positive."
  }
}

variable "statement_queued_timeout_seconds" {
  description = "Maximum queued statement duration before cancellation."
  type        = number
  default     = 300
}

variable "comment" {
  description = "Warehouse comment."
  type        = string
  default     = "Managed by enterprise-snowflake-platform-infra."
}
