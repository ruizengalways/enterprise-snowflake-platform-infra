variable "developer_databases" {
  description = "DEV analytics databases where the domain WRITE database role may create personal development schemas. Map of database name to domain code."
  type        = map(string)
  default     = {}
}

variable "ci_databases" {
  description = "CI analytics databases managed by dedicated machine-only domain CI roles. Map of database name to domain code."
  type        = map(string)
  default     = {}
}

variable "ci_warehouses_by_project" {
  description = "CI warehouse fully-qualified names keyed by domain code."
  type        = map(string)
  default     = {}
}
