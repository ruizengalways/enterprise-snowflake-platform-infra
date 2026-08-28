variable "database_name" {
  description = "Snowflake analytics database name."
  type        = string
}

variable "environment" {
  description = "Logical environment label used in comments and metadata."
  type        = string
}

variable "schemas" {
  description = "Stable project schemas managed in this analytics database. Ephemeral/personal schemas are excluded."
  type        = set(string)
  default     = []
}

variable "database_retention_days" {
  description = "Database Time Travel retention in days."
  type        = number
  default     = 1

  validation {
    condition     = var.database_retention_days >= 0 && var.database_retention_days <= 90
    error_message = "database_retention_days must be between 0 and 90."
  }
}

variable "schema_retention_days" {
  description = "Stable schema Time Travel retention in days."
  type        = number
  default     = 1

  validation {
    condition     = var.schema_retention_days >= 0 && var.schema_retention_days <= 90
    error_message = "schema_retention_days must be between 0 and 90."
  }
}

variable "drop_public_schema" {
  description = "Drop the default PUBLIC schema when the database is created to avoid accidental unmanaged use."
  type        = bool
  default     = true
}
