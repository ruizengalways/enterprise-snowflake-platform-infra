variable "project_codes" {
  description = "Domain/data-product codes used in account and database role names, for example HEALTH and TRANSPORT."
  type        = set(string)
}

variable "database_projects" {
  description = "Mapping of analytics database name to the single owning domain/data-product code."
  type        = map(string)
}

variable "stable_schemas_by_database" {
  description = "Stable schemas by analytics database. Personal and PR schemas are intentionally excluded."
  type        = map(set(string))
}

variable "published_schemas_by_database" {
  description = "Published schemas exposed to the domain GUEST role. Normally MARTS and SEMANTIC; must be a subset of stable schemas."
  type        = map(set(string))
}

variable "grant_developer_write" {
  description = "Whether domain DEVELOPER account roles receive the WRITE database role in this account. True in DEV; false in UAT/PROD."
  type        = bool
}

variable "warehouse_grants" {
  description = "Warehouse USAGE grants keyed by account-role name. Role hierarchy provides inherited access."
  type        = map(set(string))
  default     = {}
}
